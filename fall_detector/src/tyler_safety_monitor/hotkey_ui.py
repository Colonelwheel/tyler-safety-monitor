"""One-pointer shortcut editing for VoiceAttack's external speech input."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QGridLayout, QGroupBox, QLabel,
                               QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget)

from .hotkeys import ACTIONS, KEYS, HotkeyBinding, load_bindings, save_bindings
from .scrolling import PanelWheelGuard


def _button(text, parent=None, *, checkable=False):
    button = QPushButton(text, parent)
    button.setMinimumHeight(60)
    button.setAccessibleName(text)
    button.setCheckable(checkable)
    button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    return button


def _label(text):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    return label


@dataclass
class HotkeyRow:
    key: QComboBox
    ctrl: QPushButton
    alt: QPushButton
    shift: QPushButton
    apply_button: QPushButton
    remove_button: QPushButton
    active: QLabel
    feedback: QLabel


class HotkeyPanel(QWidget):
    """Edits do not take effect until Apply; Save creates a separate new revision."""
    def __init__(self, manager, parent=None, *, load_saved=True, directory: Path | None = None):
        super().__init__(parent)
        self.manager = manager
        self.directory = directory
        self.rows = {}
        layout = QVBoxLayout(self)
        self.banner = _label("VOICEATTACK INPUT — TEST ONLY. The monitor does not listen to your microphone. "
                             "Choose a key and tap modifiers separately; no held chord is needed. "
                             "Apply / Remove works anytime. Assigned global keys are consumed even while minimized. "
                             "Commands work only when the local test controls are explicitly enabled.")
        layout.addWidget(_label("VoiceAttack Hotkeys — TEST ONLY"))
        self.status = _label("No shortcut assigned by default")
        self.status.setAccessibleName("Hotkey configuration status")
        self.status.setMaximumHeight(90)
        layout.addWidget(self.status)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumSize(0, 0)
        content = QWidget()
        groups = QVBoxLayout(content)
        groups.addWidget(self.banner)

        for action, title in ACTIONS.items():
            box = QGroupBox()
            grid = QGridLayout(box)
            grid.addWidget(_label(title), 0, 0, 1, 3)
            key = QComboBox()
            key.setMinimumHeight(60)
            key.setMinimumWidth(0)
            key.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            key.setAccessibleName(f"{title} key")
            key.addItem("Choose key", None)
            key.addItems(list(KEYS))
            grid.addWidget(key, 1, 0, 1, 3)
            modifiers = []
            for column, name in enumerate(("Ctrl", "Alt", "Shift")):
                button = _button(name, checkable=True)
                button.setAccessibleName(f"{title} {name} modifier")
                button.toggled.connect(lambda checked, control=button, label=name:
                                       control.setText(label + (" ON" if checked else " OFF")))
                button.setText(name + " OFF")
                grid.addWidget(button, 2, column)
                modifiers.append(button)
            apply_button = _button("Apply", checkable=False)
            apply_button.setAccessibleName(f"Apply {title} shortcut")
            remove_button = _button("Remove")
            remove_button.setAccessibleName(f"Remove {title} shortcut")
            grid.addWidget(apply_button, 3, 0, 1, 3)
            grid.addWidget(remove_button, 4, 0, 1, 3)
            active = _label("Active: unassigned")
            grid.addWidget(active, 5, 0, 1, 3)
            feedback = _label("")
            grid.addWidget(feedback, 6, 0, 1, 3)
            row = HotkeyRow(key, *modifiers, apply_button, remove_button, active, feedback)
            self.rows[action] = row
            apply_button.clicked.connect(lambda checked=False, selected=action: self.apply(selected))
            remove_button.clicked.connect(lambda checked=False, selected=action: self.remove(selected))
            groups.addWidget(box)
        groups.addStretch()
        self.scroll.setWidget(content)
        layout.addWidget(self.scroll, 1)
        self.save_button = _button("Save Applied Hotkeys")
        self.save_button.clicked.connect(self.save)
        layout.addWidget(self.save_button)
        self.wheel_guard = PanelWheelGuard(self.scroll)
        self.manager.changed.connect(self._changed)
        if load_saved:
            saved, message = load_bindings(directory)
            failures = []
            for action, binding in saved.items():
                if binding is not None and not self.manager.apply(action, binding):
                    failures.append(self.manager.status)
                    self.rows[action].feedback.setText(self.manager.status)
            self.status.setText(message + (". " + " ".join(failures) if failures else ""))
        else:
            self.status.setText("No saved hotkeys loaded; edits remain session-only until Save")
        for action in ACTIONS:
            self._sync_editor(action)
        self._refresh_active()

    def _refresh_active(self):
        for action, binding in self.manager.bindings.items():
            self.rows[action].active.setText("Active: " + (binding.label if binding else "unassigned"))

    def _sync_editor(self, action):
        row = self.rows[action]
        binding = self.manager.bindings[action]
        row.key.setCurrentIndex(row.key.findText(binding.key) if binding else 0)
        for button, name in ((row.ctrl, "ctrl"), (row.alt, "alt"), (row.shift, "shift")):
            button.setChecked(getattr(binding, name) if binding else False)

    def _changed(self, message):
        self.status.setText(message)
        self.status.setToolTip(message)
        self.status.setAccessibleDescription(message)
        self._refresh_active()

    def apply(self, action):
        row = self.rows[action]
        try:
            binding = HotkeyBinding(row.key.currentText(), row.ctrl.isChecked(),
                                    row.alt.isChecked(), row.shift.isChecked())
        except ValueError as error:
            self.status.setText(str(error) + ". Previous binding retained.")
            row.feedback.setText(self.status.text())
            return
        self.manager.apply(action, binding)
        row.feedback.setText(self.manager.status)

    def remove(self, action):
        if self.manager.remove(action):
            self._sync_editor(action)
        self.rows[action].feedback.setText(self.manager.status)

    def save(self):
        try:
            path = save_bindings(self.manager.bindings, self.directory)
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(f"Hotkeys not saved: {error}. Earlier revisions preserved.")
            return
        self.status.setText("Applied hotkeys saved as a new revision; earlier files preserved")
        self.status.setToolTip(str(path))
        self.status.setAccessibleDescription(str(path))
