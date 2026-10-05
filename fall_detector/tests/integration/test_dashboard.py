"""Offscreen one-pointer UI checks with fake camera, tray, and sound adapters."""

import os
from pathlib import Path
import threading
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QSystemTrayIcon

from tyler_safety_monitor import dashboard as ui
from tyler_safety_monitor.scene import Rect, SceneConfig
from tyler_safety_monitor.settings import AppSettings
from tyler_safety_monitor.tracking import PoseObservation


class FakeSound:
    def __init__(self):
        self.sink = None
        self.played = []
        self.stopped = 0

    def stop(self):
        self.stopped += 1

    def play(self, volume):
        self.played.append(volume)


class FakeTray:
    ActivationReason = QSystemTrayIcon.ActivationReason
    MessageIcon = QSystemTrayIcon.MessageIcon
    available = True

    @staticmethod
    def isSystemTrayAvailable():
        return FakeTray.available

    def __init__(self, icon, parent):
        self.activated = SimpleNamespace(connect=lambda callback: None)
        self.tooltip = ""
        self.visible = False

    def setToolTip(self, text):
        self.tooltip = text

    def setContextMenu(self, menu):
        self.menu = menu

    def setIcon(self, icon):
        self.icon = icon

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False

    def showMessage(self, *args):
        raise AssertionError("Native notifications are forbidden in this test")


class FakeCapture:
    def __init__(self):
        self.stopped = False
        self.started = False
        self.reads = 0
        self.packet = SimpleNamespace(sequence=1, captured_at=100,
                                      image=np.zeros((90, 160, 3), dtype=np.uint8))
        self.metrics = SimpleNamespace(
            state="LIVE", detail="fake capture", frame_age=0.01,
            actual_width=160, actual_height=90, actual_fourcc="FAKE",
            delivered_fps=30, received_fps=20, brightness=40, blur=8,
            read_failures=0, reconnect_events=0,
        )

    def snapshot(self):
        self.reads += 1
        return self.metrics

    def latest_frame(self):
        return self.packet

    def stop(self):
        self.stopped = True

    def start(self):
        self.started = True


def wait_for(application, condition):
    for _ in range(100):
        application.processEvents()
        if condition():
            return
        QTest.qWait(10)
    pytest.fail("Expected asynchronous UI cleanup did not complete within one second")


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.fixture
def window(application, monkeypatch):
    monkeypatch.setattr(ui, "TestSound", FakeSound)
    monkeypatch.setattr(ui, "QSystemTrayIcon", FakeTray)
    monkeypatch.setattr(FakeTray, "available", True)
    monkeypatch.setattr(ui, "load_settings", lambda: (AppSettings(), "test defaults"))
    monkeypatch.setattr(ui, "CameraCapture", lambda *args: pytest.fail("Camera access forbidden"))
    dashboard = ui.Dashboard(Path("unused-model.task"), enable_camera=False)
    yield dashboard
    dashboard.shutdown()
    dashboard.deleteLater()
    application.processEvents()


def tap_normalized(preview, x, y):
    area = preview.image_rect()
    position = QPoint(round(area.x() + x * area.width()), round(area.y() + y * area.height()))
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=position)


