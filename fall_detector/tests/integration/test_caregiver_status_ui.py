"""Live two-head diagnostics stay observational and expose interrupted evidence."""
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QPushButton, QSystemTrayIcon
from tyler_safety_monitor import dashboard as ui
from tyler_safety_monitor.settings import AppSettings
from tyler_safety_monitor.scene import SceneConfig, Rect
from tyler_safety_monitor.tracking import PoseObservation


class Sound:
    def __init__(self): self.calls = []
    def play(self, volume): self.calls.append("play")
    def stop(self): self.calls.append("stop")


class Tray:
    ActivationReason = QSystemTrayIcon.ActivationReason
    @staticmethod
    def isSystemTrayAvailable(): return False
    def __init__(self, *args): self.activated = SimpleNamespace(connect=lambda callback: None)
    def setToolTip(self, *args): pass
    def setContextMenu(self, *args): pass
    def hide(self): pass


class Camera:
    def snapshot(self):
        return SimpleNamespace(state="LIVE", detail="synthetic", frame_age=.01,
                               actual_width=160, actual_height=90, actual_fourcc="FAKE",
                               delivered_fps=5., received_fps=5., brightness=40., blur=8.,
                               read_failures=0, reconnect_events=0)
    def latest_frame(self): return None
    def stop(self): pass


class Pose:
    latest_result = None
    error = None
    ready = True
    is_alive = False
    stats = SimpleNamespace(submitted=1, completed=1, dropped=0)
    def set_scene(self, scene): self.latest_result = None
    def close(self): return True


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.fixture
def live(application, monkeypatch):
    clock = [100.]
    monkeypatch.setattr(ui.time, "monotonic", lambda: clock[0])
    monkeypatch.setattr(ui, "TestSound", Sound)
    monkeypatch.setattr(ui, "QSystemTrayIcon", Tray)
    monkeypatch.setattr(ui, "load_settings", lambda: (AppSettings(), "synthetic defaults"))
    monkeypatch.setattr(ui, "CameraCapture", lambda *args: pytest.fail("Real camera access forbidden"))
    window = ui.Dashboard(Path("unused.task"), enable_camera=False)
    window.timer.stop()
    window.simulation.timer.stop()
    window.tools.clock = lambda: clock[0]
    window.capture = Camera()
    window.pose = Pose()
    window.last_tray_state = "LIVE"
    def emit(timestamp, second=True, missing=False, mapped=True):
        clock[0] = timestamp
        observations = () if missing else (PoseObservation((.25,.5), None, .95),)
        if second and not missing:
            observations += (PoseObservation((.75,.5), None, .95),)
        stamp = round(timestamp * 1000)
        window.pose.latest_result = SimpleNamespace(timestamp_ms=stamp, observations=observations)
        if mapped:
            window._pose_inputs[stamp] = (stamp, timestamp)
        window.refresh()
        return window.caregiver_counter.snapshot
    yield window, clock, emit
    window.shutdown()
    if window._cleanup_thread is not None:
        window._cleanup_thread.join(timeout=1)
    application.processEvents()
    window.deleteLater()
    application.processEvents()


def select_tyler(window, emit):
    emit(100.)
    assert "Select Tyler" in window.caregiver_status.text()
    window.tools.subject.select(window.tools.last_live_tracks, 1, 100.)


def test_live_counter_requires_selected_tyler_and_source_continuity(live):
    window, clock, emit = live
    select_tyler(window, emit)
    for index in range(1, 12):
        snapshot = emit(100. + index / 5)
    assert snapshot.status == "confirmed"
    assert snapshot.elapsed == pytest.approx(2.)
    assert snapshot.candidate_id == 2
    assert "diagnostic only" in window.caregiver_status.text()
    assert "No alert suppression or audio muting" in window.caregiver_status.text()
    assert window.sound.calls == []
    assert not window.tools.samples
    assert window.simulation.runner.engine.snapshot.message_count == 0
    previous = snapshot.elapsed
    clock[0] += .1
    window.refresh()
    assert window.caregiver_counter.snapshot.elapsed == previous


def test_missing_second_head_resets_and_reason_survives_next_count(live):
    window, _, emit = live
    select_tyler(window, emit)
    emit(100.2)
    assert emit(100.4).elapsed == pytest.approx(.2)
    interrupted = emit(100.6, second=False)
    assert interrupted.elapsed == 0
    assert interrupted.status != "confirmed"
    assert interrupted.resets >= 1
    reason = interrupted.reset_reason
    resumed = emit(100.8)
    assert resumed.elapsed == 0
    assert resumed.status == "confirming"
    assert resumed.reset_reason == reason
    assert "Resets:" in window.caregiver_status.text()
    assert reason in window.caregiver_status.text()


def test_clearing_tyler_designation_invalidates_counter_before_next_pose_result(live):
    window, clock, emit = live
    select_tyler(window, emit)
    for index in range(1, 12): emit(100. + index / 5)
    assert window.caregiver_counter.snapshot.status == "confirmed"
    window.tools.subject.reset()
    clock[0] += .1
    window.refresh()
    assert window.caregiver_counter.snapshot.elapsed == 0
    assert "Select Tyler" in window.caregiver_status.text()
    assert "designation changed" in window.caregiver_counter.snapshot.reset_reason


def test_missing_tyler_stale_frames_and_unmapped_results_never_confirm(live):
    window, clock, emit = live
    select_tyler(window, emit)
    emit(100.2)
    assert emit(100.4).elapsed > 0
    lost = emit(100.6, missing=True)
    assert lost.elapsed == 0 and lost.status != "confirmed"
    emit(100.8)
    window.tools.subject.select(window.tools.last_live_tracks, 1, 100.8)
    emit(101.)
    clock[0] = 101.5
    window.refresh()
    assert window.caregiver_counter.snapshot.elapsed == 0
    assert "Fresh pose results stopped" in window.caregiver_counter.snapshot.reset_reason
    unknown = emit(101.6, mapped=False)
    assert unknown.elapsed == 0 and unknown.status != "confirmed"
    assert "mapped source" in unknown.reset_reason


def test_scene_pause_and_selection_reset_preserve_data_and_no_automatic_audio(live):
    window, _, emit = live
    select_tyler(window, emit)
    emit(100.2)
    emit(100.4)
    prior_samples = window.tools.samples
    window.set_scene(SceneConfig(Rect(.1,.1,.8,.8)))
    assert window.caregiver_counter.snapshot.elapsed == 0
    assert "Scene changed" in window.caregiver_status.text()
    assert window.tools.samples is prior_samples
    assert window.sound.calls == []
    window.pause_camera()
    assert window.caregiver_counter.snapshot.elapsed == 0
    assert "Camera paused" in window.caregiver_status.text()
    assert window.sound.calls == ["stop"]  # Existing explicit camera-pause behavior only.
    assert window.tools.samples is prior_samples


def test_counter_label_keeps_one_finger_controls_visible_at_short_height(live, application):
    window, _, emit = live
    select_tyler(window, emit)
    emit(100.2)
    emit(100.4)
    emit(100.6, second=False)
    window.resize(1800,640)
    window.show()
    application.processEvents()
    assert window.height() <= 640
    controls = [window.capture_stop] + [button for button in window.findChildren(QPushButton)
                if button.text() in {"Decrease", "Increase", "Test Sound", "Stop Test Sound"}]
    for control in controls:
        assert control.height() >= 60
        bounds = control.rect().translated(control.mapTo(window.centralWidget(), QPoint(0,0)))
        assert window.centralWidget().rect().contains(bounds)
    assert window.caregiver_status.isVisible()
    window.hide()
