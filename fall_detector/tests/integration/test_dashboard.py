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
from tyler_safety_monitor.camera import CameraSettings
from tyler_safety_monitor.tracking import PoseObservation, Track
from tyler_safety_monitor.calibration import CalibrationProfile, scene_digest
from tyler_safety_monitor import calibration_ui as tooling
from tyler_safety_monitor.replay import FeatureSample, FeatureSequence, load_sequence


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
        self.settings = CameraSettings()
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


def ready_tools(window, monkeypatch):
    """Synthetic capture, with no camera/model access or user runtime writes."""
    clock = SimpleNamespace(value=100.0)
    window.tools.clock = lambda: clock.value
    window.capture = FakeCapture()
    window.pose = SimpleNamespace(ready=True, close=lambda: None, is_alive=False, set_scene=lambda scene: None)
    window.preview.set_frame(window.capture.packet.image)
    provenance = {"created_at": "2026-10-05T12:00:00+00:00", "scene_sha256": scene_digest(window.settings.scene),
                  "model": {"name": "synthetic.task", "sha256": "0" * 64},
                  "camera": {"source": "camera 0 / dshow", "frame_width": 160, "frame_height": 90},
                  "dependencies": {"python": "3.12.8"}}
    monkeypatch.setattr(tooling, "build_provenance", lambda *args: provenance)
    window.tools.last_live_tracks = [Track(1, (0.5, 0.5), None, 0.9, 100, 100)]
    window.tools.candidate.addItem("P1", 1)
    window.tools.candidate.setCurrentIndex(1)
    window.tools.scene_review.setChecked(True)
    window.tools.confirm = lambda *args: True
    return window.tools, clock, provenance


def test_capture_requires_current_candidate_scene_review_and_explicit_consent(window, monkeypatch):
    tools, _, _ = ready_tools(window, monkeypatch)
    tools.scene_review.setChecked(False)
    tools.request_capture()
    assert tools.state == "idle"
    tools.scene_review.setChecked(True)
    tools.confirm = lambda *args: False
    tools.request_capture()
    assert tools.state == "idle" and tools.samples == []
    tools.confirm = lambda *args: True
    window.begin_edit("mask")
    tools.request_capture()
    assert tools.state == "delay" and window.edit_mode is None
    assert tools.samples == []


def test_capture_delay_stop_and_limit_preserve_original_timestamps(window, monkeypatch):
    tools, clock, _ = ready_tools(window, monkeypatch)
    tools.request_capture()
    obs = PoseObservation((0.5, 0.5), None, 0.9)
    result = SimpleNamespace(timestamp_ms=105010, observations=(obs,))
    track = Track(1, obs.head, None, .9, 105, 105)
    tools.observe(result, [track], 1, 104.98)
    assert tools.samples == []
    clock.value = 105
    tools.tick()
    assert tools.state == "capturing"
    tools.observe(result, [track], 2, 104.99)
    assert tools.samples == []  # Late inference captured during delay rejected.
    tools.observe(result, [track], 3, 105.01)
    assert tools.samples[0].timestamp == 105.01
    assert tools.samples[0].inference_timestamp_ms == 105010
    assert tools.samples[0].capture_step == "ordinary"
    assert "CAPTURING" in window.capture_banner.text()
    clock.value = 120
    tools.tick()
    assert tools.state == "review" and len(tools.samples) == 1
    assert tools.step.isEnabled()


def test_native_minimize_and_hide_end_collection_but_keep_processing(window, monkeypatch, application):
    tools, _, _ = ready_tools(window, monkeypatch)
    window.show()
    tools.request_capture()
    window.showMinimized()
    application.processEvents()
    assert tools.state == "review"
    assert window.capture is not None and window.timer.isActive()
    window.showNormal()
    tools.request_capture()
    window.hide()
    application.processEvents()
    assert tools.state == "review" and window.capture is not None


def test_scene_change_retains_capture_but_hides_incompatible_zones(window, monkeypatch):
    tools, _, provenance = ready_tools(window, monkeypatch)
    tools.request_capture()
    tools.samples = [FeatureSample(100, 1, (PoseObservation((.5, .5), None, .9),))]
    tools.profile = CalibrationProfile(window.settings.scene, provenance, {"safe": Rect(.4, .4, .2, .2)})
    tools.show_zones()
    assert window.preview.zones
    window.set_scene(SceneConfig(Rect(.1, .1, .8, .8)))
    assert tools.state == "review" and len(tools.samples) == 1
    assert not tools.scene_review.isChecked() and window.preview.zones == {}


