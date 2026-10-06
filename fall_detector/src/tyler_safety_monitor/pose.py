"""Local pose observations only; no risk decisions or caregiver classification."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import math
import os
from pathlib import Path
import threading
import time
from typing import Callable

from .scene import SceneConfig
from .tracking import PoseObservation


def isolate_model_cache() -> None:
    """Prevent a transitive matplotlib import touching the user's shared cache."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is required for isolated model caches")
    cache = Path(local_app_data) / "TylerSafetyMonitor" / "cache" / "matplotlib"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["MPLCONFIGDIR"] = str(cache)


@dataclass(frozen=True)
class PoseResult:
    timestamp_ms: int
    observations: tuple[PoseObservation, ...]
    latency_ms: float
    scene_generation: int = 0


@dataclass(frozen=True)
class PoseStats:
    submitted: int = 0
    completed: int = 0
    dropped: int = 0
    raw_poses: int = 0
    accepted_heads: int = 0
    diagnostic_frames: int = 0
    no_pose_frames: int = 0
    rejected_head_frames: int = 0


def observations_from_result(result, scene: SceneConfig, roi_pixels,
                             frame_width: int, frame_height: int,
                             threshold: float = 0.5) -> tuple[PoseObservation, ...]:
    """Reject invisible/excluded heads and map crop coordinates to the scene.

    Confidence is a landmark visibility/presence score, not danger probability.
    A missing torso never disqualifies an otherwise visible head.
    """
    observations = []
    for landmarks in result.pose_landmarks:
        if any(not all(math.isfinite(value) for value in (p.x, p.y, p.z))
               for p in landmarks):
            continue
        def visible(index):
            if index >= len(landmarks):
                return False
            point = landmarks[index]
            values = (point.x, point.y, point.z,
                      getattr(point, "visibility", 0.0),
                      getattr(point, "presence", 0.0))
            return (all(value is not None and math.isfinite(value) for value in values)
                    and min(values[3:]) >= threshold
                    and 0 <= point.x <= 1 and 0 <= point.y <= 1)

        # Eyes/ears/nose establish a head center without requiring a full body.
        face = [index for index in (0, 2, 5, 7, 8) if visible(index)]
        if not face:
            continue
        head_crop = (sum(landmarks[i].x for i in face) / len(face),
                     sum(landmarks[i].y for i in face) / len(face))
        head = scene.map_point(head_crop, roi_pixels, frame_width, frame_height)
        if not scene.accepts_point(*head):
            continue
        shoulders = None
        if visible(11) and visible(12):
            shoulders = scene.map_point(
                ((landmarks[11].x + landmarks[12].x) / 2,
                 (landmarks[11].y + landmarks[12].y) / 2),
                roi_pixels, frame_width, frame_height)
        mapped = []
        scores = []
        for point in landmarks:
            x, y = scene.map_point((point.x, point.y), roi_pixels,
                                   frame_width, frame_height)
            mapped.append((x, y, point.z * roi_pixels[2] / frame_width))
            # Unavailable metadata is represented as zero visibility/presence;
            # this never promotes an invisible landmark into a visible head.
            pair = tuple(getattr(point, name, None) for name in ("visibility", "presence"))
            scores.append(tuple(value if value is not None and math.isfinite(value) else 0.0
                                for value in pair))
        confidence = sum(min(landmarks[i].visibility, landmarks[i].presence)
                         for i in face) / len(face)
        observations.append(PoseObservation(head=head, shoulders=shoulders,
                                            confidence=confidence,
                                            landmarks=tuple(mapped),
                                            landmark_scores=tuple(scores)))
    return tuple(observations)


