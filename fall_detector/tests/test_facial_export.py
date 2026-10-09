from types import SimpleNamespace
from uuid import uuid4
import time

import numpy as np

from tyler_safety_monitor.facial_export import FacialFrameExport, prepare_face_crop
from tyler_safety_monitor.scene import Rect, SceneConfig


class Publisher:
    def __init__(self, name=None):
        self.frames = []
        self.invalidated = 0
        self.closed = False
    def publish(self, *args):
        self.frames.append(args)
    def invalidate(self):
        self.invalidated += 1
    def close(self):
        self.closed = True


class Camera:
    def __init__(self):
        self.state = "LIVE"
        self.packet = SimpleNamespace(image=np.full((100, 200, 3), 100, np.uint8),
                                      sequence=(1 << 48) + 1, captured_at=10.0)
    def snapshot(self):
        return SimpleNamespace(state=self.state)
    def latest_frame(self):
        return self.packet


def configured():
    exporter = FacialFrameExport(clock=lambda: 10.1, publisher_factory=Publisher)
    camera = Camera()
    exporter.set_source(camera, SceneConfig(exclusions=(Rect(.3, .3, .1, .1),)), 5)
    exporter.select_crop(Rect(.2, .2, .5, .5))
    exporter._stop.clear()
    exporter._publisher = Publisher()
    return exporter, camera


def test_crop_first_exclusion_intersections_and_never_changes_original():
    image = np.full((100, 200, 3), 100, np.uint8)
    cropped = prepare_face_crop(image, Rect(.2, .2, .5, .5), (Rect(.3, .3, .1, .1),))
    assert cropped.shape == (50, 100, 3)
    assert np.all(cropped[10:20, 20:40] == 0)
    assert np.all(cropped[:10] == 100) and np.all(image == 100)
    small = prepare_face_crop(image, Rect(.1, .1, .1, .1), ())
    assert small.shape == (10, 20, 3)  # no pretend detail through upscaling
    large = prepare_face_crop(np.zeros((1080, 1920, 3), np.uint8), Rect(0, 0, 1, 1), ())
    assert large.shape == (360, 640, 3)


def test_disabled_initially_and_no_camera_start_or_source_queue_access():
    exporter, camera = configured()
    assert not exporter.enabled
    exporter._step()
    assert len(exporter._publisher.frames) == 1
    frame, captured, seq, generation, scene = exporter._publisher.frames[0]
    assert captured == 10 and seq == camera.packet.sequence
    assert generation == (5 << 32) | 1
    exporter._step()
    assert len(exporter._publisher.frames) == 1  # duplicate source skipped


def test_fault_stale_and_camera_reconnect_invalidate_without_affecting_capture():
    exporter, camera = configured()
    exporter._step()
    camera.state = "FAULT"
    exporter._step()
    assert exporter._publisher.invalidated == 1
    camera.state = "LIVE"
    camera.packet.captured_at = 9
    exporter._step()
    assert exporter._publisher.invalidated == 2
    camera.packet.captured_at = 10
    camera.packet.sequence = (2 << 48) + 1
    exporter._step()
    assert exporter._stop.is_set() and exporter.crop is None
    assert len(exporter._publisher.frames) == 1
    assert camera.state == "LIVE"


def test_stop_or_scene_change_during_copy_never_publishes_old_geometry(monkeypatch):
    exporter, camera = configured()
    import tyler_safety_monitor.facial_export as module
    real = module.prepare_face_crop
    def changed(*args):
        image = real(*args)
        exporter.invalidate_geometry("Scene changed.")
        return image
    monkeypatch.setattr(module, "prepare_face_crop", changed)
    exporter._step()
    assert not exporter._publisher.frames
    assert exporter._publisher.invalidated == 1 and exporter.crop is None


def test_independent_worker_bounded_and_explicit_enable_disable():
    camera = Camera()
    exporter = FacialFrameExport(clock=lambda: 10.1, publisher_factory=Publisher)
    exporter.set_source(camera, SceneConfig(), 1)
    assert not exporter.start()  # no face region
    exporter.select_crop(Rect(.1, .1, .2, .2))
    assert exporter.start()
    deadline = time.monotonic() + .5
    while exporter.published == 0 and time.monotonic() < deadline:
        time.sleep(.001)
    assert exporter.published == 1 and exporter.enabled
    owned = exporter._publisher
    exporter.close()
    assert owned.closed and not exporter.enabled and camera.state == "LIVE"
