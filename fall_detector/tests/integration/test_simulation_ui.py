"""Simulation controls have their own clock and never call hardware adapters."""
import os
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QSystemTrayIcon

from tyler_safety_monitor import simulation_ui as ui
from tyler_safety_monitor.simulation_replay import Scenario, SimulationRunner


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.fixture
def panel(application):
    clock = [100.0]
    widget = ui.SimulationPanel(clock=lambda: clock[0])
    widget.timer.stop()
    yield widget, clock
    widget.shutdown()
    widget.deleteLater()
    application.processEvents()


def test_simulation_starts_paused_and_buttons_need_one_pointer(panel):
    widget, clock = panel
    assert not widget.runner.playing
    assert widget.runner.position(clock[0]) == 0
    assert "SIMULATION ONLY" in widget.banner.text()
    assert "No Windows audio changes" in widget.banner.text()
    for control in widget.findChildren(QPushButton):
        assert control.minimumHeight() >= 60
        assert control.accessibleName()
    assert widget.selector.minimumHeight() >= 60
    clock[0] += 200
    widget.refresh()
    assert widget.runner.position(clock[0]) == 0


def test_paused_manual_warning_countdown_freezes_and_cancel_is_immediate(panel):
    widget, clock = panel
    widget.runner = SimulationRunner(Scenario("Manual only", "No camera evidence", (), 100))
    QTest.mouseClick(widget.findChildren(QPushButton)[0], Qt.MouseButton.LeftButton)
    widget.command("fall")
    before = widget.runner.engine.snapshot
    assert before.remaining == pytest.approx(8)
    clock[0] += 120
    widget.refresh()
    assert widget.runner.engine.snapshot.remaining == pytest.approx(8)
    QTest.mouseClick(widget.cancel_button, Qt.MouseButton.LeftButton)
    assert str(widget.runner.engine.snapshot.incident.value) == "RESOLVED"
    assert "No audio or messages sent" in widget.effects.text()


def test_pause_and_restart_do_not_count_wall_clock_gaps(panel):
    widget, clock = panel
    widget.runner = SimulationRunner(Scenario("Manual only", "No camera evidence", (), 100))
    widget.toggle_play()
    widget.command("fall")
    clock[0] += 2
    widget.refresh()
    assert widget.runner.engine.snapshot.remaining == pytest.approx(6)
    widget.toggle_play()
    clock[0] += 100
    widget.refresh()
    assert widget.runner.engine.snapshot.remaining == pytest.approx(6)
    widget.toggle_play()
    clock[0] += 1
    widget.refresh()
    assert widget.runner.engine.snapshot.remaining == pytest.approx(5)
    widget.restart()
    assert not widget.runner.playing
    assert widget.runner.position(clock[0]) == 0
    assert widget.runner.engine.snapshot.remaining is None


def test_cancel_and_play_controls_stay_visible_with_scrolled_setup(panel, application):
    widget, _ = panel
    widget.setStyleSheet("QWidget {font-size:16px;}")
    widget.runner = SimulationRunner(next(scenario for scenario in widget.scenarios
                                         if scenario.name == "Caregiver silence overrides choking"))
    widget.render(widget.runner.advance_to(4))
    widget.resize(440, 630)
    widget.show()
    application.processEvents()
    widget.scroll.verticalScrollBar().setValue(widget.scroll.verticalScrollBar().maximum())
    application.processEvents()
    for control in (widget.cancel_button, widget.play_button):
        assert widget.rect().contains(control.geometry())
        assert control.parent() is widget
    assert widget.scroll.horizontalScrollBar().maximum() == 0
    widget.hide()


def test_loaded_features_are_read_only_and_previous_import_is_memory_bounded(panel, monkeypatch):
    widget, _ = panel
    original_count = len(widget.scenarios)
    loaded = []
    monkeypatch.setattr(ui.QFileDialog, "getOpenFileName", lambda *args: ("approved.json", ""))
    monkeypatch.setattr(ui, "load_feature_sequence", lambda path: loaded.append(path) or object())
    scenario = Scenario("Approved replay — uncalibrated", "No personal thresholds", (), 10)
    monkeypatch.setattr(ui, "feature_scenario", lambda sequence: scenario)
    widget.open_feature_replay()
    widget.open_feature_replay()
    assert loaded == [Path("approved.json"), Path("approved.json")]
    assert len(widget.scenarios) == original_count + 1
    assert not widget.runner.playing
    assert widget.description.text() == "No personal thresholds"


def test_invalid_feature_load_keeps_existing_simulation(panel, monkeypatch):
    widget, _ = panel
    original = widget.runner
    monkeypatch.setattr(ui.QFileDialog, "getOpenFileName", lambda *args: ("invalid.json", ""))
    def reject(path):
        raise ValueError("invalid feature schema")
    monkeypatch.setattr(ui, "load_feature_sequence", reject)
    widget.open_feature_replay()
    assert widget.runner is original
    assert "Replay not loaded" in widget.import_status.text()


def test_dashboard_simulation_commands_do_not_change_camera_capture_or_manual_audio(application, monkeypatch):
    from tyler_safety_monitor import dashboard
    from tyler_safety_monitor.settings import AppSettings
    class Sound:
        def __init__(self):
            self.calls = []
        def stop(self):
            self.calls.append("stop")
        def play(self, volume):
            self.calls.append("play")
    class Tray:
        ActivationReason = QSystemTrayIcon.ActivationReason
        @staticmethod
        def isSystemTrayAvailable():
            return False
        def __init__(self, *args):
            self.activated = SimpleNamespace(connect=lambda callback: None)
        def setToolTip(self, *args): pass
        def setContextMenu(self, *args): pass
        def hide(self): pass
    monkeypatch.setattr(dashboard, "TestSound", Sound)
    monkeypatch.setattr(dashboard, "QSystemTrayIcon", Tray)
    monkeypatch.setattr(dashboard, "load_settings", lambda: (AppSettings(), "synthetic"))
    monkeypatch.setattr(dashboard, "CameraCapture", lambda *args: pytest.fail("No camera access allowed"))
    window = dashboard.Dashboard(Path("unused.task"), enable_camera=False)
    window.timer.stop()
    window.simulation.timer.stop()
    try:
        assert window.tabs.tabText(2) == "Simulation"
        settings = window.settings
        for action in ("start", "fall", "cancel", "night", "choking", "resolve"):
            window.simulation.command(action)
        index = next(i for i, scenario in enumerate(window.simulation.scenarios)
                     if scenario.name == "Caregiver silence overrides choking")
        window.simulation.selector.setCurrentIndex(index)
        snapshot = window.simulation.runner.advance_to(4)
        assert snapshot.caregiver
        assert snapshot.audio_priority == "caregiver_silent"
        assert snapshot.message_count == 1
        assert window.capture is None and window.pose is None
        assert window.settings is settings
        assert window.sound.calls == []
        assert not window.tools.samples
    finally:
        window.shutdown()
        assert not window.simulation.timer.isActive()
        window.deleteLater()
        application.processEvents()
