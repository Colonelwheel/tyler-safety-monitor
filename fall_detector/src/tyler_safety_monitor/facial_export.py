"""Optional face crop sharing; never opens a camera or changes safety settings."""
from __future__ import annotations

import threading
import time

import cv2
import numpy as np

from .frame_feed import MAX_HEIGHT, MAX_WIDTH, SharedFramePublisher


def prepare_face_crop(image, rect, exclusions):
    """Copy the requested face rectangle, apply exclusion intersections, shrink.

    The safety ROI determines pose inference coverage, not the optional face
    crop. Its exclusions remain privacy boundaries in both paths. Never upscale.
    """
    if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
            or image.ndim != 3 or image.shape[2] != 3):
        raise ValueError("camera frame must be uint8 BGR")
    height, width = image.shape[:2]
    x, y, w, h = rect.to_pixels(width, height)
    crop = image[y:y + h, x:x + w].copy()
    for exclusion in exclusions:
        mx, my, mw, mh = exclusion.to_pixels(width, height)
        left, top = max(x, mx), max(y, my)
        right, bottom = min(x + w, mx + mw), min(y + h, my + mh)
        if right > left and bottom > top:
            crop[top - y:bottom - y, left - x:right - x] = 0
    scale = min(1.0, MAX_WIDTH / w, MAX_HEIGHT / h)
    if scale < 1:
        crop = cv2.resize(crop, (max(1, int(w * scale)), max(1, int(h * scale))),
                          interpolation=cv2.INTER_AREA)
    return np.ascontiguousarray(crop)


class FacialFrameExport:
    """Optional independent latest-frame worker; disabled initially/per launch.

    The monitor's capture receiver, pose pipeline, UI refresh and source queues
    have no calls into this worker. Its sole camera interaction is snapshot plus
    latest_frame, both reference reads. There is no consumer IPC or growing queue.
    """

    def __init__(self, name=None, *, poll_fps=30, clock=time.monotonic,
                 publisher_factory=SharedFramePublisher):
        if poll_fps not in (10, 15, 20, 30):
            raise ValueError("export poll FPS must be 10, 15, 20, or 30")
        self.name = name
        self.poll_fps = poll_fps
        self.clock = clock
        self.publisher_factory = publisher_factory
        self.crop = None
        self.status = "Off • select a face region, then Enable Face Sharing."
        self._source = None
        self._scene = None
        self._capture_generation = 0
        self._scene_generation = 0
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._publisher = None
        self._camera_generation = None
        self._last_sequence = None
        self._last_context = None
        self.published = 0

    @property
    def enabled(self):
        return self._thread is not None and self._thread.is_alive() and not self._stop.is_set()

    def set_source(self, capture, scene, capture_generation):
        # Called only after stopping sharing on a deliberate camera/scene change.
        with self._lock:
            self._source = capture
            self._scene = scene
            self._capture_generation = capture_generation
            self._scene_generation += 1

    def select_crop(self, rect):
        self.stop("Off • face region selected. Enable sharing explicitly.")
        self.crop = rect
        self._scene_generation += 1

    def invalidate_geometry(self, reason):
        self.stop("Off • " + reason + " Select the face region again before enabling.")
        self.crop = None

    def start(self):
        if self.enabled:
            return True
        if self._thread is not None and self._thread.is_alive():
            self.status = "Waiting for previous face-sharing worker to finish; retry Enable."
            return False
        if self.crop is None:
            self.status = "Off • select a face region using two separate taps first."
            return False
        if self._source is None or self._source.snapshot().state != "LIVE":
            self.status = "Off • start the camera and wait for its live view first."
            return False
        try:
            self._publisher = self.publisher_factory(self.name)
        except (FileExistsError, OSError, ValueError):
            self.status = "Off • sharing unavailable; feed already owned or allocation failed. No existing feed changed."
            return False
        self._camera_generation = None
        self._last_sequence = None
        self._last_context = None
        self._stop.clear()
        self.status = "Starting face sharing • memory only."
        self._thread = threading.Thread(target=self._run, name="face-frame-export", daemon=True)
        self._thread.start()
        return True

    def stop(self, reason="Off • face sharing disabled."):
        self._stop.set()
        with self._lock:
            if self._publisher is not None:
                self._publisher.invalidate()
        self.status = reason

    def close(self):
        self.stop()
        if self._thread is not None:
            self._thread.join(timeout=0.5)

    def _step(self):
        with self._lock:
            context = (self._source, self._scene, self.crop,
                       self._capture_generation, self._scene_generation)
        capture, scene, crop, capture_generation, scene_generation = context
        if self._stop.is_set() or capture is None or scene is None or crop is None:
            return
        metrics = capture.snapshot()
        packet = capture.latest_frame() if metrics.state == "LIVE" else None
        if packet is None or not 0 <= self.clock() - packet.captured_at <= 0.250:
            with self._lock:
                if not self._stop.is_set() and self._publisher is not None:
                    self._publisher.invalidate()
                    self.status = "Waiting for a fresh live camera frame • game output must pause."
            return
        camera_generation = (capture_generation << 32) | (packet.sequence >> 48)
        if self._camera_generation is None:
            self._camera_generation = camera_generation
        elif camera_generation != self._camera_generation:
            self._stop.set()
            self.crop = None
            self.status = "Off • camera reconnected. Select the face region again and Enable."
            return
        if packet.sequence == self._last_sequence and context == self._last_context:
            return
        image = prepare_face_crop(packet.image, crop, scene.exclusions)
        # A UI stop/scene change during preparation cannot publish an old crop.
        with self._lock:
            if self._stop.is_set() or context != (self._source, self._scene, self.crop,
                                                 self._capture_generation, self._scene_generation):
                return
            self._publisher.publish(image, packet.captured_at, packet.sequence,
                                    camera_generation, scene_generation)
            self.published += 1
            self._last_sequence = packet.sequence
            self._last_context = context
            self.status = (f"Sharing face crop {image.shape[1]} × {image.shape[0]} • memory only; "
                           "no camera settings changed. Check actual facial detail in Test.")

    def _run(self):
        try:
            while not self._stop.is_set():
                self._step()
                self._stop.wait(1 / self.poll_fps)
        except Exception as exc:
            self._stop.set()
            self.status = f"Off • face-sharing fault ({type(exc).__name__}); monitor continues."
        finally:
            with self._lock:
                if self._publisher is not None:
                    self._publisher.close()
                    self._publisher = None
