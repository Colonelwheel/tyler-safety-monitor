"""Latest-frame camera capture with Windows driver calls isolated in a process.

Images exist only in memory. Native OpenCV calls cannot block the UI or prevent
shutdown: a parent receiver thread supervises and, when needed, terminates only
the process this instance owns. Frame age uses a monotonic clock, not wall time.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import multiprocessing as mp
from multiprocessing import shared_memory
import queue
import threading
import time
from typing import Any, Callable


@dataclass(frozen=True)
class CameraSettings:
    index: int = 0
    backend: str = "dshow"
    width: int = 1920
    height: int = 1080
    fps: int = 15
    stale_after: float = 3.0
    open_timeout: float = 15.0
    read_timeout: float = 6.0
    reconnect_initial: float = 1.0
    reconnect_max: float = 15.0

    def __post_init__(self) -> None:
        if self.backend not in {"dshow", "msmf"}:
            raise ValueError("Camera backend must be dshow or msmf")
        if self.index < 0 or min(self.width, self.height, self.fps) <= 0:
            raise ValueError("Camera index/dimensions/FPS are invalid")
        if min(self.stale_after, self.open_timeout, self.read_timeout,
               self.reconnect_initial, self.reconnect_max) <= 0:
            raise ValueError("Camera timeouts/backoff must be positive")
        if self.reconnect_initial > self.reconnect_max:
            raise ValueError("Initial reconnect delay exceeds maximum")


@dataclass(frozen=True)
class FramePacket:
    image: Any  # OpenCV BGR ndarray; consumers must copy before drawing on it.
    sequence: int
    captured_at: float


@dataclass(frozen=True)
class CameraMetrics:
    state: str = "STOPPED"
    detail: str = "Camera stopped"
    backend: str = "dshow"
    requested_width: int = 1920
    requested_height: int = 1080
    requested_fps: int = 30
    requested_fourcc: str = "MJPG"
    actual_width: int = 0
    actual_height: int = 0
    actual_fps: float = 0.0
    actual_fourcc: str = ""
    fourcc_request_accepted: bool | None = None
    negotiated_matches_request: bool | None = None
    delivered_fps: float = 0.0
    received_fps: float = 0.0
    frame_age: float | None = None
    brightness: float | None = None  # mean grayscale value, 0-255
    blur: float | None = None  # grayscale Laplacian variance, diagnostic only
    exposure: float | None = None  # backend-dependent OpenCV units
    read_failures: int = 0
    reconnect_events: int = 0
    captured_frames: int = 0
    received_frames: int = 0
    transfer_drops: int = 0
    cadence_gap_estimate: int = 0  # estimated gaps; NOT proven driver drops


def _fps(timestamps: deque[float]) -> float:
    if len(timestamps) < 2 or timestamps[-1] <= timestamps[0]:
        return 0.0
    return (len(timestamps) - 1) / (timestamps[-1] - timestamps[0])


def _put_latest(output: Any, message: dict[str, Any]) -> bool:
    """Bound memory use. Return whether an older transfer had to be discarded."""
    try:
        output.put_nowait(message)
        return False
    except queue.Full:
        try:
            output.get_nowait()
        except queue.Empty:
            pass
        try:
            output.put_nowait(message)
        except queue.Full:
            # The feeder may still own the slot. Never wait behind the consumer.
            return True
        return True


def _configure_capture(capture: Any, cv2: Any, settings: CameraSettings) -> dict[str, Any]:
    """Request stream properties, then read back negotiation without guessing.

    DirectShow may reset the format after dimension/FPS changes. Request MJPG
    last so the final change is the intended compressed stream format. A true
    set() result is recorded separately from the format actually negotiated.
    Exposure, autofocus, brightness and other persistent controls are untouched.
    """
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, settings.width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, settings.height)
    capture.set(cv2.CAP_PROP_FPS, settings.fps)
    accepted = bool(capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG")))
    raw_fourcc = int(capture.get(cv2.CAP_PROP_FOURCC))
    actual = {
        "actual_width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "actual_height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        "actual_fps": capture.get(cv2.CAP_PROP_FPS),
        "actual_fourcc": "".join(chr((raw_fourcc >> (8 * i)) & 255) for i in range(4)),
        "fourcc_request_accepted": accepted,
    }
    actual["negotiated_matches_request"] = (
        actual["actual_width"] == settings.width
        and actual["actual_height"] == settings.height
        and abs(actual["actual_fps"] - settings.fps) < 0.5
        and actual["actual_fourcc"] == "MJPG"
    )
    return actual


def _capture_worker(settings: CameraSettings, output: Any, stop: Any,
                    transport: dict[str, Any]) -> None:
    # Import in the child so loading a native library cannot freeze the UI.
    import cv2
    import numpy as np

    capture = None
    shared = shared_memory.SharedMemory(name=transport["name"])
    output.cancel_join_thread()
    try:
        backend = cv2.CAP_DSHOW if settings.backend == "dshow" else cv2.CAP_MSMF
        capture = cv2.VideoCapture(settings.index, backend)
        if not capture.isOpened():
            _put_latest(output, {"kind": "fault", "detail": "Camera open failed"})
            return
        # MJPG avoids the bandwidth limitation of an uncompressed 1080p stream.
        actual = _configure_capture(capture, cv2, settings)
        _put_latest(output, {"kind": "opened", **actual})
        times: deque[float] = deque(maxlen=max(30, settings.fps * 4))
        count = failures = consecutive_failures = drops = gaps = 0
        brightness = blur = exposure = None
        quality_at = 0.0
        while not stop.is_set():
            ok, frame = capture.read()
            now = time.monotonic()
            if not ok or frame is None or not frame.size:
                failures += 1
                consecutive_failures += 1
                _put_latest(output, {"kind": "read_failure", "read_failures": failures})
                if consecutive_failures >= 5:
                    _put_latest(output, {"kind": "fault", "detail": "Five consecutive camera reads failed"})
                    return
                stop.wait(0.1)
                continue
            consecutive_failures = 0
            if times:
                gaps += max(0, int((now - times[-1]) * settings.fps + 0.5) - 1)
            times.append(now)
            count += 1
            if frame.ndim != 3 or frame.shape[2] != 3 or frame.nbytes > shared.size:
                _put_latest(output, {"kind": "fault", "detail": "Unexpected or oversized camera frame"})
                return
            if now - quality_at >= 0.5:
                diagnostic = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(diagnostic, cv2.COLOR_BGR2GRAY)
                brightness = float(gray.mean())
                blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
                exposure = float(capture.get(cv2.CAP_PROP_EXPOSURE))
                quality_at = now
            if not transport["lock"].acquire(timeout=0.1):
                drops += 1
                continue
            try:
                np.copyto(np.ndarray(frame.shape, dtype=np.uint8, buffer=shared.buf), frame)
                transport["sequence"].value = count
            finally:
                transport["lock"].release()
            if _put_latest(output, {
                "kind": "frame", "shape": frame.shape, "captured_at": now,
                "sequence": count, "captured_frames": count,
                "delivered_fps": _fps(times), "read_failures": failures,
                "brightness": brightness, "blur": blur, "exposure": exposure,
                "transfer_drops": drops, "cadence_gap_estimate": gaps,
                **actual,
            }):
                drops += 1
    except Exception as exc:
        # Do not emit image contents, environment paths, or unrelated data.
        _put_latest(output, {"kind": "fault", "detail": f"Camera failure ({type(exc).__name__})"})
    finally:
        if capture is not None:
            capture.release()
        shared.close()


class CameraCapture:
    """Owned process + receiver thread. All public methods are non-UI-blocking.

    ``stop`` waits at most about two seconds for owned workers to exit. Snapshot
    and latest_frame are inexpensive reads; frame arrays are never written here
    after publication. Consumers should process each sequence only once.
    """

    def __init__(self, settings: CameraSettings | None = None, *,
                 _worker_target: Callable[..., None] = _capture_worker) -> None:
        self.settings = settings or CameraSettings()
        self._target = _worker_target
        self._context = mp.get_context("spawn")
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._retry = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest: FramePacket | None = None
        self._metrics = CameraMetrics(backend=self.settings.backend,
                                      requested_width=self.settings.width,
                                      requested_height=self.settings.height,
                                      requested_fps=self.settings.fps)
        self._received: deque[float] = deque(maxlen=self.settings.fps * 4)
        self._generation = 0
        self._counter_base = {key: 0 for key in
                              ("read_failures", "captured_frames", "transfer_drops", "cadence_gap_estimate")}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._retry.clear()
        self._thread = threading.Thread(target=self._supervise, name="camera-receiver", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._retry.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        with self._lock:
            self._latest = None
            self._metrics = replace(self._metrics, state="STOPPED", detail="Camera stopped")

    def retry(self) -> None:
        self._retry.set()

    def latest_frame(self) -> FramePacket | None:
        with self._lock:
            return self._latest

    def snapshot(self) -> CameraMetrics:
        with self._lock:
            result = self._metrics
            frame = self._latest
        age = None if frame is None else max(0.0, time.monotonic() - frame.captured_at)
        if result.state == "LIVE" and (age is None or age > self.settings.stale_after):
            return replace(result, state="FAULT", detail="Camera frame is stale", frame_age=age)
        return replace(result, frame_age=age)

    def _update(self, **changes: Any) -> None:
        with self._lock:
            self._metrics = replace(self._metrics, **changes)

    def _accept(self, message: dict[str, Any]) -> bool:
        kind = message["kind"]
        if kind == "fault":
            self._update(state="FAULT", detail=message["detail"])
            return False
        if kind == "read_failure":
            self._update(read_failures=self._counter_base["read_failures"] + message["read_failures"],
                         state="FAULT", detail="Camera read failed; retrying")
        if kind == "opened":
            self._update(state="STARTING", detail="Camera open; waiting for first frame",
                         **{key: value for key, value in message.items()
                            if key in CameraMetrics.__dataclass_fields__})
        if kind == "frame":
            self._received.append(message["captured_at"])
            with self._lock:
                self._latest = FramePacket(message["image"],
                                           (self._generation << 48) + message["sequence"],
                                           message["captured_at"])
                fields = {key: value for key, value in message.items()
                          if key in CameraMetrics.__dataclass_fields__}
                for key in self._counter_base:
                    if key in fields:
                        fields[key] += self._counter_base[key]
                negotiation = fields.get("negotiated_matches_request",
                                         self._metrics.negotiated_matches_request)
                detail = ("Camera live; negotiated stream differs from request"
                          if negotiation is False else "Camera live")
                self._metrics = replace(self._metrics, state="LIVE", detail=detail,
                                        received_frames=self._metrics.received_frames + 1,
                                        received_fps=_fps(self._received), **fields)
        return True

    def _supervise(self) -> None:
        delay = self.settings.reconnect_initial
        while not self._stop.is_set():
            self._retry.clear()
            self._generation += 1
            self._received.clear()
            with self._lock:
                self._counter_base = {key: getattr(self._metrics, key) for key in self._counter_base}
                self._metrics = replace(self._metrics, state="STARTING", detail="Opening camera",
                                        delivered_fps=0.0, received_fps=0.0)
            output = child_stop = shared = process = None
            last_frame = None
            started = time.monotonic()
            try:
                output = self._context.Queue(maxsize=2)
                child_stop = self._context.Event()
                # One bounded 4K BGR buffer, never a file or recording. Only small
                # metadata traverses the pipe, avoiding large partial image reads.
                shared = shared_memory.SharedMemory(create=True, size=4096 * 2160 * 3)
                transport = {"name": shared.name, "lock": self._context.Lock(),
                             "sequence": self._context.Value("q", 0, lock=False)}
                process = self._context.Process(target=self._target,
                                                args=(self.settings, output, child_stop, transport),
                                                name="tyler-camera", daemon=True)
                process.start()
                while not self._stop.is_set() and not self._retry.is_set():
                    try:
                        message = output.get(timeout=0.05)
                    except queue.Empty:
                        message = None
                    if message is not None:
                        if message["kind"] == "frame" and "image" not in message:
                            import numpy as np
                            if not transport["lock"].acquire(timeout=0.1):
                                continue
                            try:
                                if transport["sequence"].value != message["sequence"]:
                                    continue
                                message["image"] = np.ndarray(message["shape"], dtype=np.uint8,
                                                               buffer=shared.buf).copy()
                            finally:
                                transport["lock"].release()
                        if not self._accept(message):
                            break
                        if message["kind"] == "frame":
                            last_frame = message["captured_at"]
                            # Do not repeatedly reset backoff for a flapping camera.
                            if time.monotonic() - started > 10:
                                delay = self.settings.reconnect_initial
                    now = time.monotonic()
                    if not process.is_alive():
                        self._update(state="FAULT", detail="Camera worker exited; reconnecting")
                        break
                    if last_frame is None and now - started > self.settings.open_timeout:
                        self._update(state="FAULT", detail="Camera open/first-frame timeout; reconnecting")
                        break
                    if last_frame is not None and now - last_frame > self.settings.read_timeout:
                        self._update(state="FAULT", detail="Camera read timeout; reconnecting")
                        break
            except Exception as exc:
                self._update(state="FAULT", detail=f"Camera worker failure ({type(exc).__name__})")
            finally:
                if child_stop is not None:
                    child_stop.set()
                if process is not None and process.pid is not None:
                    process.join(timeout=0.3)
                    if process.is_alive():
                        process.terminate()
                        process.join(timeout=0.5)
                    if not process.is_alive():
                        process.close()
                if output is not None:
                    output.cancel_join_thread()
                    output.close()
                if shared is not None:
                    shared.close()
                    shared.unlink()
            if self._stop.is_set():
                break
            self._update(reconnect_events=self.snapshot().reconnect_events + 1)
            # Explicit Retry bypasses the automatic delay, including while waiting.
            if not self._retry.is_set():
                self._retry.wait(delay)
                delay = min(self.settings.reconnect_max, delay * 2)
