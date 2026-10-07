from pathlib import Path
from types import SimpleNamespace as NS
import sys
import threading
import time

import cv2
import numpy as np
import pytest

import tyler_safety_monitor.head_comparison as comparison
from tyler_safety_monitor.head_comparison import (
    HeadComparator, HeadComparisonResult, comparison_views, heads_from_result,
    deduplicate_heads,
)
from tyler_safety_monitor.scene import Rect, SceneConfig


def detection(x=.5, y=.5, score=.9, keypoints=True):
    return NS(categories=[NS(score=score)],
              keypoints=[NS(x=x, y=y) for _ in range(6)] if keypoints else [],
              bounding_box=NS(origin_x=40, origin_y=30, width=20, height=40))


def converted(det, scene=SceneConfig(), inverse=None, tile=(0, 0, 100, 100),
              roi=(0, 0, 100, 100), dimensions=(100, 100)):
    return heads_from_result(NS(detections=[det]), scene, roi, tile,
                             np.array([[1., 0, 0], [0, 1., 0]]) if inverse is None else inverse,
                             *dimensions)


def test_rotated_tile_inverse_returns_original_camera_point():
    scene = SceneConfig(Rect(.1, .2, .6, .6))
    roi = scene.roi.to_pixels(1000, 1000)
    tile = (150, 100, 300, 300)
    expected_pixel = np.array([180., 120., 1.])
    for angle in (0, 30, -30):
        affine = cv2.getRotationMatrix2D((150, 150), angle, 1)
        rotated = affine @ expected_pixel
        heads = converted(detection(rotated[0] / 300, rotated[1] / 300),
                          scene, cv2.invertAffineTransform(affine), tile, roi,
                          (1000, 1000))
        assert heads[0] == pytest.approx((.43, .42, .9))


def test_missing_keypoints_use_box_center_but_bad_nose_is_rejected():
    assert converted(detection(keypoints=False))[0] == (.5, .5, .9)
    assert not converted(detection(x=float("nan")))
    assert not converted(detection(x=-.1))
    assert not converted(detection(x=1.1))
    assert not converted(detection(score=float("nan")))
    assert not converted(detection(score=1.1))
    assert not converted(detection(score=.49))


def test_malformed_detection_is_rejected_without_discarding_valid_neighbor():
    bad = detection()
    bad.categories = []
    result = NS(detections=[bad, NS(), detection()])
    heads = heads_from_result(result, SceneConfig(), (0, 0, 100, 100),
                              (0, 0, 100, 100), np.eye(2, 3), 100, 100)
    assert heads == ((.5, .5, .9),)
    bad_box = detection(keypoints=False)
    bad_box.bounding_box.width = -1
    assert not converted(bad_box)


def test_excluded_points_and_rotation_padding_rejected():
    masked = SceneConfig(exclusions=(Rect(.4, .4, .2, .2),))
    assert not converted(detection(), masked)
    # The detected point is in rotated canvas, but its source lies in padding.
    inverse = np.array([[1., 0, -60], [0, 1., 0]])
    assert not converted(detection(), inverse=inverse)
    assert not converted(detection(), inverse=np.full((2, 3), float("nan")))


def test_scan_views_are_generic_masked_geometry_and_all_rotations():
    scene = SceneConfig(exclusions=(Rect(.4, .4, .2, .2),))
    cropped, _ = scene.prepare_frame(np.full((100, 200, 3), 255, np.uint8))
    views = list(comparison_views(cropped))
    assert len(views) == 30
    rectangles = {rectangle for _, rectangle, _ in views}
    assert len(rectangles) == 10
    assert (0, 0, 200, 100) in rectangles
    assert {(x, y, 100, 50) for x in (0, 50, 100) for y in (0, 25, 50)} <= rectangles
    assert np.all(views[0][0][40:60, 80:120] == 0)
    assert np.array_equal(views[0][2], np.eye(2, 3))
    assert not np.array_equal(views[1][2], views[2][2])


def test_diagnostic_dedup_preserves_separate_heads_and_highest_score():
    first = (.5, .5, .8)
    best = (.51, .5, .95)
    separate = (.6, .5, .9)
    assert deduplicate_heads((first, best, separate)) == (best, separate)


def test_missing_model_never_imports_native_library_or_downloads(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _path: False)
    worker = HeadComparator("absent.tflite", SceneConfig())
    worker.start()
    assert "model missing" in worker.error
    assert worker._thread is None
    assert not worker.ready
    assert not worker.submit(np.zeros((2, 2, 3), np.uint8))
    assert worker.close()


