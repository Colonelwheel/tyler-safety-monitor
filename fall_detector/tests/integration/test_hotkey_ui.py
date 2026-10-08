"""Offscreen one-pointer shortcut editors; backend and files are synthetic."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from tyler_safety_monitor.hotkeys import ACTIONS, GlobalHotkeys, HotkeyBinding, save_bindings
from tyler_safety_monitor.hotkey_ui import HotkeyPanel


class FakeBackend:
    def __init__(self):
        self.registered = {}
        self.conflict = False

    def register(self, identifier, modifiers, key):
        if self.conflict:
            raise OSError("synthetic OS conflict")
        self.registered[identifier] = (modifiers, key)

    def unregister(self, identifier):
        self.registered.pop(identifier)


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.fixture
def panel(application, tmp_path):
    backend = FakeBackend()
    manager = GlobalHotkeys(backend)
    widget = HotkeyPanel(manager, directory=tmp_path / "hotkeys")
    yield widget, manager, backend
    manager.close()
    widget.close()
    widget.deleteLater()
    manager.deleteLater()
    application.processEvents()


def tap(control):
    QTest.mouseClick(control, Qt.MouseButton.LeftButton)


def test_unassigned_defaults_large_separate_toggle_controls_and_no_save(panel):
    widget, manager, backend = panel
    assert manager.bindings == dict.fromkeys(ACTIONS)
    assert not backend.registered
    assert not widget.directory.exists()
    for button in widget.findChildren(QPushButton):
        assert button.minimumHeight() >= 60
        assert button.accessibleName()
    for row in widget.rows.values():
        assert row.key.minimumHeight() >= 60
        assert row.key.currentIndex() == 0
        assert not row.ctrl.isChecked()
    assert "does not listen" in widget.banner.text()


def test_apply_remove_and_save_are_separate_pointer_actions(panel):
    widget, manager, backend = panel
    row = widget.rows["cancel"]
    row.key.setCurrentText("F13")
    tap(row.ctrl)
    tap(row.shift)
    assert manager.bindings["cancel"] is None
    tap(row.apply_button)
    assert manager.bindings["cancel"] == HotkeyBinding("F13", ctrl=True, shift=True)
    assert "Ctrl+Shift+F13" in row.active.text()
    assert not widget.directory.exists()
    tap(widget.save_button)
    revisions = list(widget.directory.iterdir())
    assert len(revisions) == 1
    previous_bytes = revisions[0].read_bytes()
    tap(row.remove_button)
    assert manager.bindings["cancel"] is None
    assert row.key.currentIndex() == 0
    assert not row.ctrl.isChecked()
    assert revisions[0].read_bytes() == previous_bytes
    tap(widget.save_button)
    assert len(list(widget.directory.iterdir())) == 2


def test_failed_apply_and_duplicate_remain_visible_preserve_active(panel):
    widget, manager, backend = panel
    row = widget.rows["fall"]
    row.key.setCurrentText("F14")
    tap(row.apply_button)
    backend.conflict = True
    row.key.setCurrentText("F15")
    tap(row.apply_button)
    assert manager.bindings["fall"] == HotkeyBinding("F14")
    assert "conflict" in widget.status.text()
    assert row.active.text() == "Active: F14"
    backend.conflict = False
    other = widget.rows["choking"]
    other.key.setCurrentText("F14")
    tap(other.apply_button)
    assert manager.bindings["choking"] is None
    assert "already assigned" in widget.status.text()
    other.key.setCurrentIndex(0)
    tap(other.apply_button)
    assert "supported key" in widget.status.text()


def test_loaded_revision_registers_only_saved_bindings_and_reports_conflicts(application, tmp_path):
    bindings = dict.fromkeys(ACTIONS)
    bindings["cancel"] = HotkeyBinding("F16")
    save_bindings(bindings, tmp_path)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    backend = FakeBackend()
    backend.conflict = True
    manager = GlobalHotkeys(backend)
    widget = HotkeyPanel(manager, directory=tmp_path)
    try:
        assert manager.bindings == dict.fromkeys(ACTIONS)
        assert "conflict" in widget.status.text()
        assert widget.rows["cancel"].active.text() == "Active: unassigned"
        assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
    finally:
        manager.close()
        widget.deleteLater()
        manager.deleteLater()


def test_loaded_revision_and_corruption_are_visible_read_only(application, tmp_path):
    bindings = dict.fromkeys(ACTIONS)
    bindings["night"] = HotkeyBinding("N", ctrl=True, alt=True)
    save_bindings(bindings, tmp_path)
    manager = GlobalHotkeys(FakeBackend())
    widget = HotkeyPanel(manager, directory=tmp_path)
    try:
        assert manager.bindings == bindings
        assert widget.rows["night"].key.currentText() == "N"
        assert widget.rows["night"].ctrl.isChecked()
        assert widget.rows["night"].alt.isChecked()
    finally:
        manager.close()
        widget.deleteLater()
        manager.deleteLater()
    fault = tmp_path / "hotkeys-00000000000000000002.json"
    fault.write_text("broken")
    manager = GlobalHotkeys(FakeBackend())
    widget = HotkeyPanel(manager, directory=tmp_path)
    try:
        assert manager.bindings == dict.fromkeys(ACTIONS)
        assert "fault" in widget.status.text().lower()
        assert fault.read_text() == "broken"
    finally:
        manager.close()
        widget.deleteLater()
        manager.deleteLater()


def test_panel_fits_narrow_scroll_region_without_horizontal_growth(panel, application):
    widget, manager, backend = panel
    widget.setStyleSheet("QWidget {font-size:16px;}")
    widget.resize(400, 430)
    widget.show()
    application.processEvents()
    assert widget.width() == 400
    assert widget.height() == 430
    assert widget.scroll.horizontalScrollBar().maximum() == 0
    assert widget.rect().contains(widget.save_button.geometry())
    widget.scroll.verticalScrollBar().setValue(widget.scroll.verticalScrollBar().maximum())
    application.processEvents()
    last = widget.rows["contact_911"].remove_button
    position = last.mapTo(widget.scroll.viewport(), last.rect().center())
    assert widget.scroll.viewport().rect().contains(position)


def test_contact_911_configures_separately_and_defaults_unassigned(panel, application):
    widget, manager, backend = panel
    row = widget.rows["contact_911"]
    assert manager.bindings["contact_911"] is None
    assert "Contact 911" in row.key.accessibleName()
    assert "SIMULATION ONLY" in row.key.accessibleName()
    row.key.setCurrentText("F24")
    tap(row.alt)
    tap(row.apply_button)
    assert manager.bindings["contact_911"] == HotkeyBinding("F24", alt=True)
    dispatched = []
    manager.activated.connect(dispatched.append)
    identifier = next(iter(backend.registered))
    assert manager.dispatch_native(identifier)
    application.processEvents()
    assert dispatched == ["contact_911"]
    tap(row.remove_button)
    assert manager.bindings["contact_911"] is None
