"""Standalone feature/synthetic simulation controls; no hardware or alert adapters."""
from __future__ import annotations

from pathlib import Path
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from .replay import load_feature_sequence
from .simulation_replay import SimulationRunner, builtin_scenarios, feature_scenario
from .scrolling import PanelWheelGuard
from .messaging_ui import MessagingControls


def _button(label, callback):
    control = QPushButton(label)
    control.setMinimumHeight(60)
    control.setAccessibleName(label.replace("\n", " "))
    control.clicked.connect(callback)
    return control


def _value(value):
    return str(getattr(value, "value", value)).replace("_", " ")


class SimulationPanel(QWidget):
    """Own an in-memory simulation clock, wholly independent of live capture."""

    def __init__(self, parent=None, clock=time.monotonic):
        super().__init__(parent)
        self.clock = clock
        self.scenarios = list(builtin_scenarios())
        self._feature_index = None
        self.runner = SimulationRunner(self.scenarios[0])
        layout = QVBoxLayout(self)
        self.banner = QLabel("SIMULATION ONLY • No messages or automatic sounds. No Windows audio changes.")
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("background:#5b3d11;color:#ffe4ac;padding:10px;font-weight:700")
        layout.addWidget(self.banner)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.status.setAccessibleName("Simulation status")
        layout.addWidget(self.status)
        self.reason = QLabel()
        self.reason.setWordWrap(True)
        self.effects = QLabel()
        self.effects.setWordWrap(True)
        self.effects.setAccessibleName("Simulated effects only")
        self.cancel_button = _button("Cancel Simulated\nAlert", lambda: self.command("cancel"))
        self.cancel_button.setStyleSheet("background:#2e624b;font-weight:700")
        layout.addWidget(self.cancel_button)
        self.play_button = _button("Play / Pause\nSimulation", self.toggle_play)
        layout.addWidget(self.play_button)

        panel = QWidget()
        controls = QVBoxLayout(panel)
        # Extra explanations can grow without forcing the dashboard taller than
        # the screen. Current state/countdown and Cancel/Play stay outside scroll.
        controls.addWidget(self.reason)
        controls.addWidget(self.effects)
        note = QLabel("This separate simulation does not use the live camera. Synthetic evidence tests the rules; saved features remain uncalibrated. No movement is needed.")
        note.setWordWrap(True)
        controls.addWidget(note)
        self.selector = QComboBox()
        self.selector.setMinimumHeight(60)
        self.selector.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.selector.setAccessibleName("Simulation scenario")
        for scenario in self.scenarios:
            self.selector.addItem(scenario.name)
        controls.addWidget(self.selector)
        self.description = QLabel(self.scenarios[0].description)
        self.description.setWordWrap(True)
        controls.addWidget(self.description)
        self.selector.currentIndexChanged.connect(self.select_scenario)
        controls.addWidget(_button("Restart Scenario\nPaused", self.restart))
        controls.addWidget(_button("Advance 10 Seconds\nSimulation", self.step))
        controls.addWidget(_button("Advance 60 Seconds\nSimulation", self.advance_minute))
        controls.addWidget(_button("Open Approved\nFeature Replay", self.open_feature_replay))
        self.import_status = QLabel("Opening an existing feature file is read only; it cannot approve personal safety boundaries.")
        self.import_status.setWordWrap(True)
        controls.addWidget(self.import_status)
        for label, action in (
            ("Start Simulation", "start"),
            ("Night Mode\nSimulation", "night"),
            ("Possible Fall\nSimulation", "fall"),
            ("Choking\nSIMULATION ONLY", "choking"),
            ("Resolve Simulated\nIncident", "resolve"),
        ):
            control = _button(label, lambda checked=False, action=action: self.command(action))
            if action == "choking":
                control.setStyleSheet("background:#713540;font-weight:700")
            controls.addWidget(control)
        self.messaging_controls = MessagingControls(
            lambda: self.runner.messaging, lambda: self.runner.snapshot,
            lambda: self.runner.position(self.clock()), self.receive_simulated_reply, self,
        )
        controls.addWidget(self.messaging_controls)
        controls.addStretch()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(panel)
        self.wheel_guard = PanelWheelGuard(self.scroll)
        layout.addWidget(self.scroll, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.render(self.runner.engine.snapshot)

    def select_scenario(self, index):
        if index < 0:
            return
        self.runner.messaging.close()
        self.runner = SimulationRunner(self.scenarios[index])
        self.messaging_controls.reset()
        self.description.setText(self.scenarios[index].description)
        self.render(self.runner.engine.snapshot)

    def restart(self):
        self.runner.rewind(self.clock())
        self.messaging_controls.reset()
        self.render(self.runner.engine.snapshot)

    def step(self):
        self.render(self.runner.step(10., self.clock()))

    def advance_minute(self):
        self.render(self.runner.step(60., self.clock()))

    def toggle_play(self):
        now = self.clock()
        if self.runner.playing:
            self.runner.pause(now)
        else:
            self.runner.play(now)
        self.refresh()

    def command(self, action):
        self.render(self.runner.command(action, self.clock()))

    def receive_simulated_reply(self, reply):
        valid = self.runner.receive_reply(reply, self.clock())
        self.render(self.runner.snapshot)
        return valid

    def refresh(self):
        if self.runner.playing:
            self.render(self.runner.advance(self.clock()))
        else:
            self.render(self.runner.engine.snapshot)

    def render(self, snapshot):
        self.messaging_controls.render()
        remaining = getattr(snapshot, "remaining", None)
        countdown = "none" if remaining is None else f"{max(0.0, remaining):.1f} seconds"
        uncertain = "UNCERTAIN" if snapshot.uncertain else "synthetic evidence available"
        playback = "finished; restart to advance timers" if self.runner.finished else ("playing" if self.runner.playing else "paused")
        self.status.setText(
            f"SIMULATION • {_value(snapshot.mode)} / {_value(snapshot.incident)}\n"
            f"Countdown: {countdown} • {uncertain}\n"
            f"Fault: {getattr(snapshot, 'fault', False)} • "
            f"Night: {getattr(snapshot, 'night', False)}\n"
            f"Caregiver silence retained: {getattr(snapshot, 'caregiver', False)} • "
            f"Current evidence: {getattr(snapshot, 'caregiver_current', False)}\n"
            f"Playback: {playback} • "
            f"{self.runner.position(self.clock()):.1f} seconds"
        )
        caregiver_gap = bool(getattr(snapshot, "caregiver", False)
                             and not getattr(snapshot, "caregiver_current", False))
        self.reason.setText("Caregiver location is uncertain; departure is not confirmed."
                            if caregiver_gap else str(snapshot.reason))
        latest = "none" if not snapshot.effects else _value(snapshot.effects[-1].kind)
        self.effects.setText(
            f"Simulated message intents: {snapshot.message_count} • Last effect: {latest}\n"
            f"Simulated audio priority: {_value(snapshot.audio_priority)}. No audio or messages sent."
        )

    def open_feature_replay(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open already-approved local feature replay (read only)", "", "Feature JSON (*.json)"
        )
        if not filename:
            return
        try:
            scenario = feature_scenario(load_feature_sequence(Path(filename)))
        except (OSError, ValueError) as error:
            self.import_status.setText(f"Replay not loaded: {error}")
            return
        if self._feature_index is None:
            self._feature_index = len(self.scenarios)
            self.scenarios.append(scenario)
            self.selector.addItem(scenario.name)
        else:
            self.scenarios[self._feature_index] = scenario
            self.selector.setItemText(self._feature_index, scenario.name)
        self.selector.setCurrentIndex(self._feature_index)
        self.select_scenario(self._feature_index)
        self.import_status.setText("Existing replay loaded read only. Personal thresholds remain uncalibrated.")

    def shutdown(self):
        self.timer.stop()
        if self.runner.playing:
            self.runner.pause(self.clock())
        self.runner.messaging.close()