class FakeThread:
    def __init__(self, alive=True):
        self.alive = alive
        self.joins = []

    def is_alive(self):
        return self.alive

    def join(self, timeout):
        self.joins.append(timeout)


def test_rate_limit_and_newest_owned_mailbox_copy(monkeypatch):
    clock = [20.]
    monkeypatch.setattr(comparison.time, "monotonic", lambda: clock[0])
    worker = HeadComparator("unused", SceneConfig())
    worker._thread = FakeThread()
    source = np.full((4, 4, 3), 1, np.uint8)
    assert worker.submit(source, 10)
    source[:] = 2
    clock[0] += .499
    assert not worker.submit(source, 10)
    assert worker.stats.submitted == 1
    assert worker._pending[0].mean() == 1
    clock[0] = 20.5
    assert worker.submit(source, 10)
    source[:] = 9
    assert worker._pending[0].mean() == 2
    assert worker._pending[1] == 11
    assert worker.stats.submitted == 2
    assert worker.stats.dropped == 1


def test_invalid_frame_does_not_consume_submission_or_timestamp():
    worker = HeadComparator("unused", SceneConfig())
    worker._thread = FakeThread()
    for invalid in (np.zeros((2, 2)), np.zeros((2, 2, 3)), np.zeros((0, 2, 3), np.uint8)):
        with pytest.raises(ValueError):
            worker.submit(invalid, 10)
    assert worker._pending is None
    assert worker._last_timestamp == -1
    assert worker.stats.submitted == 0


def test_current_scene_counts_expire_and_late_result_cannot_restore():
    worker = HeadComparator("unused", SceneConfig())
    worker._finish(HeadComparisonResult(100, (), 1, 0))
    worker._finish(HeadComparisonResult(200, ((.5, .5, .9),), 1, 0))
    assert worker.stats.no_face_frames == 1
    assert worker.stats.diagnostic_frames == 2
    worker._finish(HeadComparisonResult(10200, (), 1, 0))
    assert worker.stats.no_face_frames == 1
    assert worker.stats.diagnostic_frames == 2
    worker.set_scene(SceneConfig())
    assert worker.latest_result is None
    assert worker.stats.no_face_frames == worker.stats.diagnostic_frames == 0
    worker._finish(HeadComparisonResult(10300, ((.4, .4, .9),), 1, 0))
    assert worker.latest_result is None
    assert worker.stats.diagnostic_frames == 0
    assert worker.stats.completed == 4
    worker._finish(HeadComparisonResult(10400, (), 1, 1))
    assert worker.latest_result.scene_generation == 1
    assert worker.stats.diagnostic_frames == worker.stats.no_face_frames == 1


def test_scene_change_discards_pending_copy_and_keeps_lifetime_counts():
    worker = HeadComparator("unused", SceneConfig())
    worker._thread = FakeThread()
    worker.submit(np.zeros((2, 2, 3), np.uint8), 10)
    worker.set_scene(SceneConfig())
    assert worker._pending is None
    assert worker.stats.submitted == worker.stats.dropped == 1


@pytest.mark.parametrize("phase, elapsed, expected", [
    ("initializing", 16, "initialization timed out"),
    ("active", 6, "inference stalled"),
])
def test_native_timeout_is_visible_without_return_and_rejects_late_success(phase, elapsed, expected):
    worker = HeadComparator("unused", SceneConfig())
    worker._thread = FakeThread()
    worker._ready = phase == "active"
    worker._latest = HeadComparisonResult(10, ((.5, .5, .9),), 1, 0)
    setattr(worker, "_initializing_at" if phase == "initializing" else "_active_at",
            time.monotonic() - elapsed)
    assert expected in worker.error
    assert not worker.ready
    assert worker.is_alive
    assert worker.latest_result is None
    worker._finish(HeadComparisonResult(11, ((.5, .5, .9),), 1, 0))
    assert worker.latest_result is None
    assert worker.stats.diagnostic_frames == 0
    assert not worker.submit(np.zeros((2, 2, 3), np.uint8))


def test_hung_worker_reference_retained_and_instance_cannot_be_restarted():
    worker = HeadComparator("unused", SceneConfig())
    thread = FakeThread()
    worker._thread = thread
    assert not worker.close()
    assert thread.joins == [1]
    assert worker._thread is thread
    assert worker.is_alive
    assert "did not stop" in worker.error
    worker.start()
    assert worker._thread is thread
    thread.alive = False
    assert worker.close()
    worker.start()
    assert worker._thread is thread


