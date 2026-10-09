"""Manual test session, independent of camera, calibration and feature replay."""
from __future__ import annotations

import time

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QLabel, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from .alert_audio import AlertAudio
from .simulation_state import Engine, Evidence, Incident
from .scrolling import PanelWheelGuard
from .warning_ui import WarningWindow
from .simulation_messaging import MessagingSession
from .messaging_ui import MessagingControls


def _button(label, callback):
    button = QPushButton(label)
    button.setMinimumHeight(60)
    button.setAccessibleName(label.replace("\n", " "))
    button.clicked.connect(callback)
    return button


class TestPanel(QWidget):
    """Opt-in test controls; hotkeys cannot enable a session or audible output."""
    __test__ = False
    silence_changed = Signal(bool)
    enabled_changed = Signal(bool)
    audio_enabled_changed = Signal(bool)

    def __init__(self, parent=None, clock=time.monotonic, volume=lambda: .5,
                 audio_factory=AlertAudio, enable_guard=lambda: True):
        super().__init__(parent)
        self.clock, self.volume = clock, volume
        self.audio_factory, self.enable_guard = audio_factory, enable_guard
        self.engine = Engine()
        self.messaging = MessagingSession()
        self.enabled = False
        self.playing = False
        self.audio_enabled = False
        self.audio = None
        self._position = 0.
        self._anchor = None
        self._last_observation = None
        self._synthetic = None
        self._silence = False
        self._mode_announcement = None
        self._contacted_911 = False
        self._warning_key = None
        self.warning = WarningWindow(self)
        self.warning.cancel_requested.connect(lambda: self.command("cancel"))
        self.warning.choking_requested.connect(lambda: self.command("choking"))
        self.warning.stop_audio_requested.connect(self.stop_audio)
        self.warning.contact_911_requested.connect(self.contact_911)
        layout = QVBoxLayout(self)
        self.banner = QLabel("TEST ONLY • Messages/Windows audio switching simulated.")
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("background:#5b3d11;color:#ffe4ac;font-weight:700")
        layout.addWidget(self.banner)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QGridLayout()
        self.enable_button = _button("Enable Test Session", self.toggle_session)
        self.cancel_button = _button("Cancel Test Alert", lambda: self.command("cancel"))
        self.start_button = _button("Start — Test", lambda: self.command("start"))
        self.night_button = _button("Night — Test", lambda: self.command("night"))
        self.fall_button = _button("Possible Fall — Test", lambda: self.command("fall"))
        self.choking_button = _button("Choking — TEST ONLY", lambda: self.command("choking"))
        self.choking_button.setStyleSheet("background:#713540;font-weight:700")
        self.pause_button = _button("Pause Test Clock", self.toggle_pause)
        self.stop_audio_button = _button("Stop Test Audio", self.stop_audio)
        for index, control in enumerate((self.enable_button, self.cancel_button, self.start_button,
                                        self.night_button, self.fall_button, self.choking_button,
                                        self.pause_button, self.stop_audio_button)):
            buttons.addWidget(control, index // 2, index % 2)
        layout.addLayout(buttons)
        details = QWidget()
        controls = QVBoxLayout(details)
        self.reason = QLabel()
        self.reason.setWordWrap(True)
        self.reason.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        controls.addWidget(self.reason)
        self.audio_status = QLabel("Speech/sounds OFF. No microphone listener.")
        self.audio_status.setWordWrap(True)
        controls.addWidget(self.audio_status)
        self.audio_button = _button("Enable Local Test Speech / Sounds", self.toggle_audio)
        controls.addWidget(self.audio_button)
        note = QLabel("Synthetic inputs below repeat only explicitly selected test facts. They never read live candidates or approve personal boundaries. No movement is needed.")
        note.setWordWrap(True)
        controls.addWidget(note)
        self.evidence_selector = QComboBox()
        self.evidence_selector.setMinimumHeight(60)
        self.evidence_selector.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.evidence_selector.setAccessibleName("Synthetic test evidence only")
        self.evidence_selector.addItems((
            "Unknown / no synthetic evidence", "Synthetic safe posture",
            "Synthetic ordinary lean", "Synthetic severe posture",
            "Synthetic confirmed recovery", "Synthetic caregiver candidate",
            "Synthetic caregiver departed",
        ))
        self.evidence_selector.currentIndexChanged.connect(self._select_evidence)
        controls.addWidget(self.evidence_selector)
        self.messaging_controls = MessagingControls(
            lambda: self.messaging, lambda: self.snapshot, lambda: self.position,
            self.receive_simulated_reply, self,
        )
        controls.addWidget(self.messaging_controls)
        controls.addStretch()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(0)
        self.scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        self.scroll.setWidget(details)
        self.wheel_guard = PanelWheelGuard(self.scroll)
        layout.addWidget(self.scroll, 1)
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()
        self.render()

    @property
    def snapshot(self):
        return self.engine.snapshot

    @property
    def caregiver_silent(self):
        return self._silence

    @property
    def position(self):
        if self.playing and self._anchor is not None:
            return self._position + max(0., self.clock() - self._anchor)
        return self._position

    def toggle_session(self):
        if self.enabled:
            self.end_session()
        else:
            self.enable_session()

    def enable_session(self):
        if self.enabled:
            return True
        if not self.enable_guard():
            self.status.setText("Test session blocked: finish/review active capture first.")
            return False
        self.messaging.close()
        self.engine = Engine()
        self.messaging = MessagingSession()
        self.messaging_controls.reset()
        self._contacted_911 = False
        self._position = 0.
        self._anchor = self.clock()
        self._last_observation = None
        self._synthetic = None
        self._mode_announcement = None
        self.evidence_selector.blockSignals(True)
        self.evidence_selector.setCurrentIndex(0)
        self.evidence_selector.blockSignals(False)
        self.enabled = self.playing = True
        self.enabled_changed.emit(True)
        self.render()
        return True

    def end_session(self):
        self.messaging.close()
        self.enabled = self.playing = False
        self.stop_audio()
        self.warning.hide()
        self._set_silence(False)
        self.enabled_changed.emit(False)
        self.render()

    def _set_silence(self, value):
        if value != self._silence:
            self._silence = value
            self.silence_changed.emit(value)

    def command(self, action):
        if not self.enabled:
            self.status.setText("TEST DISABLED • Enable Test Session before buttons or hotkeys.")
            return False
        if action == "contact_911":
            return self.contact_911()
        if action == "reply":
            return self.receive_simulated_reply(self.messaging.make_reply(self.position))
        previous_warning_key = self._warning_key
        self.engine.command(action, self.position)
        self._mode_announcement = action if action in {"start", "night"} else None
        self.render()
        if action in {"fall", "choking"} and previous_warning_key == self._warning_key and self._warning_key is not None:
            self.warning.bring_forward()
        return True

    def receive_simulated_reply(self, reply):
        if not self.enabled:
            return False
        now = self.position
        # Validate before the equal-time repeat deadline; Engine still owns time.
        self.messaging.sync(self.snapshot, now=now)
        if not self.messaging.receive_reply(reply, self.snapshot, now):
            return False
        self.engine.command("reply", now)
        self.render()
        return True

    def toggle_pause(self):
        if not self.enabled:
            return
        if self.playing:
            self.refresh()
            self._position = self.position
            self._anchor = None
            self.playing = False
        else:
            self._anchor = self.clock()
            self.playing = True
        self.render()

    def set_synthetic_evidence(self, **fields):
        """Explicit scenario facts only; repeated facts represent a test fixture."""
        if not self.enabled:
            return False
        Evidence(self.position, **fields)  # Validate before replacing current facts.
        self._synthetic = dict(fields)
        self.refresh()
        return True

    def _select_evidence(self, index):
        if not self.enabled:
            return
        fields = [
            {}, dict(posture="safe", subject_valid=True, safe_confirmed=True, calibrated=True),
            dict(posture="lean", subject_valid=True, calibrated=True),
            dict(posture="severe", subject_valid=True, calibrated=True),
            dict(posture="safe", subject_valid=True, safe_confirmed=True,
                 calibrated=True, recovery_confirmed=True),
            dict(posture="safe", subject_valid=True, caregiver_id="synthetic-caregiver",
                 caregiver_valid=True),
            dict(caregiver_departed=True),
        ][index]
        self.set_synthetic_evidence(**fields)

    def refresh(self):
        if self.enabled and self.playing:
            now = self.position
            if self._synthetic is not None and (self._last_observation is None or now > self._last_observation):
                self.engine.observe(Evidence(now, **self._synthetic))
                self._last_observation = now
                # Departure is an affirmative one-time synthetic event, not
                # manufactured new evidence on every later refresh.
                if self._synthetic.get("caregiver_departed"):
                    self._synthetic = None
            else:
                self.engine.tick(now)
        self.render()

    advance = refresh

    def toggle_audio(self):
        if not self.enabled:
            self.audio_status.setText("Enable Test Session first; audio remains OFF.")
            return
        if self.audio_enabled:
            self.stop_audio()
            return
        try:
            if self.audio is None:
                self.audio = self.audio_factory()
                if hasattr(self.audio, "status_changed"):
                    self.audio.status_changed.connect(self.audio_status.setText)
            self.audio_enabled = True
            self.audio_enabled_changed.emit(True)
            self.audio_status.setText(getattr(self.audio, "status", "Local test audio enabled."))
        except Exception:
            self.audio_status.setText("Local test audio unavailable; visual warning remains active.")
            self.audio_enabled = False
        self.render()

    def stop_audio(self):
        was_enabled = self.audio_enabled
        self.audio_enabled = False
        if was_enabled:
            self.audio_enabled_changed.emit(False)
        if self.audio is not None:
            self.audio.stop()
        self.audio_status.setText("Speech/sounds OFF. No microphone listener.")
        self.audio_button.setText("Enable Local Test Speech / Sounds")

    def contact_911(self):
        """Visual-only test intent: never dials, launches, sends or resolves."""
        snapshot = self.engine.snapshot
        if not self.enabled or not snapshot.choking or snapshot.incident != Incident.ALERT_ACTIVE:
            return False
        self._contacted_911 = True
        self.render()
        self.warning.bring_forward()
        return True

    def volume_changed(self):
        self.render()

    def render(self):
        snapshot = self.engine.snapshot
        if self.enabled:
            self.messaging.sync(snapshot, now=self.position)
            self.messaging.advance(self.position)
        self.messaging_controls.render(self.enabled)
        self.warning.set_messaging_status(
            self.messaging_controls.status.text() + "\n" + self.messaging_controls.preview.text())
        delivery = self.messaging.summary(snapshot.episode_id)
        messaging_unavailable = self.messaging.messaging_unavailable(snapshot.episode_id)
        messaging_note = (" Simulated caregiver messaging unavailable."
                          if delivery.error or delivery.last_status in {
                              "rejected", "failed", "undelivered", "unknown",
                          } else " Some simulated message attempts failed or remain unknown.")
        self._set_silence(self.enabled and snapshot.caregiver)
        self.enable_button.setText("End Test Session" if self.enabled else "Enable Test Session")
        self.pause_button.setText("Pause Test Clock" if self.playing else "Resume Test Clock")
        remaining = "none" if snapshot.remaining is None else f"{snapshot.remaining:.1f}s"
        silence_note = (" • CAREGIVER SILENT (synthetic)" if snapshot.caregiver else
                        " • CHOKING AUDIO SILENCED" if snapshot.choking_silent else "")
        self.status.setText(
            f"TEST {'RUNNING' if self.playing else 'PAUSED' if self.enabled else 'DISABLED'} • "
            f"{snapshot.mode.value} / {snapshot.incident.value}\n"
            f"Countdown: {remaining} • {'UNCERTAIN' if snapshot.uncertain else 'synthetic evidence'}{silence_note}"
        )
        self.reason.setText(
            f"{snapshot.reason}\nSimulated message intents: {snapshot.message_count}; no messages sent.\n"
            f"Caregiver silence retained: {snapshot.caregiver}; current synthetic evidence: {snapshot.caregiver_current}.\n"
            "Choking Windows unmute/maximum volume and restoration remain simulated."
        )
        active = snapshot.incident in {
            Incident.NORMAL_WARNING, Incident.SEVERE_WARNING, Incident.ALERT_ACTIVE,
        }
        if not snapshot.choking:
            self._contacted_911 = False
        self.warning.set_contact_911_status(self._contacted_911)
        if self.enabled and active and (self.playing or snapshot.choking) and (not snapshot.caregiver or snapshot.choking):
            self.warning.update_snapshot(snapshot)
            warning_key = (snapshot.incident, snapshot.choking)
            if self._warning_key != warning_key or not self.warning.isVisible():
                self.warning.present()
            self._warning_key = warning_key
        else:
            self.warning.hide()
            self._warning_key = None
        if not self.enabled or not self.playing or snapshot.caregiver or snapshot.choking_silent:
            self._mode_announcement = None
        if active:
            self._mode_announcement = None
        if not self.audio_enabled or self.audio is None:
            return
        self.audio_button.setText("Disable Local Test Speech / Sounds")
        if not self.enabled or not self.playing or snapshot.caregiver or snapshot.choking_silent:
            self._mode_announcement = None
            self.audio.stop()
            return
        if active:
            choking = snapshot.choking
            text = ("Emergency demonstration. No message sent. Use the large green button."
                    if choking else "Possible fall demonstration. No message sent. Use the large green button.")
            if messaging_unavailable:
                text += messaging_note
            key = (snapshot.incident.value, snapshot.audio_priority,
                   messaging_note if messaging_unavailable else "")
            self.audio.update(key, text, True, self.volume())
        elif self._mode_announcement is not None:
            action = self._mode_announcement
            text = "Automatic demonstration disabled." if action == "night" else "Automatic demonstration requested."
            self.audio.update(("mode", action), text, False, self.volume())
        else:
            self.audio.stop()

    def close_resources(self):
        self.timer.stop()
        self.end_session()
        self.warning.hide()
        self.warning.deleteLater()

    shutdown = close_resources
