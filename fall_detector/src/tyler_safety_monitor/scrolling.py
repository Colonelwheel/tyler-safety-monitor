"""Let a settings panel scroll without silently changing its options."""
from PySide6.QtCore import QEvent, QObject, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QAbstractSpinBox, QComboBox, QLineEdit, QWidget


class PanelWheelGuard(QObject):
    """Closed selectors and numeric editors yield wheel input to their panel.

    Taps, arrow buttons, typing and keyboard navigation remain unchanged. An
    explicitly opened dropdown still permits scrolling through its choices.
    """

    def __init__(self, scroll):
        super().__init__(scroll)
        self.scroll = scroll
        self.controls = {}
        for control in scroll.widget().findChildren(QWidget):
            if isinstance(control, (QAbstractSpinBox, QComboBox)):
                self.controls[control] = control
                control.installEventFilter(self)
                for editor in control.findChildren(QLineEdit):
                    self.controls[editor] = control
                    editor.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Wheel:
            control = self.controls.get(watched)
            if isinstance(control, QComboBox) and control.view().isVisible():
                return False
            pixels = event.pixelDelta()
            if not pixels.isNull():
                # Desktop/remote Qt backends can discard pixel-only gestures.
                # Their signed deltas already express the chosen scroll direction.
                for bar, delta in ((self.scroll.verticalScrollBar(), pixels.y()),
                                   (self.scroll.horizontalScrollBar(), pixels.x())):
                    bar.setValue(bar.value() - delta)
                event.accept()
                return True
            # Forward once, preserving touchpad pixel deltas and wheel phase.
            # Ignoring alone can swallow injected/remote wheel events on Windows.
            viewport = self.scroll.viewport()
            position = QPointF(viewport.mapFromGlobal(event.globalPosition().toPoint()))
            forwarded = QWheelEvent(position, event.globalPosition(), event.pixelDelta(),
                                    event.angleDelta(), event.buttons(), event.modifiers(),
                                    event.phase(), event.inverted(), event.source())
            QApplication.sendEvent(viewport, forwarded)
            event.accept()
            return True
        return super().eventFilter(watched, event)
