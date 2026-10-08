"""Fake speech/tone checks: no native engine/output creation or audible playback."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtTextToSpeech import QTextToSpeech
from PySide6.QtWidgets import QApplication

from tyler_safety_monitor.alert_audio import AlertAudio


class FakeSpeech(QObject):
    stateChanged = Signal(object)

    def __init__(self):
        super().__init__()
        self.current = QTextToSpeech.State.Ready
        self.words = []
        self.stops = []
        self.volume = None

    def state(self):
        return self.current

    def setVolume(self, volume):
        self.volume = volume

    def say(self, text):
        self.words.append(text)
        self.current = QTextToSpeech.State.Speaking
        self.stateChanged.emit(self.current)

    def stop(self, boundary):
        self.stops.append(boundary)
        self.current = QTextToSpeech.State.Ready
        self.stateChanged.emit(self.current)

    def complete(self):
        self.current = QTextToSpeech.State.Ready
        self.stateChanged.emit(self.current)


class FakeTone:
    def __init__(self):
        self.volumes = []
        self.stops = 0

    def play(self, volume):
        self.volumes.append(volume)

    def stop(self):
        self.stops += 1


@pytest.fixture
def audio():
    app = QApplication.instance() or QApplication([])
    speech = FakeSpeech()
    tone = FakeTone()
    output = AlertAudio(speech_factory=lambda: speech, tone_factory=lambda: tone)
    yield output, speech, tone
    output.stop()
    output.deleteLater()
    app.processEvents()


def test_tone_waits_for_speech_without_refresh_duplication(audio):
    output, speech, tone = audio
    output.update("fall", "Demonstration", True, .4)
    for _ in range(5):
        output.update("fall", "Demonstration", True, .4)
    assert speech.words == ["Demonstration"]
    assert tone.volumes == []
    speech.complete()
    assert tone.volumes == [.4]
    output._play_tone()
    assert tone.volumes == [.4, .4]
    assert output._timer.isActive()


def test_immediate_stop_clears_speech_and_pending_tone(audio):
    output, speech, tone = audio
    output.update("fall", "Demonstration", True, .5)
    output.stop()
    speech.complete()  # Delayed readiness cannot play the cancelled pending tone.
    output._play_tone()
    assert tone.volumes == []
    assert not output._timer.isActive()
    assert speech.stops[-1] == QTextToSpeech.BoundaryHint.Immediate


def test_transition_stops_old_output_and_never_speaks_obsolete_history(audio):
    output, speech, tone = audio
    output.update("warning", "First", True, .5)
    output.update("alert", "Latest", True, .5)
    assert speech.words == ["First", "Latest"]
    speech.complete()
    assert tone.volumes == [.5]
    assert len(speech.stops) == 2


def test_volume_zero_stops_without_speech_or_tone_then_new_output_uses_selection(audio):
    output, speech, tone = audio
    output.update("warning", "Quiet", True, 0)
    assert speech.words == [] and tone.volumes == []
    output.update("warning", "Audible", True, .2)
    assert speech.volume == .2
    output.update("warning", "Audible", True, .7)
    assert speech.words == ["Audible"]
    assert speech.volume == .7
    speech.complete()
    assert tone.volumes == [.7]


def test_audio_errors_visible_and_do_not_prevent_visual_controller(audio):
    output, speech, tone = audio
    errors = []
    output.status_changed.connect(errors.append)
    def fail(_volume):
        raise RuntimeError("synthetic device fault")
    tone.play = fail
    output.update("warning", "Demonstration", True, .5)
    speech.complete()
    assert "unavailable" in output.status
    assert errors
    assert not output._timer.isActive()
    output.stop()


def test_unready_or_failed_speech_does_not_queue(audio):
    output, speech, tone = audio
    speech.current = QTextToSpeech.State.Error
    speech.stop = lambda boundary: speech.stops.append(boundary)
    output.update("warning", "Demonstration", True, .5)
    assert not speech.words
    assert tone.volumes == [.5]
    assert "not ready" in output.status


def test_async_speech_error_reports_without_blocking_tone_or_stop(audio):
    output, speech, tone = audio
    output.update("warning", "Demonstration", True, .5)
    speech.current = QTextToSpeech.State.Error
    speech.stateChanged.emit(speech.current)
    assert "failed" in output.status
    output._play_tone()
    assert tone.volumes == [.5]
    output.stop()
    output._play_tone()
    assert tone.volumes == [.5]


def test_volume_update_exception_stays_visible_without_escaping(audio):
    output, speech, tone = audio
    output.update("warning", "Demonstration", True, .5)
    def fail(_volume):
        raise RuntimeError("synthetic volume fault")
    speech.setVolume = fail
    output.update("warning", "Demonstration", True, .7)
    assert "volume update failed" in output.status
    assert speech.words == ["Demonstration"]


def test_initial_tone_failure_does_not_start_repeat_loop(audio):
    output, speech, tone = audio
    speech.current = QTextToSpeech.State.Error
    speech.stop = lambda boundary: None
    def fail(_volume):
        raise RuntimeError("synthetic unavailable output")
    tone.play = fail
    output.update("warning", "Demonstration", True, .5)
    assert "unavailable" in output.status
    assert not output._timer.isActive()