def test_margin_invalidates_lean_review_without_expanding_danger_zone(window, monkeypatch):
    tools, _, provenance = ready_tools(window, monkeypatch)
    lean, hard = Rect(.4, .4, .2, .2), Rect(.3, .8, .3, .1)
    tools.capture_provenance = provenance
    tools.profile = CalibrationProfile(window.settings.scene, provenance,
        {"intentional_lean": lean, "hard_boundary": hard}, ("intentional_lean", "hard_boundary"))
    tools.points["intentional_lean"] = [(.4, .4), (.6, .6)]
    tools.margin.setValue(.5)
    assert tools.profile.lean_margin == .005
    assert "intentional_lean" not in tools.profile.reviewed_zones
    assert tools.profile.zones["hard_boundary"] == hard
    assert "hard_boundary" in tools.profile.reviewed_zones
    assert tools.profile.zones["intentional_lean"].height > lean.height
    tools.zone.setCurrentIndex(tools.zone.findData("hard_boundary"))
    tools.propose()
    assert "no thresholds" in tools.status.text()


def test_new_session_cancels_pending_zone_edit_and_never_deletes_saved_files(window, monkeypatch):
    tools, _, provenance = ready_tools(window, monkeypatch)
    tools.capture_provenance = provenance
    tools.profile = CalibrationProfile(window.settings.scene, provenance)
    window.begin_edit("zone:safe")
    tools.new_session()
    assert window.edit_mode is None and tools.profile is None
    tap_normalized(window.preview, .2, .2)
    tap_normalized(window.preview, .8, .8)
    assert tools.profile is None


def test_switching_candidate_or_camera_requires_new_calibration_session(window, monkeypatch):
    tools, _, _ = ready_tools(window, monkeypatch)
    tools.request_capture()
    tools.stop_capture()
    tools.samples = [FeatureSample(100, 1, (PoseObservation((.5, .5), None, .9),))]
    tools.candidate.addItem("P2", 2)
    tools.candidate.setCurrentIndex(2)
    tools.last_live_tracks = [Track(2, (.6, .5), None, .9, 100, 100)]
    tools.request_capture()
    assert tools.state == "review" and "different person candidate" in tools.status.text()
    tools.candidate.setCurrentIndex(1)
    tools.last_live_tracks = [Track(1, (.5, .5), None, .9, 100, 100)]
    window._capture_generation += 1
    tools.request_capture()
    assert tools.state == "review" and "camera session changed" in tools.status.text()


def test_real_feature_save_requires_confirmation_and_preserves_earlier_files(window, monkeypatch, tmp_path):
    tools, _, provenance = ready_tools(window, monkeypatch)
    tools.request_capture()
    tools.stop_capture()
    tools.samples = [FeatureSample(100, 1, (PoseObservation((.5, .5), None, .9),), 100000, "ordinary")]
    tools.steps_taken = ["ordinary"]
    old = tmp_path / "unrelated.txt"
    old.write_text("preserve")
    from tyler_safety_monitor import calibration, replay
    monkeypatch.setattr(tooling, "save_profile", lambda p: calibration.save_profile(p, tmp_path / "profiles"))
    monkeypatch.setattr(tooling, "save_sequence", lambda s: replay.save_sequence(s, directory=tmp_path / "features"))
    tools.confirm = lambda *args: False
    tools.request_save()
    assert list(tmp_path.iterdir()) == [old]
    tools.confirm = lambda *args: True
    tools.request_save()
    first = next((tmp_path / "profiles").glob("*.json"))
    before = first.read_bytes()
    tools.request_save()
    assert first.read_bytes() == before
    assert len(list((tmp_path / "profiles").glob("*.json"))) == 2
    assert len(list((tmp_path / "features").glob("*.json"))) == 1
    seq = load_sequence(next((tmp_path / "features").glob("*.json")))
    assert seq.samples[0].capture_step == "ordinary" and seq.samples[0].timestamp == 100
    assert old.read_text() == "preserve"


