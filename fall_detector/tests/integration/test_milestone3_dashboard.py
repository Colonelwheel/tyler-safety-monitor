"""Milestone 3 integration preserves capture, settings and diagnostic isolation."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from pathlib import Path
from types import SimpleNamespace
import pytest
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from tyler_safety_monitor import dashboard as ui
from tyler_safety_monitor import hotkeys
from tyler_safety_monitor.settings import AppSettings


class FakeHotkeys(QObject):
    activated = Signal(str)
    changed = Signal(str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bindings = {action: None for action in hotkeys.ACTIONS}
        self.status = 'All test hotkeys unassigned'
        self.closed = False
    def close(self):
        self.closed = True


class FakeSound:
    def __init__(self):
        self.sink = None
        self.played = []
        self.stopped = 0
    def play(self, volume):
        self.played.append(volume)
    def stop(self):
        self.stopped += 1


class FakeTray:
    ActivationReason = QSystemTrayIcon.ActivationReason
    @staticmethod
    def isSystemTrayAvailable(): return False
    def __init__(self, *args):
        self.activated = SimpleNamespace(connect=lambda callback: None)
    def setToolTip(self, *args): pass
    def setContextMenu(self, *args): pass
    def hide(self): pass


@pytest.fixture
def window(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ui, 'TestSound', FakeSound)
    monkeypatch.setattr(ui, 'QSystemTrayIcon', FakeTray)
    monkeypatch.setattr(ui, 'load_settings', lambda: (AppSettings(), 'synthetic defaults'))
    monkeypatch.setattr(ui, 'CameraCapture', lambda *args: pytest.fail('No hardware'))
    monkeypatch.setattr(hotkeys, 'GlobalHotkeys', FakeHotkeys)
    from tyler_safety_monitor import hotkey_ui
    monkeypatch.setattr(hotkey_ui, 'load_bindings', lambda *args, **kwargs: ({action: None for action in hotkeys.ACTIONS}, 'No saved mappings'))
    view = ui.Dashboard(Path('unused.task'), enable_camera=False)
    view.timer.stop()
    view.simulation.timer.stop()
    view.warning_test.timer.stop()
    yield view
    view.shutdown()
    assert view.hotkeys.closed
    view.deleteLater()
    app.processEvents()


def test_hotkeys_require_test_enable_and_do_not_touch_camera_settings_or_quiet_replay(window):
    settings = window.settings
    replay = window.simulation.runner
    window.hotkeys.activated.emit('choking')
    assert not window.warning_test.enabled
    assert window.warning_test.snapshot.message_count == 0
    window.warning_test.enable_session()
    window.hotkeys.activated.emit('choking')
    assert window.warning_test.snapshot.message_count == 1
    window.hotkeys.activated.emit('cancel')
    assert window.warning_test.snapshot.incident.value == 'RESOLVED'
    assert window.settings is settings and window.simulation.runner is replay
    assert window.capture is None and window.pose is None
    assert window.sound.played == [] and window.tools.samples == []


def test_warning_test_refuses_active_capture_and_preserves_existing_samples(window):
    sentinel = object()
    window.tools.samples.append(sentinel)
    window.tools.state = 'capturing'
    window.warning_test.enable_session()
    assert not window.warning_test.enabled
    assert window.tools.state == 'capturing' and window.tools.samples == [sentinel]
    assert 'Stop / Review' in window.settings_status.text()
    window.tools.state = 'review'


def test_capture_refuses_enabled_warning_test_before_consent(window, monkeypatch):
    sentinel = object()
    window.tools.samples.append(sentinel)
    window.warning_test.enable_session()
    monkeypatch.setattr(window.tools, 'confirm', lambda *args: pytest.fail('Capture consent forbidden'))
    window.tools.request_capture()
    assert window.tools.samples == [sentinel] and window.tools.state == 'idle'
    assert 'End the warning test' in window.tools.status.text()


def test_live_candidate_counter_never_silences_test_sound_or_enables_test(window):
    from tyler_safety_monitor.caregiver_status import CaregiverStatus
    window.caregiver_counter._snapshot = CaregiverStatus('confirmed', 2., 7, 'synthetic diagnostic', 0)
    window.render_caregiver_status()
    window.test_sound()
    assert window.sound.played == [.5]
    assert not window.warning_test.enabled


def test_manual_test_sound_is_blocked_only_by_enabled_test_caregiver_latch(window, monkeypatch):
    window.warning_test.enable_session()
    monkeypatch.setattr(type(window.warning_test), 'caregiver_silent', property(lambda _: True))
    window.warning_test_silence(True)
    window.test_sound()
    assert window.sound.played == [] and window.sound.stopped >= 2
    assert 'Simulated caregiver silence' in window.settings_status.text()
    monkeypatch.setattr(type(window.warning_test), 'caregiver_silent', property(lambda _: False))
    window.warning_test_silence(False)
    assert window.sound.played == []
    window.test_sound()
    assert window.sound.played == [.5]


def test_global_audio_stop_stops_manual_and_alert_audio_without_cancelling_incident(window):
    window.warning_test.enable_session()
    window.warning_test.command('fall')
    before = window.warning_test.snapshot
    window.stop_all_sounds()
    assert window.sound.stopped >= 1
    assert window.warning_test.snapshot.incident == before.incident


def test_enabling_warning_audio_stops_manual_test_sound_and_keeps_capture_data(window):
    class Audio:
        status = 'Fake ready'
        def stop(self): pass
        def update(self, *args): pass
    window.warning_test.audio_factory = Audio
    window.test_sound()
    assert window.sound.played == [.5]
    before = window.sound.stopped
    window.warning_test.enable_session()
    window.warning_test.toggle_audio()
    assert window.sound.stopped == before + 1
    assert window.warning_test.audio_enabled and window.tools.samples == []

def test_manual_test_tone_stops_warning_audio_and_keeps_choking_unresolved(window):
    class Audio:
        status = 'Fake ready'
        def __init__(self): self.stops = 0
        def stop(self): self.stops += 1
        def update(self, *args): pass
    window.warning_test.audio_factory = Audio
    window.warning_test.enable_session()
    window.warning_test.toggle_audio()
    window.warning_test.command('choking')
    before = window.warning_test.snapshot
    stops = window.warning_test.audio.stops
    window.test_sound()
    assert window.sound.played == [.5]
    assert not window.warning_test.audio_enabled
    assert window.warning_test.audio.stops > stops
    assert window.warning_test.snapshot == before
    assert window.warning_test.warning.isVisible()
