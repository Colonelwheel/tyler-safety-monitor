"""Development foreground startup without camera, audio or native UI."""
import sys
from types import SimpleNamespace
import pytest
from tyler_safety_monitor import __main__ as entry

@pytest.mark.parametrize('arguments,tray,shown', [
    ([], True, True), (['--show'], True, True),
    (['--start-minimized'], True, False),
    (['--start-minimized'], False, True),
])
def test_development_default_opens_foreground_and_explicit_tray_option_remains(arguments,tray,shown,monkeypatch):
    from PySide6 import QtWidgets
    from tyler_safety_monitor import dashboard
    windows = []
    class Application:
        def __init__(self, args):
            self.aboutToQuit = SimpleNamespace(connect=lambda callback: None)
        def setApplicationName(self, name): pass
        def setQuitOnLastWindowClosed(self, value): pass
        def exec(self): return 0
    class Window:
        def __init__(self, model, enable_camera):
            assert not enable_camera
            self.tray_available = tray
            self.opened = False
            windows.append(self)
        def open_dashboard(self): self.opened = True
        def shutdown(self): pass
    monkeypatch.setattr(sys, 'argv', ['monitor', '--no-camera', '--model', 'unused.task', *arguments])
    monkeypatch.setattr(QtWidgets, 'QApplication', Application)
    monkeypatch.setattr(dashboard, 'Dashboard', Window)
    assert entry.main() == 0
    assert windows[0].opened is shown