def test_replay_uses_its_clock_original_aspect_ratio_and_camera_stays_paused(window):
    clock = SimpleNamespace(value=2000.0)
    window.tools.clock = lambda: clock.value
    seq = FeatureSequence(SceneConfig(), {"source_kind": "synthetic", "frame_width": 640, "frame_height": 480}, (
        FeatureSample(10, 1, (PoseObservation((.5, .5), None, .9),)),
        FeatureSample(10.2, 2, ()),
        FeatureSample(10.3, 3, (PoseObservation((.51, .51), None, .9),)),
    ))
    tools = window.tools
    tools.install_replay(seq)
    tools.toggle_play()
    tools.render_replay()
    assert len(window.preview.tracks) == 1 and window.preview.frame_ratio == 4 / 3
    clock.value += .31
    tools.render_replay()
    paths = window.preview.trajectory_segments
    assert len(paths[1]) == 2  # Missing batch visibly breaks the path.
    tools.rewind()
    assert window.preview.tracks == [] and window.preview.trajectory_segments == {}
    tools.leave_replay()
    assert window.capture is None and tools.player is None


def test_profile_zones_hidden_when_model_dimensions_or_camera_differ(window, monkeypatch):
    tools, _, provenance = ready_tools(window, monkeypatch)
    tools.capture_provenance = provenance
    tools.profile = CalibrationProfile(window.settings.scene, provenance, {"safe": Rect(.4, .4, .2, .2)})
    tools.show_zones()
    assert window.preview.zones
    window.capture.metrics.actual_width = 640
    tools.show_zones()
    assert window.preview.zones == {}
    tools.review_zone()
    assert "unverifiable" in tools.status.text()


def test_tools_controls_are_one_pointer_and_global_volume_stop_remain_visible(window, application):
    window.resize(1400, 900)
    window.show()
    window.tabs.setCurrentIndex(1)
    application.processEvents()
    assert window.capture_stop.isVisible()
    for control in window.tools.findChildren(QPushButton):
        assert control.accessibleName() == control.text()
        assert control.minimumHeight() >= 60
    for text in ("Decrease", "Increase", "Test Sound"):
        controls = [c for c in window.findChildren(QPushButton) if c.text() == text]
        assert len(controls) == 1 and controls[0].isVisible()


def test_profile_provenance_uses_owned_camera_instead_of_next_launch_settings(window, monkeypatch):
    tools, _, provenance = ready_tools(window, monkeypatch)
    source = []
    monkeypatch.setattr(tooling, "build_provenance", lambda scene, model, camera, *args: source.append(camera) or provenance)
    window.camera_index.setValue(1)
    window.backend.setCurrentIndex(1)
    window.settings = window.read_controls()  # Save Settings does not reopen camera.
    tools.request_capture()
    assert source == ["camera 0 / dshow"]
    tools.profile = CalibrationProfile(window.settings.scene, provenance, {"safe": Rect(.4, .4, .2, .2)})
    tools.show_zones()
    assert window.preview.zones
    window.capture.settings = CameraSettings(index=1)
    tools.show_zones()
    assert window.preview.zones == {}


def test_camera_pause_and_fault_clear_reviewed_zone_overlays(window, monkeypatch):
    tools, _, provenance = ready_tools(window, monkeypatch)
    tools.capture_provenance = provenance
    tools.profile = CalibrationProfile(window.settings.scene, provenance,
        {"safe": Rect(.4, .4, .2, .2)}, ("safe",))
    tools.show_zones()
    assert window.preview.zones and window.preview.reviewed_zones
    window.capture.metrics.state = "FAULT"
    tools.show_zones()
    assert window.preview.zones == {} and window.preview.reviewed_zones == set()
    window.capture.metrics.state = "LIVE"
    tools.show_zones()
    window.pause_camera()
    assert window.preview.zones == {} and window.preview.reviewed_zones == set()


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


