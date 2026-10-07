"""Optional memory-only face comparison; never supplies pose tracks or profiles."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import math
from pathlib import Path
import threading
import time

import numpy as np

from .pose import isolate_model_cache
from .scene import SceneConfig


@dataclass(frozen=True)
class HeadComparisonResult:
    timestamp_ms: int
    heads: tuple[tuple[float, float, float], ...]
    latency_ms: float
    scene_generation: int = 0
    below_cutoff_heads: int = 0


@dataclass(frozen=True)
class HeadComparisonStats:
    submitted: int = 0
    completed: int = 0
    dropped: int = 0
    no_face_frames: int = 0
    diagnostic_frames: int = 0
    low_score_frames: int = 0


def comparison_views(cropped):
    """Yield masked full ROI plus nine overlapping half-size tiles, rotated."""
    import cv2
    height, width = cropped.shape[:2]
    rectangles = [(0, 0, width, height)]
    tile_width, tile_height = math.ceil(width / 2), math.ceil(height / 2)
    for fraction_y in (0, .25, .5):
        for fraction_x in (0, .25, .5):
            x = min(width - tile_width, round(width * fraction_x))
            y = min(height - tile_height, round(height * fraction_y))
            rectangle = (x, y, tile_width, tile_height)
            if rectangle not in rectangles:
                rectangles.append(rectangle)
    for rectangle in rectangles:
        x, y, w, h = rectangle
        tile = cropped[y:y + h, x:x + w]
        for angle in (0, 30, -30):
            affine = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1)
            rotated = (np.ascontiguousarray(tile) if angle == 0 else
                       cv2.warpAffine(tile, affine, (w, h),
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0))
            yield rotated, rectangle, cv2.invertAffineTransform(affine)


def heads_from_result(result, scene, roi, tile, inverse, frame_width, frame_height):
    """Map the nose, or unavailable-keypoint box centre, to original coordinates."""
    heads = []
    # Limit malformed/unbounded native output without inventing an accepted head.
    for detection in result.detections[:16]:
        try:
            score = float(detection.categories[0].score)
            if not math.isfinite(score) or not .5 <= score <= 1:
                continue
            x, y, width, height = tile
            keypoints = detection.keypoints
            if keypoints is not None and len(keypoints) > 2:
                px, py = float(keypoints[2].x) * width, float(keypoints[2].y) * height
            else:
                box = detection.bounding_box
                if box.width <= 0 or box.height <= 0:
                    continue
                px = float(box.origin_x) + float(box.width) / 2
                py = float(box.origin_y) + float(box.height) / 2
            if not all(math.isfinite(v) for v in (px, py)):
                continue
            if not 0 <= px <= width or not 0 <= py <= height:
                continue
            unrotated = inverse @ np.array((px, py, 1.0))
            ux, uy = float(unrotated[0]), float(unrotated[1])
            # Reject rotation padding, even when it maps somewhere inside the ROI.
            if not (math.isfinite(ux) and math.isfinite(uy)
                    and 0 <= ux <= width and 0 <= uy <= height):
                continue
            head = scene.map_point(((x + ux) / roi[2], (y + uy) / roi[3]),
                                   roi, frame_width, frame_height)
            if scene.accepts_point(*head):
                heads.append((*head, score))
        except (AttributeError, IndexError, TypeError, ValueError, OverflowError):
            continue
    return tuple(heads)


def deduplicate_heads(heads):
    """Diagnostic spatial suppression only; no person identity is assigned."""
    kept = []
    for head in sorted(heads, key=lambda head: (-head[2], head[0], head[1])):
        if all(math.hypot(head[0] - other[0], head[1] - other[1]) > .035
               for other in kept):
            kept.append(head)
            if len(kept) == 16:
                break
    return tuple(kept)


def _validated_min_score(value):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not .5 <= value <= 1 or not math.isfinite(value)):
        raise ValueError("comparison minimum score must be finite and between 0.5 and 1")
    return float(value)


class HeadComparator:
    """IMAGE face worker, capped at two submitted frames per second.

    One native scan and one replaceable copied pending frame are retained.
    Initialization and inference faults are evaluated on status reads, allowing
    the UI to remain responsive even when the native thread is stuck.
    """
    def __init__(self, model_path: str | Path, scene: SceneConfig, min_score=.5):
        self._min_score = _validated_min_score(min_score)
        self.model_path = Path(model_path)
        self._scene = scene
        self._condition = threading.Condition()
        self._thread = None
        self._stopping = False
        self._pending = None
        self._active_at = None
        self._initializing_at = None
        self._last_submit_at = None
        self._last_scan_at = None
        self._last_timestamp = -1
        self._generation = 0
        self._ready = False
        self._error = ""
        self._latest = None
        self._stats = HeadComparisonStats()
        self._diagnostic_frames = deque(maxlen=32)

    @property
    def latest_result(self):
        # A fault must not leave an earlier successful result looking current.
        if self.error:
            return None
        with self._condition:
            return self._latest

    @property
    def stats(self):
        with self._condition:
            return self._stats

    @property
    def error(self):
        with self._condition:
            if not self._error and not self._stopping:
                now = time.monotonic()
                if self._initializing_at is not None and now - self._initializing_at >= 15:
                    self._error = "Head comparison initialization timed out. Restart application."
                elif self._active_at is not None and now - self._active_at >= 5:
                    self._error = "Head comparison inference stalled. Restart application."
                if self._error:
                    self._latest = None
                    self._condition.notify_all()
            return self._error

    @property
    def is_alive(self):
        return self._thread is not None and self._thread.is_alive()

    @property
    def ready(self):
        if self.error:
            return False
        with self._condition:
            return self._ready and not self._stopping

    def start(self):
        with self._condition:
            if self._thread is not None or self._stopping or self._error:
                return
            if not self.model_path.is_file():
                self._error = "Head comparison model missing; select an existing local model."
                return
            self._initializing_at = time.monotonic()
            self._thread = threading.Thread(target=self._run, name="head-comparison", daemon=True)
            self._thread.start()

    @property
    def min_score(self):
        with self._condition:
            return self._min_score

    def set_min_score(self, value):
        value = _validated_min_score(value)
        with self._condition:
            if value != self._min_score:
                self._min_score = value
                # Changing qualification must invalidate old and in-flight results.
                self.set_scene(self._scene)

    def set_scene(self, scene):
        with self._condition:
            self._scene = scene
            self._generation += 1
            self._latest = None
            self._diagnostic_frames.clear()
            self._stats = replace(self._stats, no_face_frames=0, diagnostic_frames=0,
                                  low_score_frames=0)
            if self._pending is not None:
                self._pending = None
                self._stats = replace(self._stats, dropped=self._stats.dropped + 1)

    def submit(self, frame, timestamp_ms=None):
        if self.error:
            return False
        with self._condition:
            if self._stopping or self._error or self._thread is None:
                return False
            now = time.monotonic()
            if self._last_submit_at is not None and now - self._last_submit_at < .5:
                return False
            if (not isinstance(frame, np.ndarray) or frame.ndim != 3
                    or frame.shape[2] != 3 or frame.dtype != np.uint8
                    or min(frame.shape[:2]) < 1):
                raise ValueError("comparison frame must be a nonempty uint8 BGR array")
            timestamp = int(now * 1000) if timestamp_ms is None else int(timestamp_ms)
            timestamp = max(timestamp, self._last_timestamp + 1)
            self._last_timestamp = timestamp
            self._last_submit_at = now
            self._stats = replace(self._stats, submitted=self._stats.submitted + 1,
                                  dropped=self._stats.dropped + (self._pending is not None))
            self._pending = (frame.copy(), timestamp, self._scene, self._generation,
                             self._min_score)
            self._condition.notify_all()
            return True

    def _finish(self, result):
        with self._condition:
            self._active_at = None
            self._stats = replace(self._stats, completed=self._stats.completed + 1)
            if (result.scene_generation == self._generation
                    and not self._stopping and not self._error):
                self._latest = result
                self._diagnostic_frames.append((result.timestamp_ms, not result.heads,
                                                not result.heads and result.below_cutoff_heads > 0))
                while (self._diagnostic_frames and
                       result.timestamp_ms - self._diagnostic_frames[0][0] > 10000):
                    self._diagnostic_frames.popleft()
                self._stats = replace(
                    self._stats, diagnostic_frames=len(self._diagnostic_frames),
                    no_face_frames=sum(entry[1] for entry in self._diagnostic_frames),
                    low_score_frames=sum(entry[2] for entry in self._diagnostic_frames))

    def _scan(self, detector, mp, frame, timestamp, scene, generation, min_score):
        import cv2
        started = time.monotonic()
        cropped, roi = scene.prepare_frame(frame)
        heads = []
        for view, tile, inverse in comparison_views(cropped):
            with self._condition:
                if self._stopping or self._error or generation != self._generation:
                    return None
            if self.error:
                return None
            rgb = cv2.cvtColor(view, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect(image)
            heads.extend(heads_from_result(result, scene, roi, tile, inverse,
                                            frame.shape[1], frame.shape[0]))
        # A final native call might itself return after the deadline.
        if self.error:
            return None
        mapped = deduplicate_heads(heads)
        qualifying = tuple(head for head in mapped if head[2] >= min_score)
        return HeadComparisonResult(timestamp, qualifying,
                                    (time.monotonic() - started) * 1000, generation,
                                    len(mapped) - len(qualifying))

    def _run(self):
        try:
            isolate_model_cache()
            import mediapipe as mp
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision
            options = vision.FaceDetectorOptions(
                base_options=python.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.IMAGE,
                min_detection_confidence=.5, min_suppression_threshold=.3)
            with vision.FaceDetector.create_from_options(options) as detector:
                with self._condition:
                    if self._stopping or self.error:
                        return
                    self._ready = True
                    self._initializing_at = None
                while True:
                    with self._condition:
                        self._condition.wait_for(lambda: self._stopping or self._error
                                                  or self._pending is not None)
                        if self._stopping or self._error:
                            return
                        now = time.monotonic()
                        remaining = (0 if self._last_scan_at is None else
                                     .5 - (now - self._last_scan_at))
                        if remaining > 0:
                            self._condition.wait(timeout=remaining)
                            continue
                        self._last_scan_at = now
                        frame, timestamp, scene, generation, min_score = self._pending
                        self._pending = None
                        self._active_at = time.monotonic()
                    result = self._scan(detector, mp, frame, timestamp, scene, generation, min_score)
                    if result is not None:
                        self._finish(result)
                    else:
                        with self._condition:
                            self._active_at = None
        except Exception as error:
            with self._condition:
                self._error = ("Head comparison initialization/inference failed "
                               f"({type(error).__name__}). Restart application.")
                self._latest = None
                self._active_at = None
                self._condition.notify_all()
        finally:
            with self._condition:
                self._ready = False

    def close(self):
        """Keep an unfinished native worker referenced; refuse to restart it."""
        with self._condition:
            self._stopping = True
            self._ready = False
            self._latest = None
            self._pending = None
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=1)
        stopped = not self.is_alive
        if not stopped:
            with self._condition:
                self._error = "Head comparison worker did not stop; exit/restart application."
        return stopped