class PoseWorker:
    """LIVE_STREAM worker with one active input and one replaceable newest frame.

    Capture stays responsive, old queued frames never build up, and inference
    skips are counted separately from camera read failures. No model download
    occurs implicitly. A hung callback becomes a visible fault after 5 seconds.
    """
    def __init__(self, model_path: str | Path, scene: SceneConfig,
                 num_poses: int = 2, on_result: Callable[[PoseResult], None] | None = None):
        if num_poses < 1:
            raise ValueError("num_poses must be positive")
        self.model_path = Path(model_path)
        self.num_poses = num_poses
        self.on_result = on_result
        self._scene = scene
        self._condition = threading.Condition()
        self._pending = None
        self._active = None
        self._thread = None
        self._stopping = False
        self._latest = None
        self._stats = PoseStats()
        self._diagnostic_frames = deque(maxlen=1024)
        self._error = ""
        self._last_timestamp = -1
        self._generation = 0
        self._initializing_at = None
        self._ready = False

    @property
    def latest_result(self) -> PoseResult | None:
        with self._condition:
            return self._latest

    @property
    def stats(self) -> PoseStats:
        with self._condition:
            return self._stats

    @property
    def error(self) -> str:
        with self._condition:
            if (not self._error and not self._ready and not self._stopping
                    and self._initializing_at is not None
                    and time.monotonic() - self._initializing_at >= 15):
                self._error = "Pose initialization timed out. Restart Detector."
                self._condition.notify_all()
            return self._error

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def ready(self) -> bool:
        # Reading error also evaluates the native startup timeout.
        if self.error:
            return False
        with self._condition:
            return self._ready and not self._stopping

    def start(self):
        if self._thread is not None:
            return
        if not self.model_path.is_file():
            self._error = "Pose model missing; select a local .task model in Settings."
            return
        self._thread = threading.Thread(target=self._run, name="pose-inference", daemon=True)
        self._initializing_at = time.monotonic()
        self._thread.start()

    def set_scene(self, scene: SceneConfig):
        with self._condition:
            self._scene = scene
            self._generation += 1
            # Results for the old crop must not be presented as current settings.
            self._latest = None
            self._diagnostic_frames.clear()
            self._stats = replace(self._stats, raw_poses=0, accepted_heads=0,
                                  diagnostic_frames=0, no_pose_frames=0, rejected_head_frames=0)
            if self._pending is not None:
                self._pending = None
                self._stats = replace(self._stats, dropped=self._stats.dropped + 1)

    def submit(self, frame_bgr, timestamp_ms: int | None = None) -> bool:
        with self._condition:
            if self._stopping or self._error or self._thread is None:
                return False
            timestamp = (int(time.monotonic() * 1000) if timestamp_ms is None
                         else int(timestamp_ms))
            timestamp = max(timestamp, self._last_timestamp + 1)
            self._last_timestamp = timestamp
            dropped = self._stats.dropped + (self._pending is not None)
            self._stats = replace(self._stats, submitted=self._stats.submitted + 1, dropped=dropped)
            # The source is owned by capture; copy for safe asynchronous use.
            self._pending = (frame_bgr.copy(), timestamp, self._scene, self._generation)
            self._condition.notify_all()
            return True

    def _callback(self, result, _image, timestamp_ms):
        with self._condition:
            context = self._active
            if context is None or context[0] != timestamp_ms:
                return
            _, scene, roi, width, height, started, generation = context
            try:
                converted = PoseResult(timestamp_ms, observations_from_result(
                    result, scene, roi, width, height), (time.monotonic() - started) * 1000,
                    generation)
            except Exception:
                # Never propagate a malformed native result through its callback
                # dispatcher or leave the worker silently awaiting that result.
                self._error = "Invalid pose result. Restart Detector."
                self._active = None
                self._condition.notify_all()
                return
            self._active = None
            self._stats = replace(self._stats, completed=self._stats.completed + 1)
            if generation == self._generation and not self._stopping:
                raw_count = len(result.pose_landmarks)
                accepted_count = len(converted.observations)
                # Counts and booleans only; no additional imagery or landmarks.
                self._diagnostic_frames.append((timestamp_ms, raw_count == 0,
                                                raw_count > 0 and accepted_count == 0))
                while self._diagnostic_frames and timestamp_ms - self._diagnostic_frames[0][0] > 10000:
                    self._diagnostic_frames.popleft()
                self._stats = replace(self._stats, raw_poses=raw_count, accepted_heads=accepted_count,
                                      diagnostic_frames=len(self._diagnostic_frames),
                                      no_pose_frames=sum(frame[1] for frame in self._diagnostic_frames),
                                      rejected_head_frames=sum(frame[2] for frame in self._diagnostic_frames))
                self._latest = converted
            self._condition.notify_all()
            deliver = generation == self._generation and not self._stopping
        if deliver and self.on_result:
            try:
                self.on_result(converted)
            except Exception:
                with self._condition:
                    self._error = "Pose result consumer failed. Restart Detector."

    def _run(self):
        try:
            import cv2
            isolate_model_cache()
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.LIVE_STREAM,
                num_poses=self.num_poses,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                result_callback=self._callback)
            with vision.PoseLandmarker.create_from_options(options) as detector:
                with self._condition:
                    self._ready = True
                    self._initializing_at = None
                while True:
                    with self._condition:
                        self._condition.wait_for(lambda: self._stopping or self._error or
                                                  self._pending is not None)
                        if self._stopping or self._error:
                            return
                        frame, timestamp, scene, generation = self._pending
                        self._pending = None
                    cropped, roi = scene.prepare_frame(frame)
                    rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                    image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                    with self._condition:
                        self._active = (timestamp, scene, roi, frame.shape[1],
                                        frame.shape[0], time.monotonic(), generation)
                    detector.detect_async(image, timestamp)
                    with self._condition:
                        completed = self._condition.wait_for(
                            lambda: self._active is None or self._stopping, timeout=5)
                        if not completed:
                            self._error = "Pose inference stalled. Restart Detector."
                            return
                        if self._stopping:
                            return
        except Exception as error:
            with self._condition:
                self._error = f"Pose initialization/inference failed ({type(error).__name__}). Restart Detector."
                self._active = None
                self._condition.notify_all()
        finally:
            with self._condition:
                self._ready = False

    def close(self) -> bool:
        """Request exit and report whether native inference actually stopped.

        Callers must retain an unfinished worker and prevent replacement until
        is_alive becomes false, avoiding accumulation after native hangs.
        """
        with self._condition:
            self._stopping = True
            self._ready = False
            self._pending = None
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=1)
        stopped = not self.is_alive
        if not stopped:
            with self._condition:
                self._error = "Pose worker did not stop; exit/restart application before retrying."
        return stopped
