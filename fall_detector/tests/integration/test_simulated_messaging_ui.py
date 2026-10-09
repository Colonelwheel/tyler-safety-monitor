"""M4 fake transport/UI integration; all clocks, audio and evidence are synthetic."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
import socket
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from tyler_safety_monitor.test_ui import TestPanel
from tyler_safety_monitor.simulation_ui import SimulationPanel
from tyler_safety_monitor.simulation_replay import Scenario, SimulationRunner, SimulationCommand
from tyler_safety_monitor.simulation_state import Engine, Config, Incident
from tyler_safety_monitor.simulation_messaging import MessagingSession


class FakeAudio:
    status = "Synthetic output only"
    def __init__(self):
        self.updates, self.key = [], None
    def update(self, key, text, repeating, volume):
        if key != self.key:
            self.updates.append((key, text, repeating, volume))
        self.key = key
    def stop(self):
        self.key = None


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    return application


@pytest.fixture
def panel(app, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No real transport is permitted")
    monkeypatch.setattr(socket, "create_connection", forbidden)
    clock = [100.]
    widget = TestPanel(clock=lambda: clock[0], audio_factory=FakeAudio)
    widget.timer.stop()
    yield widget, clock
    widget.close_resources()
    widget.deleteLater()
    app.processEvents()


def step(widget, clock, seconds):
    clock[0] += seconds
    widget.refresh()


@pytest.mark.parametrize("outcome", ["rejected", "failed", "undelivered", "unknown"])
def test_all_failed_unknown_attempts_use_existing_ten_slot_budget(panel, outcome):
    widget, clock = panel
    widget.enable_session()
    widget.messaging_controls.outcome.setCurrentIndex(widget.messaging_controls.outcome.findData(outcome))
    widget.command("choking")
    for _ in range(9):
        step(widget, clock, 60)
    step(widget, clock, 6000)
    summary = widget.messaging.summary(widget.snapshot.episode_id)
    assert summary.attempted == widget.snapshot.message_count == 10
    assert summary.delivered == 0
    assert summary.unknown == (10 if outcome == "unknown" else 0)
    assert len(widget.messaging.records) == 10
    assert widget.warning.isVisible() and widget.snapshot.choking
    assert widget.audio is None
    assert "Attempts 10" in widget.messaging_controls.status.text()
    assert widget.warning.messaging_status.isVisible()
    assert "Simulated messaging unavailable" in widget.warning.messaging_status.text()
    assert "URGENT" in widget.warning.messaging_status.text()


def test_choking_upgrade_new_budget_preview_and_old_reply_filter(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("fall")
    step(widget, clock, 8)
    fall_episode = widget.snapshot.episode_id
    assert "URGENT" not in widget.messaging_controls.preview.text()
    old_reply = widget.messaging.make_reply(widget.position)
    step(widget, clock, .1)
    widget.command("choking")
    assert widget.snapshot.episode_id > fall_episode
    assert widget.snapshot.message_count == 1
    assert len(widget.messaging.records) == 2
    assert "URGENT" in widget.messaging_controls.preview.text()
    assert not widget.receive_simulated_reply(old_reply)
    step(widget, clock, .1)
    assert widget.receive_simulated_reply(widget.messaging.make_reply(widget.position))
    step(widget, clock, 600)
    assert widget.snapshot.message_count == 1
    assert widget.snapshot.choking and widget.warning.isVisible()
    widget.command("cancel")
    assert "URGENT" in widget.messaging_controls.preview.text()  # Retained episode history.


@pytest.mark.parametrize("field,value", [
    ("sender", "synthetic:other"), ("recipient", "synthetic:other"),
    ("created", 0.), ("created", 1000.), ("session_id", "old-session"),
])
def test_invalid_reply_does_not_resolve_stop_or_silence_choking(panel, field, value):
    widget, clock = panel
    widget.enable_session()
    widget.command("choking")
    step(widget, clock, 1)
    reply = replace(widget.messaging.make_reply(widget.position), **{field: value})
    assert not widget.receive_simulated_reply(reply)
    step(widget, clock, 59)
    assert widget.snapshot.message_count == 2
    assert widget.snapshot.choking and not widget.snapshot.choking_silent
    assert widget.warning.isVisible()


def test_valid_reply_at_repeat_deadline_wins_and_is_duplicate_protected(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("choking")
    clock[0] += 60  # Reply reaches owning reducer before equal-time expiry tick.
    reply = widget.messaging.make_reply(widget.position)
    assert widget.receive_simulated_reply(reply)
    assert not widget.receive_simulated_reply(reply)
    step(widget, clock, 600)
    assert widget.snapshot.message_count == 1
    assert widget.snapshot.choking and widget.warning.isVisible()
    assert not widget.snapshot.caregiver and not widget.snapshot.choking_silent


def test_delayed_result_freezes_on_pause_and_delivery_never_resolves(panel):
    widget, clock = panel
    widget.enable_session()
    controls = widget.messaging_controls
    controls.outcome.setCurrentIndex(controls.outcome.findData("delayed"))
    controls.delay.setValue(5)
    widget.command("choking")
    assert widget.messaging.records[0].status == "delayed"
    widget.toggle_pause()
    step(widget, clock, 100)
    assert widget.messaging.records[0].status == "delayed"
    widget.toggle_pause()
    step(widget, clock, 5)
    assert widget.messaging.records[0].status == "delivered"
    assert widget.snapshot.choking and widget.warning.isVisible()
    assert widget.snapshot.incident == Incident.ALERT_ACTIVE


def test_end_new_session_rejects_old_reply_and_delivery_without_replay(panel):
    widget, clock = panel
    widget.enable_session()
    widget.command("choking")
    step(widget, clock, 1)
    previous = widget.messaging
    reply = previous.make_reply(widget.position)
    message = previous.records[0]
    widget.end_session()
    assert not previous.apply_status(previous.session_id, message.message_id, "delivered", 1)
    widget.enable_session()
    assert widget.messaging.session_id != previous.session_id
    assert widget.messaging.records == () and widget.snapshot.message_count == 0
    assert not widget.receive_simulated_reply(reply)
    assert not widget.audio_enabled and widget.audio is None


def test_unavailable_speech_opt_in_respects_persistent_choking_silence(panel):
    widget, clock = panel
    widget.enable_session()
    widget.messaging.set_outcome("unknown")
    widget.command("choking")
    assert widget.audio is None
    widget.toggle_audio()
    assert "messaging unavailable" in widget.audio.updates[-1][1]
    widget.set_synthetic_evidence(posture="safe", subject_valid=True,
                                  caregiver_id="synthetic-caregiver", caregiver_valid=True)
    for _ in range(21):
        step(widget, clock, .1)
    assert widget.snapshot.caregiver and widget.audio.key is None
    widget.set_synthetic_evidence(caregiver_departed=True)
    assert widget.snapshot.choking_silent and widget.audio.key is None
    widget.volume = lambda: .2
    widget.volume_changed()
    widget.stop_audio()
    widget.toggle_audio()
    assert widget.audio.key is None and widget.warning.isVisible()
    widget.command("cancel")
    step(widget, clock, .1)
    widget.command("choking")
    assert widget.audio.key is not None and widget.audio.updates[-1][3] == .2


def test_outbound_history_fault_does_not_block_ui_caregiver_acknowledgement(panel):
    widget, clock = panel
    widget.enable_session()
    widget.engine = Engine(Config(max_effects=1))
    widget.messaging = MessagingSession()
    # Two effects between deliveries creates a genuine history-gap fault.
    widget.engine.command("fall", 0)
    widget.engine.command("cancel", 1)
    widget.engine.command("choking", 2)
    clock[0] = 102.
    widget.render()
    assert widget.messaging.error
    clock[0] = 103.
    assert widget.receive_simulated_reply(widget.messaging.make_reply(widget.position))
    step(widget, clock, 600)
    assert widget.snapshot.message_count == 1
    assert widget.messaging.error and widget.warning.isVisible() and widget.snapshot.choking


def test_quiet_runner_consumes_every_effect_and_rewind_rejects_stale_results():
    scenario = Scenario("Many synthetic events", "History exceeds Engine ring", tuple(
        SimulationCommand(float(i), action) for i in range(300)
        for action in (("fall", "cancel") if i % 2 == 0 else ("choking", "cancel"))
    ), 400)
    # Commands at one timestamp preserve source ordering; this exercises every
    # transition, not an end-only scan of an evicted effect history.
    runner = SimulationRunner(scenario)
    runner.advance_to(300)
    assert runner.messaging.error is None
    assert len(runner.messaging.records) == 150
    previous = runner.messaging
    runner.rewind(500)
    assert runner.messaging.session_id != previous.session_id
    assert runner.messaging.records == ()
    assert not previous.receive_reply(previous.make_reply(301), runner.snapshot, 301)


def test_quiet_simulation_delays_freeze_and_matching_reply_stops_only_repeats(app):
    clock = [100.]
    widget = SimulationPanel(clock=lambda: clock[0])
    widget.timer.stop()
    widget.runner = SimulationRunner(Scenario("Manual synthetic only", "No camera", (), 1000))
    try:
        widget.messaging_controls.reset()
        widget.messaging_controls.outcome.setCurrentIndex(widget.messaging_controls.outcome.findData("delayed"))
        widget.command("choking")
        first = widget.runner.messaging.records[0]
        clock[0] += 100
        widget.refresh()
        assert widget.runner.messaging.records[0].status == "delayed"
        widget.toggle_play()
        clock[0] += 5
        widget.refresh()
        assert widget.runner.messaging.records[0].status == "delivered"
        reply = widget.runner.messaging.make_reply(widget.runner.position(clock[0]))
        assert widget.receive_simulated_reply(reply)
        clock[0] += 100
        widget.refresh()
        assert widget.runner.snapshot.choking and widget.runner.snapshot.message_count == 1
        assert widget.runner.messaging.records[0].message_id == first.message_id
        assert "No audio or messages sent" in widget.effects.text()
    finally:
        widget.shutdown()
        widget.deleteLater()
        app.processEvents()


def test_simulated_controls_fit_without_horizontal_scroll_and_keep_cancel_visible(panel, app):
    widget, clock = panel
    widget.enable_session()
    widget.setStyleSheet("QWidget {font-size:16px;}")
    widget.resize(440, 630)
    widget.show()
    app.processEvents()
    widget.scroll.verticalScrollBar().setValue(widget.scroll.verticalScrollBar().maximum())
    app.processEvents()
    assert widget.scroll.horizontalScrollBar().maximum() == 0
    assert widget.rect().contains(widget.cancel_button.geometry())
    for control in widget.messaging_controls.findChildren(QPushButton):
        assert control.minimumHeight() >= 60 and control.accessibleName()
    widget.hide()


def test_warning_delivery_text_reachable_at_800x600_with_enlarged_font(panel, app):
    from PySide6.QtCore import QPoint
    widget, clock = panel
    widget.enable_session()
    widget.messaging.set_outcome("unknown")
    widget.command("choking")
    warning = widget.warning
    warning.showNormal()
    warning.resize(800, 600)
    font = warning.font()
    font.setPointSizeF(font.pointSizeF() * 1.35)
    warning.setFont(font)
    app.processEvents()
    warning.scroll.verticalScrollBar().setValue(warning.scroll.verticalScrollBar().maximum())
    app.processEvents()
    viewport = warning.scroll.viewport()
    bottom = warning.messaging_status.mapTo(viewport, QPoint(0, warning.messaging_status.height() - 1))
    assert 0 <= bottom.y() < viewport.height()
    assert warning.scroll.horizontalScrollBar().maximum() == 0
    for control in (warning.cancel_button, warning.choking_button,
                    warning.stop_audio_button, warning.contact_911_button):
        assert control.parent() is warning
        assert warning.rect().contains(control.geometry())
        assert control.isVisible()
    assert "Simulated messaging unavailable" in warning.messaging_status.text()


def test_one_action_minute_advance_exercises_repeat_without_real_wait(app):
    clock = [100.]
    widget = SimulationPanel(clock=lambda: clock[0])
    widget.timer.stop()
    try:
        widget.selector.setCurrentIndex(widget.selector.findText("Unacknowledged choking messages"))
        widget.refresh()
        assert widget.runner.snapshot.message_count == 0  # Selection stays paused until an action.
        button = next(control for control in widget.findChildren(QPushButton)
                      if control.text() == "Advance 60 Seconds\nSimulation")
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert widget.runner.position(clock[0]) == 60
        assert widget.runner.snapshot.message_count == 2
        assert len(widget.runner.messaging.records) == 2
        assert not widget.runner.playing
        for _ in range(9):
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert widget.runner.position(clock[0]) == 600
        assert widget.runner.snapshot.message_count == 10
        assert len(widget.runner.messaging.records) == 10
        assert widget.runner.snapshot.choking
        assert "No audio or messages sent" in widget.effects.text()
    finally:
        widget.shutdown()
        widget.deleteLater()
        app.processEvents()
