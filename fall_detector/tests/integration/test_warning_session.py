"""Synthetic manual warning checks; no camera, speech/audio devices or native keys."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from tyler_safety_monitor.test_ui import TestPanel
from tyler_safety_monitor.simulation_state import Incident, Mode


class FakeAudio:
    status = "Fake audio ready"

    def __init__(self):
        self.key = None
        self.updates = []
        self.stops = 0

    def update(self, key, text, repeating, volume):
        if key != self.key:
            self.updates.append((key, text, repeating, volume))
        self.key = key

    def stop(self):
        self.key = None
        self.stops += 1


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.fixture
def panel(application):
    clock = [100.]
    widget = TestPanel(clock=lambda: clock[0], audio_factory=FakeAudio)
    widget.timer.stop()
    yield widget, clock
    widget.close_resources()
    widget.deleteLater()
    application.processEvents()


def step(widget, clock, seconds):
    clock[0] += seconds
    widget.refresh()


def test_disabled_commands_cannot_enable_output_or_test_session(panel):
    widget, clock = panel
    for action in ("start", "night", "fall", "choking", "cancel", "resolve"):
        assert not widget.command(action)
    widget.toggle_audio()
    assert widget.audio is None and not widget.audio_enabled
    assert not widget.enabled and not widget.warning.isVisible()
    step(widget, clock, 1000)
    assert widget.position == 0


def test_enable_gate_keeps_existing_session_untouched(panel):
    widget, clock = panel
    widget.enable_guard = lambda: False
    assert not widget.enable_session()
    assert not widget.enabled and widget.position == 0
    assert "blocked" in widget.status.text()


def test_manual_fall_has_running_deadline_without_replay_end(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("fall")
    assert widget.engine.snapshot.remaining == 8
    assert widget.warning.isVisible()
    step(widget, clock, 3)
    assert widget.engine.snapshot.remaining == 5
    # Evidence absent; fixed incident deadline continues.
    step(widget, clock, 5)
    assert widget.engine.snapshot.incident == Incident.ALERT_ACTIVE
    step(widget, clock, 60)
    assert widget.engine.snapshot.message_count == 2
    widget.command("cancel")
    assert widget.engine.snapshot.incident == Incident.RESOLVED
    assert not widget.warning.isVisible()


def test_pause_freezes_and_cancels_speech_then_resume_current_snapshot(panel):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("fall")
    assert len(widget.audio.updates) == 1
    step(widget, clock, 1)
    widget.toggle_pause()
    assert widget.audio.key is None and not widget.warning.isVisible()
    step(widget, clock, 100)
    assert widget.engine.snapshot.remaining == 7
    widget.toggle_pause()
    assert widget.warning.isVisible()
    assert len(widget.audio.updates) == 2
    step(widget, clock, 7)
    assert widget.engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert len(widget.audio.updates) == 3


def test_refresh_does_not_duplicate_speech_and_stop_audio_does_not_resolve(panel):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("choking")
    for _ in range(5):
        step(widget, clock, .1)
    assert len(widget.audio.updates) == 1
    assert widget.audio.updates[0][3] == .5
    assert "large green button" in widget.audio.updates[0][1]
    widget.stop_audio()
    assert not widget.audio_enabled and widget.audio.key is None
    assert widget.engine.snapshot.incident == Incident.ALERT_ACTIVE
    widget.command("resolve")
    assert not widget.warning.isVisible()


@pytest.mark.parametrize("mode", ("start", "night"))
def test_manual_choking_available_in_modes_and_posture_cannot_cancel(panel, mode):
    widget, clock = panel
    widget.enable_session()
    widget.command(mode)
    widget.command("choking")
    widget.set_synthetic_evidence(posture="safe", subject_valid=True,
                                  calibrated=True, safe_confirmed=True,
                                  recovery_confirmed=True)
    step(widget, clock, .1)
    assert widget.engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert widget.engine.snapshot.message_count == 1


def test_caregiver_latch_retains_silence_until_departure_independent_night(panel):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("choking")
    changes = []
    widget.silence_changed.connect(changes.append)
    widget.set_synthetic_evidence(posture="safe", subject_valid=True,
                                  caregiver_id="fixture", caregiver_valid=True)
    for _ in range(20):
        step(widget, clock, .1)
    assert widget.caregiver_silent
    assert widget.engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert widget.snapshot.choking
    assert widget.audio.key is None and widget.warning.isVisible()
    assert widget.warning.title.text() == "Choking — TEST ONLY"
    assert "CAREGIVER SILENT" in widget.status.text()
    widget.set_synthetic_evidence()
    step(widget, clock, .5)
    assert widget.caregiver_silent and widget.engine.snapshot.uncertain
    widget.command("night")
    widget.command("choking")
    assert widget.audio.key is None
    widget.set_synthetic_evidence(caregiver_departed=True)
    step(widget, clock, .1)
    assert not widget.caregiver_silent
    assert widget.engine.snapshot.mode == Mode.NIGHT
    assert widget.engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert widget.warning.isVisible() and widget.snapshot.choking
    assert widget.snapshot.choking_silent and widget.audio.key is None
    widget.stop_audio()
    widget.toggle_audio()
    assert widget.audio.key is None  # Opt-in cannot bypass durable choking silence.
    before = widget.snapshot.message_count
    step(widget, clock, 120)
    assert widget.snapshot.message_count == before  # Departure cannot resume SMS repeats.
    assert changes == [True, False]
    widget.command("cancel")
    assert widget.snapshot.incident == Incident.RESOLVED
    assert not widget.warning.isVisible() and widget.audio.key is None


def test_end_session_stops_warning_audio_and_future_commands(panel):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("choking")
    widget.end_session()
    assert not widget.enabled and not widget.audio_enabled
    assert widget.audio.key is None and not widget.warning.isVisible()
    assert not widget.command("fall")
    widget.enable_session()
    assert widget.engine.snapshot.incident == Incident.NONE
    assert widget.position == 0 and not widget.audio_enabled


def test_warning_close_and_escape_explicitly_cancel(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("fall")
    QTest.keyClick(widget.warning, Qt.Key.Key_Escape)
    assert widget.engine.snapshot.incident == Incident.RESOLVED
    widget.command("choking")
    widget.warning.close()
    assert widget.engine.snapshot.incident == Incident.RESOLVED
    assert not widget.warning.isVisible()


def test_primary_one_pointer_controls_fit_small_panel(application, panel):
    widget, _ = panel
    widget.resize(440, 400)
    widget.show()
    application.processEvents()
    assert widget.height() <= 400
    for control in (widget.enable_button, widget.cancel_button, widget.start_button,
                    widget.night_button, widget.fall_button, widget.choking_button,
                    widget.pause_button, widget.stop_audio_button):
        assert control.minimumHeight() >= 60
        assert control.accessibleName()
        assert control.geometry().bottom() <= widget.height()
    assert widget.scroll.horizontalScrollBar().maximum() == 0


def test_fullscreen_warning_allows_choking_escalation_and_audio_stop(panel):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("fall")
    QTest.mouseClick(widget.warning.choking_button, Qt.MouseButton.LeftButton)
    assert widget.snapshot.incident == Incident.ALERT_ACTIVE
    assert widget.snapshot.audio_priority == "choking_maximum_simulated"
    assert widget.warning.countdown.text() == "Immediate test alert"
    QTest.mouseClick(widget.warning.stop_audio_button, Qt.MouseButton.LeftButton)
    assert not widget.audio_enabled and widget.audio.key is None
    assert widget.snapshot.incident == Incident.ALERT_ACTIVE
    assert widget.warning.isVisible()


def test_expired_fall_warning_is_not_labeled_immediate(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("fall")
    step(widget, clock, 8)
    assert widget.warning.countdown.text() == "Test alert active - no message sent"
    assert "Immediate" not in widget.warning.countdown.text()
    widget.warning.showNormal()
    widget.warning.resize(800, 600)
    QApplication.instance().processEvents()
    assert widget.warning.width() <= 800 and widget.warning.height() <= 600
    assert widget.warning.cancel_button.geometry().bottom() <= 600


def test_warning_essential_controls_fit_600px_and_larger_text(application, panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("fall")
    warning = widget.warning
    application.processEvents()
    warning.showNormal()
    application.processEvents()
    warning.resize(800, 600)
    font = warning.font()
    font.setPointSizeF(font.pointSizeF() * 1.35)
    warning.setFont(font)
    warning.reason.setText("Synthetic uncertainty and diagnostic explanation. " * 100)
    application.processEvents()
    assert warning.width() <= 800 and warning.height() <= 600
    for control in (warning.choking_button, warning.stop_audio_button, warning.cancel_button):
        assert control.geometry().bottom() <= warning.height()
        assert control.geometry().left() >= 0
        assert control.geometry().right() <= warning.width()
    assert warning.cancel_button.height() >= 100
    assert warning.choking_button.height() >= 60
    assert warning.stop_audio_button.height() >= 60
    assert warning.scroll.horizontalScrollBar().maximum() == 0


def test_audio_opt_in_signal_allows_manual_tone_arbitration(panel):
    widget, clock = panel
    changes = []
    widget.audio_enabled_changed.connect(changes.append)
    widget.enable_session()
    widget.toggle_audio()
    widget.stop_audio()
    widget.stop_audio()
    assert changes == [True, False]


def test_choking_reply_stops_repeats_but_retains_popup_until_manual_cancel(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("choking")
    widget.command("reply")
    assert widget.snapshot.incident == Incident.ALERT_ACTIVE
    assert widget.snapshot.choking and widget.warning.isVisible()
    count = widget.snapshot.message_count
    step(widget, clock, 180)
    assert widget.snapshot.message_count == count
    widget.command("resolve")
    assert widget.snapshot.incident == Incident.RESOLVED
    assert not widget.warning.isVisible()


def test_contact_911_is_visual_only_and_never_resolves_or_changes_output(panel, monkeypatch):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("fall")
    assert not widget.warning.contact_911_button.isVisible()
    assert not widget.contact_911()
    widget.command("choking")
    assert widget.warning.contact_911_button.isVisible()
    before = widget.snapshot
    audio_count = len(widget.audio.updates)
    def forbidden(*args, **kwargs):
        raise AssertionError("Contact911 must not invoke any engine action or external dialer")
    monkeypatch.setattr(widget.engine, "command", forbidden)
    import os, subprocess, webbrowser
    monkeypatch.setattr(os, "startfile", forbidden, raising=False)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(webbrowser, "open", forbidden)
    QTest.mouseClick(widget.warning.contact_911_button, Qt.MouseButton.LeftButton)
    assert widget.snapshot == before
    assert widget.snapshot.incident == Incident.ALERT_ACTIVE
    assert widget.warning.contact_911_status.isVisible()
    assert widget.warning.contact_911_status.text() == "911 contact simulated; no call placed. Choking remains unresolved."
    assert len(widget.audio.updates) == audio_count
    assert widget.warning.isVisible()


def test_contact_911_confirmation_and_all_choking_actions_fit_600px(application, panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("choking")
    widget.contact_911()
    warning = widget.warning
    application.processEvents()
    warning.showNormal()
    application.processEvents()
    warning.resize(800, 600)
    font = warning.font()
    font.setPointSizeF(font.pointSizeF() * 1.35)
    warning.setFont(font)
    warning.reason.setText("Retained synthetic choking uncertainty. " * 100)
    application.processEvents()
    assert warning.width() <= 800 and warning.height() <= 600
    for control in (warning.choking_button, warning.stop_audio_button,
                    warning.contact_911_button, warning.cancel_button):
        assert control.isVisible() and control.minimumHeight() >= 60
        assert control.geometry().bottom() <= warning.height()
        assert control.geometry().right() <= warning.width()
    assert warning.cancel_button.minimumHeight() >= 100
    assert warning.contact_911_status.geometry().bottom() < warning.cancel_button.geometry().top()
    assert warning.scroll.horizontalScrollBar().maximum() == 0


def test_cancel_clears_simulated_contact_911_confirmation_for_new_incident(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("choking")
    widget.contact_911()
    widget.command("cancel")
    widget.command("choking")  # Same source tick is deduplicated by engine.
    step(widget, clock, .1)
    widget.command("choking")
    assert widget.snapshot.choking
    assert not widget.warning.contact_911_status.isVisible()


def test_durable_choking_silence_survives_volume_change_but_manual_cancel_allows_new_audio(panel):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("choking")
    widget.set_synthetic_evidence(posture="safe", subject_valid=True,
                                  caregiver_id="fixture", caregiver_valid=True)
    for _ in range(20):
        step(widget, clock, .1)
    widget.set_synthetic_evidence(caregiver_departed=True)
    step(widget, clock, .1)
    assert widget.snapshot.choking_silent and widget.warning.isVisible()
    widget.volume = lambda: .2
    widget.volume_changed()
    widget.stop_audio()
    widget.toggle_audio()
    assert widget.audio.key is None
    widget.command("cancel")
    step(widget, clock, .1)
    widget.command("choking")
    assert widget.snapshot.choking and not widget.snapshot.choking_silent
    assert widget.audio.key is not None
    assert widget.audio.updates[-1][3] == .2


def test_pausing_choking_freezes_test_but_retains_popup_until_manual_cancel(panel):
    widget, clock = panel
    widget.enable_session()
    widget.toggle_audio()
    widget.command("choking")
    widget.toggle_pause()
    assert not widget.playing and widget.audio.key is None
    assert widget.snapshot.choking and widget.warning.isVisible()
    assert widget.warning.contact_911_button.isVisible()
    widget.command("cancel")
    assert not widget.warning.isVisible()


def test_contact_911_command_route_guards_disabled_and_non_choking_and_does_not_resolve(panel):
    widget, clock = panel
    assert not widget.command("contact_911")
    widget.enable_session()
    assert not widget.command("contact_911")
    widget.command("fall")
    assert not widget.command("contact_911")
    widget.command("choking")
    before = widget.snapshot
    assert widget.command("contact_911")
    assert widget.command("contact_911")
    assert widget.snapshot == before and widget.snapshot.incident == Incident.ALERT_ACTIVE
    widget.command("cancel")
    assert not widget.command("contact_911")


def test_warning_foreground_requested_once_per_transition_and_explicit_contact(panel, monkeypatch):
    widget, clock = panel
    calls = []
    monkeypatch.setattr(widget.warning, "bring_forward", lambda: calls.append("foreground"))
    widget.enable_session()
    assert calls == []
    widget.command("fall")
    assert calls == ["foreground"]
    for _ in range(5):
        step(widget, clock, .1)
    assert calls == ["foreground"]
    widget.command("choking")
    assert calls == ["foreground", "foreground"]
    for _ in range(5):
        step(widget, clock, .1)
    assert calls == ["foreground", "foreground"]
    widget.command("contact_911")
    assert len(calls) == 3
    step(widget, clock, .1)
    assert len(calls) == 3


def test_windows_foreground_helper_targets_only_warning_with_no_geometry_changes():
    from types import SimpleNamespace
    from tyler_safety_monitor.warning_ui import request_windows_foreground
    calls = []
    def position(hwnd, order, x, y, width, height, flags):
        calls.append(("position", hwnd, order.value, x, y, width, height, flags))
        return 1
    def foreground(hwnd):
        calls.append(("foreground", hwnd))
        return 1
    fake_user32 = SimpleNamespace(SetWindowPos=position, SetForegroundWindow=foreground)
    assert request_windows_foreground(1234, fake_user32)
    assert calls[0][0:2] == ("position", 1234)
    assert calls[0][3:7] == (0, 0, 0, 0)
    assert calls[0][-1] == 0x0001 | 0x0002 | 0x0040 | 0x0200
    assert calls[1] == ("foreground", 1234)
    def denied(hwnd):
        return 0
    fake_user32.SetForegroundWindow = denied
    assert not request_windows_foreground(1234, fake_user32)