def native_fakes(monkeypatch, detector):
    monkeypatch.setattr(comparison, "isolate_model_cache", lambda: None)
    python = NS(BaseOptions=lambda **kwargs: kwargs)
    vision = NS(FaceDetectorOptions=lambda **kwargs: kwargs,
                RunningMode=NS(IMAGE="IMAGE"),
                FaceDetector=NS(create_from_options=lambda options: detector))
    python.vision = vision
    mp = NS(Image=lambda **kwargs: kwargs["data"], ImageFormat=NS(SRGB="SRGB"))
    tasks = NS(python=python)
    monkeypatch.setitem(sys.modules, "mediapipe", mp)
    monkeypatch.setitem(sys.modules, "mediapipe.tasks", tasks)
    monkeypatch.setitem(sys.modules, "mediapipe.tasks.python", python)
    monkeypatch.setattr(Path, "is_file", lambda _path: True)


class Detector:
    def __init__(self, output=None):
        self.output = output if output is not None else NS(detections=[])
        self.calls = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True

    def detect(self, _image):
        self.calls += 1
        return self.output


def wait_until(predicate):
    deadline = time.monotonic() + 2
    while not predicate():
        if time.monotonic() >= deadline:
            pytest.fail("synthetic worker did not finish")
        time.sleep(.005)


def test_full_worker_scans_thirty_views_without_recording_or_network(monkeypatch):
    detector = Detector()
    native_fakes(monkeypatch, detector)
    worker = HeadComparator("unused", SceneConfig())
    worker.start()
    wait_until(lambda: worker.ready)
    assert worker.submit(np.zeros((20, 40, 3), np.uint8), 100)
    wait_until(lambda: worker.stats.completed == 1)
    assert detector.calls == 30
    assert worker.latest_result.heads == ()
    assert worker.latest_result.timestamp_ms == 100
    assert worker.stats.no_face_frames == worker.stats.diagnostic_frames == 1
    assert worker.close()
    assert detector.closed


def test_bad_native_result_is_visible_fault_not_success(monkeypatch):
    detector = Detector(output=NS())
    native_fakes(monkeypatch, detector)
    worker = HeadComparator("unused", SceneConfig())
    worker.start()
    wait_until(lambda: worker.ready)
    worker.submit(np.zeros((20, 40, 3), np.uint8), 100)
    wait_until(lambda: bool(worker.error))
    assert "inference failed (AttributeError)" in worker.error
    assert worker.latest_result is None
    assert worker.stats.completed == 0
    assert worker.close()


def test_scene_change_during_native_scan_never_publishes_old_head(monkeypatch):
    entered, release = threading.Event(), threading.Event()

    class BlockingDetector(Detector):
        def detect(self, _image):
            entered.set()
            assert release.wait(2)
            return NS(detections=[detection()])

    detector = BlockingDetector()
    native_fakes(monkeypatch, detector)
    worker = HeadComparator("unused", SceneConfig())
    worker.start()
    wait_until(lambda: worker.ready)
    worker.submit(np.zeros((20, 40, 3), np.uint8), 100)
    assert entered.wait(1)
    worker.set_scene(SceneConfig(exclusions=(Rect(.1, .1, .2, .2),)))
    release.set()
    wait_until(lambda: worker._active_at is None)
    assert worker.latest_result is None
    assert worker.stats.diagnostic_frames == 0
    assert worker.close()


def test_dedup_output_capped_without_merging_distinct_estimates():
    heads = tuple((i * .1, j * .1, .9) for i in range(10) for j in range(10))
    result = deduplicate_heads(heads)
    assert len(result) == 16
    assert all(head in heads for head in result)
    assert all(np.hypot(a[0] - b[0], a[1] - b[1]) > .035
               for index, a in enumerate(result) for b in result[index + 1:])


def test_scan_start_rate_cap_survives_an_immediate_pending_frame(monkeypatch):
    detector = Detector()
    native_fakes(monkeypatch, detector)
    starts = []

    def scan(_detector, _mp, _frame, timestamp, _scene, generation):
        starts.append(time.monotonic())
        return HeadComparisonResult(timestamp, (), 0, generation)

    worker = HeadComparator("unused", SceneConfig())
    monkeypatch.setattr(worker, "_scan", scan)
    worker.start()
    wait_until(lambda: worker.ready)
    worker.submit(np.zeros((2, 2, 3), np.uint8), 100)
    wait_until(lambda: worker.stats.completed == 1)
    # Bypass only submission throttling to exercise the independent worker cap.
    worker._last_submit_at = None
    worker.submit(np.zeros((2, 2, 3), np.uint8), 101)
    wait_until(lambda: worker.stats.completed == 2)
    assert starts[1] - starts[0] >= .49
    assert worker.close()
