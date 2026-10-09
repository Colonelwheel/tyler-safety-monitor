"""Offscreen single-pointer controls, fake camera/audio/native notifications."""
from pathlib import Path
from types import SimpleNamespace
import time

import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QSystemTrayIcon

from tyler_safety_monitor import dashboard as ui
from tyler_safety_monitor.scene import Rect, SceneConfig
from tyler_safety_monitor.settings import AppSettings
from test_facial_export import Publisher


class FakeSound:
    def __init__(self):
        self.sink = None
    def stop(self):
        pass
    def play(self, volume):
        raise AssertionError("Actual sound forbidden")


class FakeTray:
    ActivationReason = QSystemTrayIcon.ActivationReason
    MessageIcon = QSystemTrayIcon.MessageIcon
    @staticmethod
    def isSystemTrayAvailable():
        return True
    def __init__(self, *args):
        self.activated = SimpleNamespace(connect=lambda callback: None)
    def setToolTip(self, *args): pass
    def setContextMenu(self, *args): pass
    def setIcon(self, *args): pass
    def show(self): pass
    def hide(self): pass
    def showMessage(self, *args): raise AssertionError("Actual notification forbidden")


class FakeCamera:
    def snapshot(self):
        return SimpleNamespace(state="LIVE")
    def latest_frame(self):
        return SimpleNamespace(sequence=(1 << 48) + 1, captured_at=time.monotonic(),
                               image=np.full((100, 200, 3), 90, np.uint8))
    def stop(self): pass


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.fixture
def window(application, monkeypatch):
    monkeypatch.setattr(ui, "TestSound", FakeSound)
    monkeypatch.setattr(ui, "QSystemTrayIcon", FakeTray)
    monkeypatch.setattr(ui, "load_settings", lambda: (AppSettings(), "test defaults"))
    monkeypatch.setattr(ui, "CameraCapture", lambda *args: pytest.fail("Real webcam forbidden"))
    dashboard = ui.Dashboard(Path("unused.task"), enable_camera=False)
    dashboard.timer.stop()
    dashboard.facial_export.publisher_factory = Publisher
    yield dashboard
    dashboard.shutdown()
    dashboard.deleteLater()
    application.processEvents()


def click_button(window, text):
    control = next(button for button in window.findChildren(QPushButton) if button.text() == text)
    assert control.minimumHeight() >= 60
    QTest.mouseClick(control, Qt.MouseButton.LeftButton)


def tap(preview, x, y):
    area = preview.image_rect()
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton,
                     pos=QPoint(round(area.x() + x * area.width()), round(area.y() + y * area.height())))


def live(window):
    window.capture = FakeCamera()
    window.preview.resize(800, 600)
    window.preview.set_frame(np.zeros((100, 200, 3), np.uint8))


def test_off_by_default_two_single_taps_do_not_touch_safety_geometry(window):
    original = window.settings
    assert not window.facial_export.enabled and window.facial_export.crop is None
    click_button(window, "Enable Face Sharing")
    assert not window.facial_export.enabled
    live(window)
    click_button(window, "Select Face Region")
    # Letterbox taps never select pixels.
    QTest.mouseClick(window.preview, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    assert window.preview.pending_corner is None
    tap(window.preview, .2, .3)
    assert window.facial_export.crop is None and not window.facial_export.enabled
    tap(window.preview, .5, .6)
    crop = window.facial_export.crop
    assert (crop.x, crop.y, crop.width, crop.height) == pytest.approx((.2, .3, .3, .3), abs=.003)
    assert window.settings == original and window.preview.scene == original.scene
    assert not window.facial_export.enabled  # selection never enables implicitly
    click_button(window, "Enable Face Sharing")
    assert window.facial_export.enabled
    click_button(window, "Disable Face Sharing")
    assert not window.facial_export.enabled and window.settings == original


def test_pause_and_scene_changes_invalidate_feed_and_pending_corners(window):
    live(window)
    click_button(window, "Select Face Region")
    tap(window.preview, .2, .3)
    window.pause_camera()
    assert window.preview.pending_corner is None and window.edit_mode is None
    assert window.facial_export.crop is None and not window.facial_export.enabled
    live(window)
    click_button(window, "Select Face Region")
    tap(window.preview, .2, .3)
    tap(window.preview, .5, .6)
    click_button(window, "Enable Face Sharing")
    next_scene = SceneConfig(exclusions=(Rect(.7, .7, .1, .1),))
    window.set_scene(next_scene)
    assert not window.facial_export.enabled and window.facial_export.crop is None
    assert window.preview.face_crop is None and window.settings.scene == next_scene


def test_region_selection_blocked_in_replay_or_active_calibration(window):
    live(window)
    window.tools.state = "capturing"
    click_button(window, "Select Face Region")
    assert window.edit_mode is None
    click_button(window, "Enable Face Sharing")
    assert not window.facial_export.enabled
    window.tools.state = "idle"
    window.tools.player = object()
    click_button(window, "Select Face Region")
    assert window.edit_mode is None
    click_button(window, "Enable Face Sharing")
    assert not window.facial_export.enabled
    window.tools.player = None
