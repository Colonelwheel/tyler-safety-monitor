"""User-configured global shortcuts; no microphone or general keyboard capture.

Only explicitly registered WM_HOTKEY messages are dispatched. VoiceAttack may
send the chosen shortcuts; warning audio remains a separate output adapter.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass
from datetime import datetime
import itertools
import json
from pathlib import Path
import sys
import re

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, QThread, Qt, Signal, Slot

from .settings import data_directory

ACTIONS = {
    "start": "Start Test Monitoring", "night": "Night — Test Mode",
    "fall": "Possible Fall — Test", "choking": "Choking — Test Only",
    "cancel": "Cancel / Resolve Test Alert",
    "contact_911": "Contact 911 — SIMULATION ONLY",
}
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
KEYS = {**{chr(key): key for key in range(65, 91)},
        **{str(key): ord(str(key)) for key in range(10)},
        **{f"F{key}": 0x6F + key for key in range(1, 25) if key != 12},
        "Space": 0x20, "Escape": 0x1B, "Tab": 0x09, "Enter": 0x0D,
        "Insert": 0x2D, "Delete": 0x2E, "Home": 0x24, "End": 0x23,
        "Page Up": 0x21, "Page Down": 0x22,
        "Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28}
_IDS = itertools.count(0x1000)
_SEQUENCE_FILE = re.compile(r"hotkeys-(\d{20})\.json\Z")
_LEGACY_FILE = re.compile(r"hotkeys-(\d{8}T\d{12}Z)-[0-9a-f]{32}\.json\Z")


@dataclass(frozen=True)
class HotkeyBinding:
    key: str
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    win: bool = False

    def __post_init__(self):
        if not isinstance(self.key, str) or self.key not in KEYS:
            raise ValueError("Choose a supported key; F12 and Print Screen are reserved")
        if any(type(flag) is not bool for flag in (self.ctrl, self.alt, self.shift, self.win)):
            raise ValueError("Shortcut modifiers must be true or false")
        if self.win:
            raise ValueError("Windows-key shortcuts are reserved for Windows")
        if (self.alt and self.key in {"Tab", "Escape", "F4"}
                or self.ctrl and self.key == "Escape"
                or self.ctrl and self.alt and self.key == "Delete"):
            raise ValueError("That shortcut is reserved for Windows")

    @property
    def modifiers(self):
        return ((MOD_CONTROL if self.ctrl else 0) | (MOD_ALT if self.alt else 0)
                | (MOD_SHIFT if self.shift else 0) | (MOD_WIN if self.win else 0))

    @property
    def label(self):
        return "+".join([name for name, enabled in
                         (("Ctrl", self.ctrl), ("Alt", self.alt), ("Shift", self.shift))
                         if enabled] + [self.key])


def _validate_bindings(bindings):
    if not isinstance(bindings, dict) or set(bindings) != set(ACTIONS):
        raise ValueError("Hotkeys must contain exactly the six test actions")
    assigned = []
    for binding in bindings.values():
        if binding is not None and not isinstance(binding, HotkeyBinding):
            raise ValueError("Invalid hotkey binding")
        if binding is not None:
            if binding in assigned:
                raise ValueError("Each action needs a different shortcut")
            assigned.append(binding)
    return dict(bindings)


def save_bindings(bindings, directory: Path | None = None) -> Path:
    """Explicitly create one new revision, preserving all earlier files."""
    bindings = _validate_bindings(bindings)
    directory = Path(directory) if directory is not None else data_directory() / "hotkeys"
    document = {"schema_version": 1, "bindings": {
        action: asdict(binding) if binding else None for action, binding in bindings.items()}}
    encoded = json.dumps(document, indent=2, allow_nan=False) + "\n"
    directory.mkdir(parents=True, exist_ok=True)
    # A timestamp plus random UUID cannot order rapid saves reliably on Windows.
    # Allocate an exclusive increasing filename instead; never trust wall time.
    for _ in range(64):
        sequence = 1 + max((int(match[1]) for existing in directory.glob("hotkeys-*.json")
                            if (match := _SEQUENCE_FILE.fullmatch(existing.name))), default=0)
        if sequence > 99999999999999999999:
            raise RuntimeError("Hotkey revision capacity reached")
        path = directory / f"hotkeys-{sequence:020d}.json"
        try:
            stream = path.open("x", encoding="utf-8")
        except FileExistsError:
            continue  # Another save won this ordinal; scan again without replacing it.
        with stream:
            stream.write(encoded)
        return path
    raise RuntimeError("Concurrent hotkey saves prevented a new revision; retry Save")


def load_bindings(directory: Path | None = None):
    """Read only the latest revision; a fault never silently loads an old one."""
    empty = dict.fromkeys(ACTIONS)
    try:
        directory = Path(directory) if directory is not None else data_directory() / "hotkeys"
        revisions = list(directory.glob("hotkeys-*.json"))
        if not revisions:
            return empty, "All hotkeys unassigned; choose and Apply when ready"
        numbered, legacy = [], []
        for revision in revisions:
            match = _SEQUENCE_FILE.fullmatch(revision.name)
            if match and int(match[1]) > 0:
                numbered.append((int(match[1]), revision))
                continue
            match = _LEGACY_FILE.fullmatch(revision.name)
            if not match:
                raise ValueError("unrecognized hotkey revision filename")
            stamp = datetime.strptime(match[1], "%Y%m%dT%H%M%S%fZ")
            legacy.append((stamp, revision))
        if numbered:
            # An explicit new-format save supersedes retained legacy revisions.
            path = max(numbered, key=lambda item: item[0])[1]
        else:
            latest_stamp = max(stamp for stamp, _ in legacy)
            latest = [revision for stamp, revision in legacy if stamp == latest_stamp]
            if len(latest) != 1:
                raise ValueError("legacy revisions share a timestamp; review and save a new revision")
            path = latest[0]
        if path.stat().st_size > 16 * 1024:
            raise ValueError("hotkey revision is too large")
        document = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(document, dict) or set(document) != {"schema_version", "bindings"}
                or type(document["schema_version"]) is not int or document["schema_version"] != 1):
            raise ValueError("unsupported hotkey revision schema")
        raw = document["bindings"]
        # Earlier five-action revisions remain unchanged. The newly introduced
        # 911 simulation command starts unassigned when reading those files.
        legacy_actions = set(ACTIONS) - {"contact_911"}
        if not isinstance(raw, dict) or set(raw) not in (set(ACTIONS), legacy_actions):
            raise ValueError("invalid saved hotkey actions")
        parsed = dict.fromkeys(ACTIONS)
        for action, value in raw.items():
            if value is not None and (not isinstance(value, dict)
                                      or set(value) != {"key", "ctrl", "alt", "shift", "win"}):
                raise ValueError("invalid saved hotkey fields")
            parsed[action] = HotkeyBinding(**value) if value is not None else None
        return _validate_bindings(parsed), "Saved hotkey revision loaded"
    except (OSError, ValueError, TypeError, RuntimeError, RecursionError) as error:
        return empty, f"Hotkey settings fault: {error}. No saved shortcuts activated."


class WindowsHotkeyBackend:
    """Register thread-specific shortcuts; never install a keyboard hook."""
    def __init__(self):
        self._user32 = None

    def _api(self):
        if sys.platform != "win32":
            raise OSError("Global hotkeys require Windows")
        if self._user32 is None:
            self._user32 = ctypes.WinDLL("user32", use_last_error=True)
            self._user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self._user32.RegisterHotKey.restype = wintypes.BOOL
            self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self._user32.UnregisterHotKey.restype = wintypes.BOOL
        return self._user32

    def register(self, identifier, modifiers, key):
        if not self._api().RegisterHotKey(None, identifier, modifiers, key):
            raise OSError(ctypes.get_last_error(), "Shortcut unavailable or already used by another application")

    def unregister(self, identifier):
        if not self._api().UnregisterHotKey(None, identifier):
            raise OSError(ctypes.get_last_error(), "Windows could not release this shortcut")


class HotkeyNativeFilter(QAbstractNativeEventFilter):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) not in {b"windows_generic_MSG", b"windows_dispatcher_MSG"}:
            return False, 0
        native = wintypes.MSG.from_address(int(message))
        if native.message != WM_HOTKEY or native.hWnd:
            return False, 0
        consumed = self.manager.dispatch_native(int(native.wParam), int(native.lParam))
        return consumed, 0


class GlobalHotkeys(QObject):
    activated = Signal(str)
    changed = Signal(str)
    _pending = Signal(int)

    def __init__(self, backend=None, parent=None):
        super().__init__(parent)
        self.backend = backend if backend is not None else WindowsHotkeyBackend()
        self.status = "All hotkeys unassigned"
        self._active = {}
        self._owned = set()
        self._closed = False
        self.native_filter = HotkeyNativeFilter(self)
        self._application = QCoreApplication.instance()
        if self._application is not None:
            self._application.installNativeEventFilter(self.native_filter)
            self._application.aboutToQuit.connect(self.close)
        self._pending.connect(self._deliver, Qt.ConnectionType.QueuedConnection)

    @property
    def bindings(self):
        return {action: self._active[action][1] if action in self._active else None for action in ACTIONS}

    def _report(self, message):
        self.status = message
        self.changed.emit(message)

    def _can_edit(self, action):
        if self._closed or action not in ACTIONS:
            self._report("Hotkeys closed or action invalid")
            return False
        if QThread.currentThread() != self.thread():
            self._report("Hotkey changes require the application's UI thread")
            return False
        return True

    def _release(self, identifier):
        self.backend.unregister(identifier)
        self._owned.discard(identifier)

    def apply(self, action, binding):
        if not self._can_edit(action):
            return False
        if not isinstance(binding, HotkeyBinding):
            self._report("Choose a supported shortcut before Apply")
            return False
        if any(other != action and current == binding for other, current in self.bindings.items()):
            self._report("Shortcut already assigned to another test action; previous binding retained")
            return False
        previous = self._active.get(action)
        if previous and previous[1] == binding:
            self._report(f"{ACTIONS[action]} remains {binding.label}")
            return True
        identifier = next(_IDS)
        if identifier > 0xBFFF:
            self._report("Hotkey identifier capacity reached; restart when convenient")
            return False
        try:
            self.backend.register(identifier, binding.modifiers | MOD_NOREPEAT, KEYS[binding.key])
            self._owned.add(identifier)
        except (OSError, RuntimeError) as error:
            self._report(f"Could not apply {binding.label}: {error}. Previous binding retained.")
            return False
        if previous:
            try:
                self._release(previous[0])
            except (OSError, RuntimeError) as error:
                # Keep the known old mapping if Windows cannot retire it.
                try:
                    self._release(identifier)
                except (OSError, RuntimeError):
                    pass  # Retain owned ID for shutdown retry; never dispatch it.
                self._report(f"Could not replace previous shortcut: {error}. Previous binding retained.")
                return False
        self._active[action] = (identifier, binding)
        self._report(f"{ACTIONS[action]}: {binding.label} applied — TEST ONLY")
        return True

    def remove(self, action):
        if not self._can_edit(action):
            return False
        previous = self._active.get(action)
        if previous:
            try:
                self._release(previous[0])
            except (OSError, RuntimeError) as error:
                self._report(f"Could not remove shortcut: {error}. Previous binding retained.")
                return False
            del self._active[action]
        self._report(f"{ACTIONS[action]}: unassigned (save to retain after restart)")
        return True

    def dispatch_native(self, identifier, key_details=None):
        """Queue an owned active shortcut; key_details validates the WM_HOTKEY payload."""
        if self._closed:
            return False
        for owned_id, binding in self._active.values():
            if identifier == owned_id:
                expected = (KEYS[binding.key] << 16) | binding.modifiers
                if key_details is not None and key_details != expected:
                    return False
                self._pending.emit(identifier)
                return True
        return False

    @Slot(int)
    def _deliver(self, identifier):
        if not self._closed:
            for action, (current_id, _) in self._active.items():
                if current_id == identifier:
                    self.activated.emit(action)
                    return

    @Slot()
    def close(self):
        self._closed = True
        self._active.clear()
        if self._application is not None:
            self._application.removeNativeEventFilter(self.native_filter)
        failures = []
        for identifier in tuple(self._owned):
            try:
                self._release(identifier)
            except (OSError, RuntimeError) as error:
                failures.append(str(error))
        if failures:
            self._report("Hotkey release fault: " + "; ".join(failures))
