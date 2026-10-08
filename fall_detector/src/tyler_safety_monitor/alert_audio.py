"""Opt-in app-local test speech and tones; no microphone or Windows switching."""
from __future__ import annotations

import math
import os

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtTextToSpeech import QTextToSpeech

from .audio import TestSound


class AlertAudio(QObject):
    """Latest-state output only: replacing/stopping never queues old utterances."""

    status_changed = Signal(str)

    def __init__(self, parent=None, speech_factory=None, tone_factory=TestSound):
        super().__init__(parent)
        self.status = "Local test audio not initialized."
        self._speech = None
        self._tone = tone_factory()
        self._key = None
        self._pending_tone = False
        self._volume = .5
        self._timer = QTimer(self)
        self._timer.setInterval(3000)
        self._timer.timeout.connect(self._play_tone)
        try:
            if speech_factory is not None:
                self._speech = speech_factory()
            elif os.name == "nt" and "sapi" in QTextToSpeech.availableEngines():
                # The installed Windows SAPI engine uses local voices. Do not
                # fall back to engines that could acquire online voices.
                self._speech = QTextToSpeech("sapi", self)
            if self._speech is not None:
                self._speech.stateChanged.connect(self._speech_state)
                if self._speech.state() == QTextToSpeech.State.Error:
                    self._status("Speech unavailable; visual warning remains active.")
                else:
                    self._status("Local speech ready; tone availability checked on playback.")
            else:
                self._status("Installed local Windows speech unavailable; tones/visuals remain.")
        except Exception:
            self._speech = None
            self._status("Local speech initialization failed; tones/visuals remain.")

    def _status(self, value):
        self.status = value
        self.status_changed.emit(value)

    def _speech_state(self, state):
        if state == QTextToSpeech.State.Ready and self._pending_tone and self._key is not None:
            self._pending_tone = False
            self._play_tone()
        if state == QTextToSpeech.State.Error:
            self._status("Local speech failed; visual warning remains active.")

    def _stop_outputs(self):
        self._pending_tone = False
        self._timer.stop()
        if self._speech is not None:
            try:
                self._speech.stop(QTextToSpeech.BoundaryHint.Immediate)
            except Exception:
                self._status("Speech stop failed; use End Test Session.")
        try:
            self._tone.stop()
        except Exception:
            self._status("Tone stop failed; use End Test Session.")

    def stop(self):
        self._key = None
        self._stop_outputs()

    def update(self, key, text, repeating, volume):
        if not math.isfinite(volume) or not 0 <= volume <= 1:
            raise ValueError("selected volume must be between zero and one")
        self._volume = float(volume)
        if volume == 0:
            self.stop()
            return
        if key == self._key:
            try:
                if self._speech is not None:
                    self._speech.setVolume(volume)
                if getattr(self._tone, "sink", None) is not None:
                    self._tone.sink.setVolume(volume)
            except Exception:
                self._status("Local volume update failed; visual warning remains active.")
            return
        self._stop_outputs()
        self._key = key
        if self._speech is not None:
            try:
                if self._speech.state() == QTextToSpeech.State.Ready:
                    self._speech.setVolume(volume)
                    self._speech.say(text)
                else:
                    self._status("Speech not ready; visual warning remains active.")
            except Exception:
                self._status("Speech playback failed; visual warning remains active.")
        usable = self._play_tone()
        if repeating and usable:
            self._timer.start()

    def _play_tone(self):
        if self._key is None:
            return False
        try:
            if self._speech is not None and self._speech.state() in {QTextToSpeech.State.Speaking, QTextToSpeech.State.Synthesizing}:
                self._pending_tone = True
                return True
            self._tone.play(self._volume)
            sink = getattr(self._tone, "sink", None)
            if sink is not None:
                sink.stateChanged.connect(lambda state: self._tone_state(sink))
                if self._tone_state(sink):
                    return False
            return True
        except Exception:
            self._timer.stop()
            self._status("Local tone unavailable; visual warning remains active.")
            return False

    def _tone_state(self, sink):
        if sink is getattr(self._tone, "sink", None) and sink.error().value != 0:
            self._timer.stop()
            self._status("Local tone playback failed; visual warning remains active.")
            return True
        return False