def test_long_saved_paths_do_not_widen_calibration_controls(window, application, monkeypatch):
    tools, _, _ = ready_tools(window, monkeypatch)
    tools.request_capture()
    tools.stop_capture()
    tools.samples = [FeatureSample(100, 1, (PoseObservation((.5, .5), None, .9),))]
    profile_path = Path(r"C:\Users\SyntheticUser\AppData\Local\TylerSafetyMonitor\calibration\profiles\profile-20261005T000000000000Z-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json")
    feature_path = Path(r"C:\Users\SyntheticUser\AppData\Local\TylerSafetyMonitor\calibration\replays\features-20261005T000000000000Z-bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb.json")
    monkeypatch.setattr(tooling, "save_profile", lambda profile: profile_path)
    monkeypatch.setattr(tooling, "save_sequence", lambda sequence: feature_path)
    window.tabs.setCurrentIndex(1)
    window.show()
    application.processEvents()
    scroll = window.tabs.widget(1)
    baseline_width = window.tools.minimumSizeHint().width()
    baseline_scroll = scroll.horizontalScrollBar().maximum()
    tools.request_save()
    application.processEvents()
    assert "New profile saved" in tools.status.text()
    assert "New feature replay saved" in tools.status.text()
    assert str(profile_path) in tools.status.toolTip()
    assert str(feature_path) in tools.status.accessibleDescription()
    assert "SyntheticUser" not in tools.status.text()
    assert tools.status.wordWrap() and tools.status.hasHeightForWidth()
    assert tools.minimumSizeHint().width() <= baseline_width
    assert scroll.horizontalScrollBar().maximum() <= baseline_scroll
    tools.message("Next capture is idle")
    assert not tools.status.toolTip() and not tools.status.accessibleDescription()


def test_scaled_screen_height_keeps_bottom_and_essential_controls_inside_window(window, application):
    window.resize(1800, 640)
    window.tabs.setCurrentIndex(1)
    window.show()
    application.processEvents()
    assert window.width() <= 1800 and window.height() <= 640
    scroll = window.tabs.widget(1)
    scroll.verticalScrollBar().setValue(scroll.verticalScrollBar().maximum())
    application.processEvents()
    last = next(control for control in window.tools.findChildren(QPushButton)
                if control.text() == "Live View • Camera Stays Paused")
    last_rect = last.rect().translated(last.mapTo(scroll.viewport(), QPoint(0, 0)))
    assert last_rect.top() >= 0 and last_rect.bottom() < scroll.viewport().height()
    essential = [window.capture_stop] + [control for control in window.findChildren(QPushButton)
        if control.text() in {"Decrease", "Increase", "Test Sound", "Stop Test Sound"}]
    for control in essential:
        rect = control.rect().translated(control.mapTo(window.centralWidget(), QPoint(0, 0)))
        assert window.centralWidget().rect().contains(rect)
        assert control.height() >= 60


def test_duplicate_candidate_label_keeps_visibility_and_identity_separate():
    track = Track(1, (.5, .5), None, .9, 1, 1, identity_uncertain=True,
                  uncertainty_reasons=("duplicate heads",))
    label = tooling.candidate_label(track)
    assert "head visible" in label
    assert "ID uncertain: duplicate heads" in label
    assert track.identity_uncertain  # Display wording does not authorize continuity.


def test_tracking_diagnostics_do_not_force_global_controls_off_screen(window, application):
    window.tracking_status.setText("Head rings show current detections; amber ID text means uncertain identity. "
                                   "Model: raw poses 2, accepted heads 2. " + window.tracker.diagnostics.summary())
    window.resize(1800, 640)
    window.show()
    application.processEvents()
    assert window.capture_stop.mapTo(window, QPoint(0, 0)).y() + window.capture_stop.height() <= window.height()
    for label in ("Decrease", "Increase", "Test Sound", "Stop Test Sound"):
        control = next(b for b in window.findChildren(QPushButton) if b.text() == label)
        assert control.mapTo(window, QPoint(0, 0)).y() + control.height() <= window.height()


def test_selected_candidate_survives_gap_without_silent_reassignment(window):
    tools = window.tools
    tools.update_candidates([Track(1, (.5, .5), None, .9, 1, 1)], 1)
    tools.candidate.setCurrentIndex(tools.candidate.findData(1))
    tools.update_candidates([], 1.1)
    assert tools.candidate.currentData() == 1
    assert "not visible" in tools.candidate.currentText()
    tools.update_candidates([Track(2, (.6, .5), None, .9, 3, 3)], 3)
    assert tools.candidate.currentData() == 1  # Never silently selects the new ID.
    assert tools.candidate.findData(2) >= 0
    tools.reset_candidate_choices()
    assert tools.candidate.currentData() is None and tools.candidate.count() == 1


