"""Synthetic global shortcut lifecycle; no Windows registrations or key injection."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QApplication

from tyler_safety_monitor.hotkeys import (ACTIONS, KEYS, MOD_NOREPEAT, WM_HOTKEY,
    GlobalHotkeys, HotkeyBinding, load_bindings, save_bindings)


class FakeBackend:
    def __init__(self):
        self.registered = {}
        self.calls = []
        self.fail_register = False
        self.fail_release = set()

    def register(self, identifier, modifiers, key):
        self.calls.append(("register", identifier, modifiers, key))
        if self.fail_register:
            raise OSError("shortcut used elsewhere")
        self.registered[identifier] = (modifiers, key)

    def unregister(self, identifier):
        self.calls.append(("unregister", identifier))
        if identifier in self.fail_release:
            raise OSError("release failed")
        del self.registered[identifier]


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.fixture
def manager(application):
    backend = FakeBackend()
    manager = GlobalHotkeys(backend)
    yield manager, backend
    backend.fail_release.clear()
    manager.close()
    application.processEvents()
    manager.deleteLater()


def test_defaults_have_no_shortcut_and_do_not_call_os(manager):
    hotkeys, backend = manager
    assert hotkeys.bindings == dict.fromkeys(ACTIONS)
    assert backend.calls == []


@pytest.mark.parametrize("binding", [dict(key="F12"), dict(key="Print Screen"),
    dict(key="A", win=True), dict(key="Tab", alt=True), dict(key="F4", alt=True),
    dict(key="Delete", ctrl=True, alt=True), dict(key="Escape", ctrl=True, shift=True),
    dict(key="A", ctrl=1), dict(key=None)])
def test_reserved_and_invalid_bindings(binding):
    with pytest.raises(ValueError):
        HotkeyBinding(**binding)


def test_replacement_failure_preserves_existing_and_success_retires_old(manager, application):
    hotkeys, backend = manager
    seen = []
    hotkeys.activated.connect(seen.append)
    first = HotkeyBinding("F13")
    second = HotkeyBinding("B", ctrl=True, shift=True)
    assert hotkeys.apply("fall", first)
    first_id = next(iter(backend.registered))
    assert backend.registered[first_id][0] == MOD_NOREPEAT
    backend.fail_register = True
    assert not hotkeys.apply("fall", second)
    assert hotkeys.bindings["fall"] == first
    assert hotkeys.dispatch_native(first_id)
    application.processEvents()
    assert seen == ["fall"]
    backend.fail_register = False
    assert hotkeys.dispatch_native(first_id)  # Queued before replacement must expire.
    assert hotkeys.apply("fall", second)
    assert first_id not in backend.registered
    assert not hotkeys.dispatch_native(first_id)
    application.processEvents()
    assert seen == ["fall"]
    new_id = next(iter(backend.registered))
    assert hotkeys.dispatch_native(new_id, (KEYS["B"] << 16) | second.modifiers)
    application.processEvents()
    assert seen == ["fall", "fall"]


def test_duplicate_action_binding_and_idempotent_apply(manager):
    hotkeys, backend = manager
    binding = HotkeyBinding("F14")
    assert hotkeys.apply("cancel", binding)
    calls = list(backend.calls)
    assert hotkeys.apply("cancel", binding)
    assert backend.calls == calls
    assert not hotkeys.apply("choking", binding)
    assert hotkeys.bindings["choking"] is None
    assert backend.calls == calls


def test_unregister_failure_rolls_back_and_owned_leak_ignored(manager, application):
    hotkeys, backend = manager
    assert hotkeys.apply("cancel", HotkeyBinding("F15"))
    identifier = next(iter(backend.registered))
    backend.fail_release.add(identifier)
    assert not hotkeys.remove("cancel")
    assert hotkeys.bindings["cancel"] == HotkeyBinding("F15")
    assert not hotkeys.apply("cancel", HotkeyBinding("F16"))
    assert len(backend.registered) == 1
    assert hotkeys.bindings["cancel"] == HotkeyBinding("F15")
    assert hotkeys.dispatch_native(identifier)
    # Simulate rollback-release failure: held ID remains owned, but ignored.
    original_release = backend.unregister
    def always_fail(current):
        raise OSError("release failed")
    backend.unregister = always_fail
    assert not hotkeys.apply("cancel", HotkeyBinding("F17"))
    leaked = set(backend.registered) - {identifier}
    assert len(leaked) == 1
    assert not hotkeys.dispatch_native(next(iter(leaked)))
    backend.unregister = original_release
    backend.fail_release.clear()
    hotkeys.close()
    assert not backend.registered


def test_close_ignores_queued_delivery_and_retries_only_owned_release(manager, application):
    hotkeys, backend = manager
    seen = []
    hotkeys.activated.connect(seen.append)
    assert hotkeys.apply("choking", HotkeyBinding("C", alt=True))
    identifier = next(iter(backend.registered))
    backend.registered[999] = (0, 0)  # Unrelated simulated component's registration.
    hotkeys.dispatch_native(identifier)
    backend.fail_release.add(identifier)
    hotkeys.close()
    application.processEvents()
    assert not seen
    assert "release fault" in hotkeys.status
    backend.fail_release.clear()
    hotkeys.close()
    assert set(backend.registered) == {999}
    assert not hotkeys.dispatch_native(identifier)
    assert not hotkeys.apply("cancel", HotkeyBinding("F18"))


def test_only_owned_wm_hotkey_with_matching_payload_is_consumed(manager, application):
    hotkeys, backend = manager
    seen = []
    hotkeys.activated.connect(seen.append)
    binding = HotkeyBinding("F19", ctrl=True)
    hotkeys.apply("start", binding)
    identifier = next(iter(backend.registered))
    message = wintypes.MSG()
    message.message = WM_HOTKEY
    message.wParam = identifier
    message.lParam = (KEYS[binding.key] << 16) | binding.modifiers
    pointer = ctypes.addressof(message)
    event_filter = hotkeys.native_filter
    assert event_filter.nativeEventFilter(QByteArray(b"not_windows"), pointer) == (False, 0)
    message.message = 0x0100  # General WM_KEYDOWN is not captured.
    assert event_filter.nativeEventFilter(QByteArray(b"windows_generic_MSG"), pointer) == (False, 0)
    message.message = WM_HOTKEY
    message.wParam = identifier + 1000
    assert event_filter.nativeEventFilter(QByteArray(b"windows_dispatcher_MSG"), pointer) == (False, 0)
    message.wParam = identifier
    message.lParam += 1
    assert event_filter.nativeEventFilter(QByteArray(b"windows_dispatcher_MSG"), pointer) == (False, 0)
    message.lParam -= 1
    message.hWnd = 1234
    assert event_filter.nativeEventFilter(QByteArray(b"windows_generic_MSG"), pointer) == (False, 0)
    message.hWnd = None
    assert event_filter.nativeEventFilter(QByteArray(b"windows_dispatcher_MSG"), pointer) == (True, 0)
    assert not seen
    application.processEvents()
    assert seen == ["start"]


def test_dispatch_is_queued_to_gui_thread_and_changes_on_worker_rejected(manager, application):
    hotkeys, backend = manager
    received = []
    hotkeys.activated.connect(lambda action: received.append((action, threading.get_ident())))
    hotkeys.apply("night", HotkeyBinding("F20"))
    identifier = next(iter(backend.registered))
    outcome = []
    def worker():
        outcome.append(hotkeys.apply("cancel", HotkeyBinding("F21")))
        hotkeys.dispatch_native(identifier)
    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert outcome == [False]
    assert not received
    application.processEvents()
    assert received == [("night", threading.get_ident())]


def test_save_and_load_revisions_preserve_existing_settings_and_old_revisions(tmp_path):
    directory = tmp_path / "hotkeys"
    unrelated = tmp_path / "config" / "settings.json"
    unrelated.parent.mkdir()
    unrelated.write_text("preserve")
    bindings = dict.fromkeys(ACTIONS)
    bindings["cancel"] = HotkeyBinding("F22")
    first = save_bindings(bindings, directory)
    original = first.read_bytes()
    bindings["choking"] = HotkeyBinding("F23", shift=True)
    second = save_bindings(bindings, directory)
    assert first != second
    assert first.read_bytes() == original
    assert unrelated.read_text() == "preserve"
    loaded, status = load_bindings(directory)
    assert loaded == bindings
    assert "loaded" in status
    assert len(list(directory.iterdir())) == 2


@pytest.mark.parametrize("payload", ["{broken", "[]", "null",
    json.dumps({"schema_version": True, "bindings": dict.fromkeys(ACTIONS)}),
    json.dumps({"schema_version": 1, "bindings": {}}),
    json.dumps({"schema_version": 1, "bindings": dict.fromkeys(ACTIONS), "extra": 1}),
    "x" * (16 * 1024 + 1)], ids=["broken", "array", "null", "bool-schema", "missing-actions", "extra-field", "oversize"])
def test_latest_corruption_stays_visible_no_old_fallback(tmp_path, payload):
    bindings = dict.fromkeys(ACTIONS)
    bindings["fall"] = HotkeyBinding("F24")
    first = save_bindings(bindings, tmp_path)
    before = first.read_bytes()
    fault = tmp_path / "hotkeys-00000000000000000002.json"
    fault.write_text(payload)
    loaded, status = load_bindings(tmp_path)
    assert loaded == dict.fromkeys(ACTIONS)
    assert "fault" in status.lower()
    assert first.read_bytes() == before
    assert fault.read_text() == payload


def test_no_saved_revision_is_read_only_and_unassigned(tmp_path):
    directory = tmp_path / "not-created"
    assert load_bindings(directory)[0] == dict.fromkeys(ACTIONS)
    assert not directory.exists()


def test_saved_duplicate_binding_or_unknown_fields_rejected(tmp_path):
    binding = {"key": "F13", "ctrl": False, "alt": False, "shift": False, "win": False}
    data = {"schema_version": 1, "bindings": dict.fromkeys(ACTIONS)}
    data["bindings"]["fall"] = binding
    data["bindings"]["choking"] = binding
    path = tmp_path / "hotkeys-00000000000000000001.json"
    path.write_text(json.dumps(data))
    assert "fault" in load_bindings(tmp_path)[1].lower()
    data["bindings"]["choking"] = None
    binding["unexpected"] = 1
    path.write_text(json.dumps(data))
    assert "fault" in load_bindings(tmp_path)[1].lower()


def test_exclusive_save_collision_retries_without_overwrite(tmp_path, monkeypatch):
    original_open = Path.open
    collided = []
    def race(path, mode="r", *args, **kwargs):
        if mode == "x" and not collided:
            with original_open(path, "x", encoding="utf-8") as stream:
                stream.write("preserve concurrent revision")
            collided.append(path)
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", race)
    result = save_bindings(dict.fromkeys(ACTIONS), tmp_path)
    assert result.name == "hotkeys-00000000000000000002.json"
    assert collided[0].read_text() == "preserve concurrent revision"
    assert load_bindings(tmp_path)[0] == dict.fromkeys(ACTIONS)


@pytest.mark.parametrize("stamps", [("20261008T120000000000Z", "20261008T120000000000Z"),
                                  ("20261008T120000000000Z", "20261007T120000000000Z")],
                         ids=["identical-clock", "regressed-clock"])
def test_revision_order_does_not_depend_on_wall_clock(tmp_path, monkeypatch, stamps):
    from tyler_safety_monitor import hotkeys
    class FakeDateTime:
        @classmethod
        def now(cls, *args):
            class Stamp:
                def strftime(self, format):
                    return current_stamp[0]
            return Stamp()
    current_stamp = [stamps[0]]
    monkeypatch.setattr(hotkeys, "datetime", FakeDateTime)
    first_bindings = dict.fromkeys(ACTIONS)
    first_bindings["cancel"] = HotkeyBinding("F13")
    first = save_bindings(first_bindings, tmp_path)
    preserved = first.read_bytes()
    current_stamp[0] = stamps[1]
    second_bindings = dict(first_bindings)
    second_bindings["choking"] = HotkeyBinding("F14")
    second = save_bindings(second_bindings, tmp_path)
    # Filesystem timestamps can be coarse or go backwards too.
    os.utime(first, ns=(1_000_000_000, 1_000_000_000))
    os.utime(second, ns=(1_000_000_000, 1_000_000_000))
    assert first.read_bytes() == preserved
    assert first.name == "hotkeys-00000000000000000001.json"
    assert second.name == "hotkeys-00000000000000000002.json"
    assert load_bindings(tmp_path)[0] == second_bindings


def test_existing_highest_ordinal_respected_and_other_files_preserved(tmp_path):
    older = tmp_path / "hotkeys-00000000000000000009.json"
    older.write_text("retained invalid old revision")
    unrelated = tmp_path / "notes.txt"
    unrelated.write_text("keep")
    bindings = dict.fromkeys(ACTIONS)
    bindings["fall"] = HotkeyBinding("F15")
    saved = save_bindings(bindings, tmp_path)
    assert saved.name == "hotkeys-00000000000000000010.json"
    assert load_bindings(tmp_path)[0] == bindings
    assert older.read_text() == "retained invalid old revision"
    assert unrelated.read_text() == "keep"


def test_legacy_revision_read_only_and_new_numbered_revision_supersedes(tmp_path):
    from dataclasses import asdict
    bindings = dict.fromkeys(ACTIONS)
    bindings["start"] = HotkeyBinding("F16")
    legacy = tmp_path / ("hotkeys-20261008T120000000000Z-" + "a" * 32 + ".json")
    payload = {"schema_version": 1, "bindings": {
        action: asdict(binding) if binding else None for action, binding in bindings.items()}}
    legacy.write_text(json.dumps(payload))
    preserved = legacy.read_bytes()
    assert load_bindings(tmp_path)[0] == bindings
    bindings["night"] = HotkeyBinding("F17")
    saved = save_bindings(bindings, tmp_path)
    assert saved.name == "hotkeys-00000000000000000001.json"
    assert load_bindings(tmp_path)[0] == bindings
    assert legacy.read_bytes() == preserved


def test_legacy_timestamp_tie_is_visible_without_random_choice(tmp_path):
    payload = {"schema_version": 1, "bindings": dict.fromkeys(ACTIONS)}
    for suffix in ("a" * 32, "b" * 32):
        path = tmp_path / f"hotkeys-20261008T120000000000Z-{suffix}.json"
        path.write_text(json.dumps(payload))
    loaded, status = load_bindings(tmp_path)
    assert loaded == dict.fromkeys(ACTIONS)
    assert "share a timestamp" in status
    assert len(list(tmp_path.iterdir())) == 2


def test_bounded_collision_retry_preserves_all_existing_revisions(tmp_path, monkeypatch):
    original_open = Path.open
    collisions = []
    def race(path, mode="r", *args, **kwargs):
        if mode == "x":
            with original_open(path, "x", encoding="utf-8") as stream:
                stream.write("preserve")
            collisions.append(path)
        return original_open(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", race)
    with pytest.raises(RuntimeError, match="Concurrent"):
        save_bindings(dict.fromkeys(ACTIONS), tmp_path)
    assert len(collisions) == 64
    assert all(path.read_text() == "preserve" for path in collisions)


def test_contact_911_saved_revision_roundtrip_and_duplicate_conflict(manager, tmp_path, application):
    hotkeys, backend = manager
    assert hotkeys.bindings["contact_911"] is None
    binding = HotkeyBinding("F24", ctrl=True)
    assert hotkeys.apply("contact_911", binding)
    assert not hotkeys.apply("choking", binding)
    dispatched = []
    hotkeys.activated.connect(dispatched.append)
    identifier = next(iter(backend.registered))
    assert hotkeys.dispatch_native(identifier, (KEYS[binding.key] << 16) | binding.modifiers)
    application.processEvents()
    assert dispatched == ["contact_911"]
    save_bindings(hotkeys.bindings, tmp_path)
    assert load_bindings(tmp_path)[0] == hotkeys.bindings


def test_previous_five_action_revision_loads_contact_911_unassigned_without_rewrite(tmp_path):
    from dataclasses import asdict
    bindings = dict.fromkeys(set(ACTIONS) - {"contact_911"})
    bindings["cancel"] = asdict(HotkeyBinding("F23"))
    payload = {"schema_version": 1, "bindings": bindings}
    revision = tmp_path / "hotkeys-00000000000000000001.json"
    revision.write_text(json.dumps(payload))
    original = revision.read_bytes()
    loaded, status = load_bindings(tmp_path)
    assert "loaded" in status
    assert loaded["cancel"] == HotkeyBinding("F23")
    assert loaded["contact_911"] is None
    assert set(loaded) == set(ACTIONS)
    assert revision.read_bytes() == original
    saved = save_bindings(loaded, tmp_path)
    assert saved != revision
    assert load_bindings(tmp_path)[0] == loaded
    assert revision.read_bytes() == original