def test_two_separate_taps_edit_roi_and_mask_with_letterbox_mapping(window):
    preview = window.preview
    preview.resize(800, 800)
    preview.set_frame(np.zeros((90, 160, 3), dtype=np.uint8))
    assert preview.image_rect().y() > 0
    window.begin_edit("roi")
    QTest.mouseClick(preview, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    assert preview.pending_corner is None  # Letterbox margin does not become camera geometry.
    tap_normalized(preview, 0.2, 0.3)
    assert preview.pending_corner == pytest.approx((0.2, 0.3), abs=0.003)
    assert window.settings.scene.roi == Rect(0, 0, 1, 1)
    tap_normalized(preview, 0.8, 0.9)
    roi = window.settings.scene.roi
    assert (roi.x, roi.y, roi.width, roi.height) == pytest.approx((0.2, 0.3, 0.6, 0.6), abs=0.003)
    assert preview.pending_corner is None and window.edit_mode is None
    window.begin_edit("mask")
    tap_normalized(preview, 0.7, 0.4)
    tap_normalized(preview, 0.5, 0.2)  # Reverse corner order works without dragging.
    mask = window.settings.scene.exclusions[0]
    assert (mask.x, mask.y, mask.width, mask.height) == pytest.approx((0.5, 0.2, 0.2, 0.2), abs=0.003)
    assert window.settings.scene.roi == roi


def test_volume_controls_clamp_only_app_level_and_manual_test_uses_selection(window):
    app_volumes = []
    window.sound.sink = SimpleNamespace(setVolume=app_volumes.append)
    window.change_volume(-2)
    assert window.settings.alert_volume == 0 and app_volumes[-1] == 0
    window.change_volume(2)
    assert window.settings.alert_volume == 1 and app_volumes[-1] == 1
    window.change_volume(-0.3)
    window.test_sound()
    assert window.sound.played == [0.7]
    assert "Windows volume is unchanged" in window.settings_status.text()
    assert "70%" in window.volume_label.text()


def test_single_tray_click_restores_and_hide_preserves_processing(window):
    window.capture = FakeCapture()
    window.show()
    window.hide()
    assert not window.isVisible() and window.timer.isActive()
    window.refresh()
    assert window.capture.reads == 1 and not window.capture.stopped
    assert window.preview.image is not None
    window.tray_activated(FakeTray.ActivationReason.Context)
    assert not window.isVisible()
    window.tray_activated(FakeTray.ActivationReason.Trigger)
    assert window.isVisible()


def test_close_to_tray_keeps_capture_and_timer_alive(window):
    window.capture = FakeCapture()
    window.show()
    window.close()
    assert not window.isVisible()
    assert window.timer.isActive() and not window.capture.stopped


def test_unavailable_tray_does_not_leave_dashboard_unreachable(window, monkeypatch, application):
    monkeypatch.setattr(FakeTray, "available", False)
    fallback = ui.Dashboard(Path("unused-model.task"), enable_camera=False)
    try:
        fallback.show()
        minimize = next(control for control in fallback.findChildren(QPushButton)
                        if "Minimize" in control.text())
        assert minimize.accessibleName() == minimize.text()
        minimize.click()
        assert fallback.isVisible() or not minimize.isEnabled()
        assert fallback.timer.isActive()
    finally:
        fallback.shutdown()
        fallback.deleteLater()
        application.processEvents()


def test_stale_or_faulted_camera_hides_tracking_overlays(window, monkeypatch):
    clock = SimpleNamespace(value=100.0)
    monkeypatch.setattr(ui, "time", SimpleNamespace(monotonic=lambda: clock.value))
    window.capture = FakeCapture()
    result = SimpleNamespace(timestamp_ms=100_000,
                             observations=[PoseObservation((0.5, 0.7), None, 0.9)])
    window.pose = SimpleNamespace(
        latest_result=result, stats=SimpleNamespace(submitted=1, completed=1, dropped=0),
        error=None, submit=lambda *args: None, close=lambda: None,
    )
    window.refresh()
    assert len(window.preview.tracks) == 1
    clock.value = 101.1
    window.refresh()
    assert window.preview.tracks == []
    window.preview.tracks = window.tracker.update(result.observations, 102)
    window.capture.metrics.state = "FAULT"
    window.tray_available = False  # Native fault notification remains disabled.
    window.refresh()
    assert window.preview.tracks == []


def test_delayed_callback_does_not_restore_old_captured_frame_as_fresh_tracking(window, monkeypatch):
    monkeypatch.setattr(ui, "time", SimpleNamespace(monotonic=lambda: 105.0))
    window.capture = FakeCapture()
    old = SimpleNamespace(timestamp_ms=100_000,
                          observations=[PoseObservation((0.5, 0.7), None, 0.9)])
    window.pose = SimpleNamespace(
        latest_result=old, stats=SimpleNamespace(submitted=1, completed=1, dropped=0),
        error=None, submit=lambda *args: None, close=lambda: None,
    )
    window.refresh()
    assert window.preview.tracks == []
    assert window.last_pose_seen_at == 100.0
    fresh = SimpleNamespace(timestamp_ms=104_900, observations=old.observations)
    window.pose.latest_result = fresh
    window.refresh()
    assert len(window.preview.tracks) == 1


def test_retry_keeps_pointer_controls_responsive_while_cleanup_waits(window, monkeypatch, application):
    entered, release, completed = threading.Event(), threading.Event(), threading.Event()
    close_thread_ids = []
    ui_thread_id = threading.get_ident()
    capture = FakeCapture()
    replacement = FakeCapture()
    created = []

    def close_pose():
        close_thread_ids.append(threading.get_ident())
        entered.set()
        release.wait(timeout=3)
        completed.set()

    window.capture = capture
    window.pose = SimpleNamespace(close=close_pose, is_alive=False)
    monkeypatch.setattr(ui, "CameraCapture", lambda settings: created.append(replacement) or replacement)
    try:
        window.start_camera()
        assert entered.wait(timeout=1)
        assert len(close_thread_ids) == 1 and close_thread_ids[0] != ui_thread_id
        assert not completed.is_set() and window._retiring is not None
        assert capture.stopped and created == []
        window.change_volume(0.1)
        assert window.settings.alert_volume == 0.6
        assert window.timer.isActive()
        release.set()
        wait_for(application, lambda: window._retiring is None)
        assert completed.is_set() and created == [replacement] and replacement.started
    finally:
        release.set()


def test_hung_pose_blocks_replacement_and_stops_retired_capture(window, application):
    capture = FakeCapture()
    closed = []
    hung_pose = SimpleNamespace(close=lambda: closed.append(True), is_alive=True)
    window.capture = capture
    window.pose = hung_pose
    window.start_camera()
    wait_for(application, lambda: window._retiring is None)
    assert capture.stopped and closed == [True]
    assert window.capture is None and window.pose is None
    assert window._blocked_pose is hung_pose
    assert "restart" in window.pose_status.text().lower()
    window.start_camera()  # The fixture's camera factory fails if replacement is attempted.
    assert window.capture is None and "did not stop" in window.pose_status.text()


def test_failed_capture_cleanup_also_blocks_replacement_without_pose(window, application):
    def failed_stop():
        raise RuntimeError("simulated cleanup failure")

    window.capture = SimpleNamespace(stop=failed_stop)
    window.start_camera()
    wait_for(application, lambda: window._retiring is None)
    assert window.capture is None
    assert window._cleanup_failed
    window.start_camera()  # Never create another process after unknown cleanup failure.
    assert "cleanup fault" in window.pose_status.text().lower()


def test_capture_cleanup_exception_with_idle_pose_cannot_be_cleared_by_retry(window, monkeypatch, application):
    def failed_stop():
        raise RuntimeError("simulated cleanup failure")

    created = []
    replacement = FakeCapture()
    monkeypatch.setattr(ui, "CameraCapture", lambda settings: created.append(replacement) or replacement)
    window.capture = SimpleNamespace(stop=failed_stop)
    window.pose = SimpleNamespace(close=lambda: None, is_alive=False)
    window.start_camera()
    wait_for(application, lambda: window._retiring is None)
    window.start_camera()
    assert created == [] and window.capture is None
    assert "cleanup fault" in window.pose_status.text().lower()


def test_scene_change_invalidates_old_candidates_and_forwards_revision(window):
    previous_tracker = window.tracker
    window.preview.tracks = previous_tracker.update([PoseObservation((0.5, 0.7), None, 0.9)], 1)
    scenes = []
    window.pose = SimpleNamespace(set_scene=scenes.append, close=lambda: None)
    scene = SceneConfig(Rect(0.2, 0.3, 0.6, 0.6))
    window.set_scene(scene)
    assert window.preview.tracks == []
    assert window.tracker is not previous_tracker
    assert window.last_pose_timestamp == -1
    assert scenes == [scene]


def test_controls_expose_observation_status_and_no_emergency_or_messaging_action(window):
    labels = [control.text() for control in window.findChildren(QPushButton)]
    assert "Test Sound" in labels and "Decrease" in labels and "Increase" in labels
    assert not any("SMS" in label or "Choking" in label or "Possible Fall" in label for label in labels)
    for control in window.findChildren(QPushButton):
        assert control.minimumHeight() >= 60 and control.accessibleName()