def test_candidate_uncertainty_updates_keep_keyed_row_and_selection(window):
    tools = window.tools
    clear = Track(1, (.5, .5), None, .9, 1, 1)
    uncertain = Track(1, (.5, .5), None, .9, 1.1, 1.1, identity_uncertain=True,
                      uncertainty_reasons=("duplicate heads",))
    tools.update_candidates([clear], 1)
    index = tools.candidate.findData(1)
    tools.candidate.setCurrentIndex(index)
    tools.update_candidates([uncertain], 1.1)
    assert tools.candidate.currentIndex() == index and tools.candidate.currentData() == 1
    assert "ID uncertain" in tools.candidate.currentText()
    tools.update_candidates([clear], 1.2)
    assert tools.candidate.currentIndex() == index and tools.candidate.currentData() == 1
    assert tools.candidate.count() == 2


def test_unselected_missing_candidate_expires_and_scene_clears_selection(window):
    tools = window.tools
    tools.update_candidates([Track(1, (.5, .5), None, .9, 1, 1)], 1)
    tools.update_candidates([], 2.1)
    assert tools.candidate.count() == 1
    tools.update_candidates([Track(2, (.5, .5), None, .9, 3, 3)], 3)
    tools.candidate.setCurrentIndex(tools.candidate.findData(2))
    tools.scene_changed()
    assert tools.candidate.currentData() is None and tools.candidate.count() == 1


class FakeHeadComparison:
    def __init__(self):
        self.is_alive = True
        self.ready = True
        self.error = ""
        self.latest_result = SimpleNamespace(timestamp_ms=100000, heads=((.3,.4,.8),))
        self.stats = SimpleNamespace(diagnostic_frames=3, no_face_frames=1, completed=3, dropped=0)
        self.scenes = []
        self.closed = False
    def set_scene(self, scene):
        self.scenes.append(scene)
        self.latest_result = None
    def close(self):
        self.closed = True
        self.is_alive = False
        return True


def test_comparison_overlay_remains_separate_and_expires_without_holding_head(window, monkeypatch):
    worker = FakeHeadComparison()
    window.head_comparison = worker
    window._head_enabled = True
    window.preview.tracks = [Track(7,(.5,.5),None,.9,100,100)]
    monkeypatch.setattr(ui.time, "monotonic", lambda: 100.5)
    window.refresh_head_comparison(True)
    assert window.preview.comparison_heads == ((.3,.4,.8),)
    assert window.preview.tracks[0].id == 7
    assert "3 samples" in window.head_status.text() and "no face 1" in window.head_status.text()
    monkeypatch.setattr(ui.time, "monotonic", lambda: 102)
    window.refresh_head_comparison(True)
    assert window.preview.comparison_heads == ()
    assert window.preview.tracks[0].id == 7
    worker.error = "comparison fault"
    window.refresh_head_comparison(True)
    assert window.preview.comparison_heads == () and "comparison fault" in window.head_status.text()


def test_head_comparison_blocks_feature_capture_and_never_prompts_to_save(window, monkeypatch):
    window._head_preparing = True
    monkeypatch.setattr(window.tools, "confirm", lambda *a: pytest.fail("capture consent must not be reached"))
    window.tools.request_capture()
    assert window.tools.state == "idle" and not window.tools.samples
    assert "Stop the experimental head comparison" in window.tools.status.text()


def test_head_comparison_stops_on_pause_and_forwards_scene_generation(window, application):
    worker = FakeHeadComparison()
    window.head_comparison = worker
    window._head_enabled = True
    window.preview.comparison_heads = ((.3,.4,.8),)
    scene = SceneConfig(Rect(.2,.2,.7,.7))
    window.set_scene(scene)
    assert worker.scenes == [scene] and window.preview.comparison_heads == ()
    window.pause_camera()
    wait_for(application, lambda: worker.closed)
    assert not window._head_enabled and not window.comparison_active
    assert window.preview.comparison_heads == ()


def test_late_preparation_completion_cannot_start_after_stop(window):
    window._head_preparing = True
    window._head_request = 1
    window.stop_head_comparison()
    window.finish_head_preparation(1, Path("unused-experimental.tflite"))
    assert window.head_comparison is None and not window._head_enabled


def test_running_or_hung_comparison_cannot_be_replaced(window):
    window.head_comparison = FakeHeadComparison()
    window.start_head_comparison()
    assert "unfinished worker cannot be replaced" in window.head_status.text()
    assert not window._head_preparing
