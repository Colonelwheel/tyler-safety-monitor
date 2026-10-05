"""Camera supervision checks use no camera, image files, or native drivers."""

from collections import deque
import multiprocessing
import time

import pytest

from tyler_safety_monitor.camera import CameraCapture, CameraSettings, _configure_capture, _fps, _put_latest


def _hung_worker(settings, output, stop, transport):
    # Ignore cooperative stop, like a blocked driver read/open.
    time.sleep(60)


def _frame_then_hung_worker(settings, output, stop, transport):
    from multiprocessing import shared_memory
    import numpy as np
    shared = shared_memory.SharedMemory(name=transport["name"])
    try:
        with transport["lock"]:
            np.ndarray((2, 2, 3), dtype=np.uint8, buffer=shared.buf).fill(77)
            transport["sequence"].value = 1
        output.put({"kind": "frame", "shape": (2, 2, 3), "sequence": 1,
                    "captured_at": time.monotonic(), "captured_frames": 1})
        time.sleep(60)
    finally:
        shared.close()


def _wait_until(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


def test_settings_validate_backend_and_delays():
    with pytest.raises(ValueError):
        CameraSettings(backend="anything")
    with pytest.raises(ValueError):
        CameraSettings(reconnect_initial=20, reconnect_max=10)
    with pytest.raises(ValueError):
        CameraSettings(fps=0)


def test_monotonic_stale_frame_is_visible_and_fresh_frame_recovers():
    camera = CameraCapture(CameraSettings(stale_after=0.01))
    old = time.monotonic() - 1.0
    camera._accept({"kind": "frame", "image": object(), "captured_at": old, "sequence": 1})
    stale = camera.snapshot()
    assert stale.state == "FAULT"
    assert stale.frame_age >= 1.0
    camera._accept({"kind": "frame", "image": object(), "captured_at": time.monotonic(), "sequence": 2})
    assert camera.snapshot().state == "LIVE"
    assert camera.latest_frame().sequence == 2
    assert camera.snapshot().received_frames == 2
    camera.stop()
    assert camera.latest_frame() is None


def test_read_failure_is_visible_without_wall_clock_timers():
    camera = CameraCapture()
    camera._accept({"kind": "read_failure", "read_failures": 3})
    assert camera.snapshot().state == "FAULT"
    assert camera.snapshot().read_failures == 3
    camera._accept({"kind": "frame", "image": object(), "captured_at": time.monotonic(),
                    "sequence": 1, "read_failures": 3})
    assert camera.snapshot().state == "LIVE"
    assert camera.snapshot().read_failures == 3


def test_fps_uses_timestamp_span_and_handles_empty_or_duplicate_times():
    assert _fps(deque()) == 0
    assert _fps(deque([1.0, 1.0])) == 0
    assert _fps(deque([1.0, 1.1, 1.2])) == pytest.approx(10)


def test_bounded_queue_replaces_oldest_without_waiting():
    import queue
    output = queue.Queue(maxsize=1)
    assert _put_latest(output, {"sequence": 1}) is False
    assert _put_latest(output, {"sequence": 2}) is True
    assert output.get_nowait()["sequence"] == 2


def test_hung_native_worker_recovers_with_bounded_backoff_and_stops():
    initial_children = {process.pid for process in multiprocessing.active_children()}
    camera = CameraCapture(CameraSettings(open_timeout=0.15, reconnect_initial=0.05,
                                           reconnect_max=0.1), _worker_target=_hung_worker)
    camera.start()
    try:
        assert _wait_until(lambda: camera.snapshot().reconnect_events >= 2)
    finally:
        camera.stop()
    assert camera.snapshot().state == "STOPPED"
    assert not camera._thread.is_alive()
    assert {process.pid for process in multiprocessing.active_children()} <= initial_children


def test_retry_bypasses_long_reconnect_delay():
    camera = CameraCapture(CameraSettings(open_timeout=0.15, reconnect_initial=10,
                                           reconnect_max=10), _worker_target=_hung_worker)
    camera.start()
    try:
        assert _wait_until(lambda: camera.snapshot().reconnect_events == 1)
        previous_generation = camera._generation
        camera.retry()
        assert _wait_until(lambda: camera._generation > previous_generation, timeout=1)
    finally:
        camera.stop()


def test_shared_frame_delivery_stale_read_fault_and_owned_process_restart():
    camera = CameraCapture(CameraSettings(open_timeout=3, stale_after=0.05,
                                           read_timeout=0.3, reconnect_initial=0.05,
                                           reconnect_max=0.1), _worker_target=_frame_then_hung_worker)
    camera.start()
    try:
        assert _wait_until(lambda: camera.latest_frame() is not None)
        first = camera.latest_frame()
        assert first.image.shape == (2, 2, 3)
        assert (first.image == 77).all()
        assert _wait_until(lambda: camera.snapshot().state == "FAULT", timeout=2)
        assert _wait_until(lambda: camera.snapshot().reconnect_events >= 1)
        assert _wait_until(lambda: camera.latest_frame().sequence > first.sequence)
        assert camera.snapshot().captured_frames >= 2
    finally:
        camera.stop()


class _CaptureProperties:
    CAP_PROP_FRAME_WIDTH = "width"
    CAP_PROP_FRAME_HEIGHT = "height"
    CAP_PROP_FPS = "fps"
    CAP_PROP_FOURCC = "fourcc"

    @staticmethod
    def VideoWriter_fourcc(*characters):
        return sum(ord(character) << (8 * index) for index, character in enumerate(characters))


class _FormatResettingCapture:
    """Emulate a driver which switches back to YUY2 on mode changes."""

    def __init__(self, refuse_format=False):
        self.values = {"width": 640, "height": 480, "fps": 30,
                       "fourcc": _CaptureProperties.VideoWriter_fourcc(*"YUY2")}
        self.calls = []
        self.refuse_format = refuse_format

    def set(self, prop, value):
        self.calls.append(prop)
        if prop == "fourcc" and self.refuse_format:
            return False
        self.values[prop] = value
        if prop != "fourcc":
            self.values["fourcc"] = _CaptureProperties.VideoWriter_fourcc(*"YUY2")
        return True

    def get(self, prop):
        return self.values[prop]


def test_mjpg_is_requested_after_dimension_and_fps_changes_reset_format():
    capture = _FormatResettingCapture()
    actual = _configure_capture(capture, _CaptureProperties, CameraSettings(fps=15))
    assert capture.calls == ["width", "height", "fps", "fourcc"]
    assert actual["actual_fourcc"] == "MJPG"
    assert actual["actual_width"] == 1920
    assert actual["actual_height"] == 1080
    assert actual["actual_fps"] == 15
    assert actual["fourcc_request_accepted"] is True
    assert actual["negotiated_matches_request"] is True


def test_refused_format_is_reported_and_stream_mismatch_is_visible():
    capture = _FormatResettingCapture(refuse_format=True)
    actual = _configure_capture(capture, _CaptureProperties, CameraSettings())
    assert actual["actual_fourcc"] == "YUY2"
    assert actual["fourcc_request_accepted"] is False
    assert actual["negotiated_matches_request"] is False
    camera = CameraCapture()
    camera._accept({"kind": "opened", **actual})
    camera._accept({"kind": "frame", "image": object(), "captured_at": time.monotonic(),
                    "sequence": 1, **actual})
    metrics = camera.snapshot()
    assert metrics.state == "LIVE"
    assert metrics.negotiated_matches_request is False
    assert "differs" in metrics.detail
