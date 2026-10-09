"""Accessible test-only warning above ordinary windows."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)


def request_windows_foreground(hwnd, user32=None):
    """Request Windows topmost/activation without input injection or policy bypass."""
    import ctypes
    from ctypes import wintypes
    if user32 is None:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.SetWindowPos.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    # Retain geometry and owner z-order. This only changes this warning window.
    flags = 0x0001 | 0x0002 | 0x0040 | 0x0200
    topmost = user32.SetWindowPos(hwnd, wintypes.HWND(-1), 0, 0, 0, 0, flags)
    foreground = user32.SetForegroundWindow(hwnd)
    return bool(topmost and foreground)


class WarningWindow(QWidget):
    cancel_requested = Signal()
    choking_requested = Signal()
    stop_audio_requested = Signal()
    contact_911_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle("Tyler Safety Monitor — TEST WARNING")
        self.setStyleSheet("background:#28161c;color:white")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        self.banner = QLabel("TEST ONLY • No message sent")
        self.banner.setStyleSheet("font-size:24px;font-weight:700")
        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size:36px;font-weight:700")
        self.countdown = QLabel()
        self.countdown.setWordWrap(True)
        self.countdown.setStyleSheet("font-size:56px;font-weight:700")
        for widget in (self.banner, self.title, self.countdown):
            layout.addWidget(widget)
        details = QWidget()
        details_layout = QVBoxLayout(details)
        self.reason = QLabel()
        self.reason.setWordWrap(True)
        self.reason.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.reason.setStyleSheet("font-size:22px")
        self.uncertainty = QLabel()
        self.uncertainty.setWordWrap(True)
        self.uncertainty.setStyleSheet("font-size:22px")
        self.note = QLabel("Selected app volume only. Windows mute/maximum-volume changes and all messaging are simulated.")
        self.note.setWordWrap(True)
        self.messaging_status = QLabel()
        self.messaging_status.setWordWrap(True)
        self.messaging_status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.messaging_status.setAccessibleName("Simulated warning message status and preview")
        self.foreground_status = QLabel()
        self.foreground_status.setWordWrap(True)
        for widget in (self.reason, self.uncertainty, self.note, self.messaging_status, self.foreground_status):
            details_layout.addWidget(widget)
        details_layout.addStretch()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(details)
        self.scroll.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.scroll, 1)
        self.choking_button = QPushButton("Choking — TEST ONLY")
        self.choking_button.setStyleSheet("background:#713540;font-size:20px;font-weight:700")
        self.stop_audio_button = QPushButton("Stop Test Audio")
        self.stop_audio_button.setStyleSheet("background:#454545;font-size:20px")
        actions = QHBoxLayout()
        for control in (self.choking_button, self.stop_audio_button):
            control.setMinimumHeight(60)
            control.setAccessibleName(control.text())
            actions.addWidget(control)
        self.choking_button.clicked.connect(self.choking_requested)
        self.stop_audio_button.clicked.connect(self.stop_audio_requested)
        layout.addLayout(actions)
        self.contact_911_button = QPushButton("Contact 911 - SIMULATION ONLY")
        self.contact_911_button.setMinimumHeight(60)
        self.contact_911_button.setAccessibleName("Contact 911 - SIMULATION ONLY")
        self.contact_911_button.setStyleSheet("background:#805217;font-size:22px;font-weight:700")
        self.contact_911_button.clicked.connect(self.contact_911_requested)
        self.contact_911_button.hide()
        self.contact_911_status = QLabel()
        self.contact_911_status.setWordWrap(True)
        self.contact_911_status.setStyleSheet("font-size:18px;font-weight:700")
        self.contact_911_status.hide()
        layout.addWidget(self.contact_911_status)
        layout.addWidget(self.contact_911_button)
        self.cancel_button = QPushButton("Cancel Test Alert")
        self.cancel_button.setMinimumHeight(100)
        self.cancel_button.setAccessibleName("Cancel Test Alert")
        self.cancel_button.setStyleSheet("background:#276b49;font-size:32px;font-weight:700")
        self.cancel_button.clicked.connect(self.cancel_requested)
        layout.addWidget(self.cancel_button)

    def update_snapshot(self, snapshot):
        choking = snapshot.choking
        self.title.setText("Choking — TEST ONLY" if choking else "Possible Fall — TEST ONLY")
        self.contact_911_button.setVisible(choking)
        label = "Immediate test alert" if choking else "Test alert active - no message sent"
        self.countdown.setText(label if snapshot.remaining is None
                               else f"{max(0., snapshot.remaining):.1f} seconds")
        self.reason.setText(snapshot.reason.replace("no message or audio action", "no message sent"))
        uncertainty = ("UNCERTAIN • missing evidence does not reset the deadline."
                       if snapshot.uncertain else "Synthetic evidence only; no live recognition.")
        if snapshot.caregiver:
            uncertainty += " Caregiver silence retained - synthetic only; choking remains unresolved." if choking else " Caregiver silence retained - synthetic only."
        elif snapshot.choking_silent:
            uncertainty += " Choking audio remains silent until manual cancellation."
        self.uncertainty.setText(uncertainty)

    def set_messaging_status(self, text):
        # Delivery information stays reachable inside the warning's detail scroll.
        self.messaging_status.setText(text)

    def present(self):
        self.showFullScreen()
        self.bring_forward()

    def bring_forward(self):
        """One request per transition/show or explicit user action, never a tick loop."""
        self.raise_()
        self.activateWindow()
        handle = self.windowHandle()
        if handle is not None:
            handle.requestActivate()
        if QGuiApplication.platformName() == "windows":
            try:
                confirmed = request_windows_foreground(int(self.winId()))
            except Exception:
                confirmed = False
            self.foreground_status.setText(
                "" if confirmed else
                "Windows foreground activation not confirmed; exclusive fullscreen visibility is unverified."
            )

    def set_contact_911_status(self, simulated):
        self.contact_911_status.setText(
            "911 contact simulated; no call placed. Choking remains unresolved."
            if simulated else ""
        )
        self.contact_911_status.setVisible(simulated)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        self.cancel_requested.emit()
        event.ignore()
        self.hide()
