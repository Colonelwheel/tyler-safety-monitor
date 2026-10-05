"""One-pointer observation dashboard. No emergency or messaging adapter exists."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time
import threading

import cv2
from PySide6.QtCore import QEvent, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QHBoxLayout, QLabel, QMainWindow,
    QMenu, QPushButton, QScrollArea, QSpinBox, QSystemTrayIcon, QTabWidget, QVBoxLayout, QWidget,
)

from .audio import TestSound
from .camera import CameraCapture, CameraSettings
from .scene import Rect, SceneConfig
from .settings import AppSettings, load_settings, save_settings
from .tracking import PersonTracker


class Preview(QWidget):
    point_selected = Signal(float, float)

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumSize(480, 270)
        self.image = None
        self.scene = SceneConfig()
        self.tracks = []
        self.pending_corner = None
        self.caption = "Waiting for camera"
        self.geometry_available = False
        self.frame_ratio = 16 / 9
        self.trajectory_segments = {}
        self.zones = {}
        self.reviewed_zones = set()

    def image_rect(self) -> QRectF:
        ratio = self.image.width() / self.image.height() if self.image is not None else self.frame_ratio
        width = min(self.width(), self.height() * ratio)
        height = width / ratio
        return QRectF((self.width() - width) / 2, (self.height() - height) / 2, width, height)

    def set_frame(self, frame) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        self.image = QImage(rgb.data, width, height, rgb.strides[0], QImage.Format.Format_RGB888).copy()
        self.geometry_available = True
        self.frame_ratio = width / height
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#101724"))
        area = self.image_rect()
        if self.image is not None:
            painter.drawImage(area, self.image)
        else:
            painter.setPen(QColor("#dce5f1"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.caption)
        def box(rect):
            return QRectF(area.x() + rect.x * area.width(), area.y() + rect.y * area.height(),
                          rect.width * area.width(), rect.height * area.height())
        painter.setPen(QPen(QColor("#58dfb1"), 3))
        painter.drawRect(box(self.scene.roi))
        for exclusion in self.scene.exclusions:
            painter.fillRect(box(exclusion), QColor(5, 5, 5, 200))
            painter.setPen(QPen(QColor("#ffbd66"), 3))
            painter.drawRect(box(exclusion))
        for name, rect in self.zones.items():
            reviewed = name in self.reviewed_zones
            color = QColor("#8bdd98" if reviewed else "#df8cff")
            pen = QPen(color, 2)
            if not reviewed:
                pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)
            region = box(rect)
            painter.drawRect(region)
            painter.drawText(int(region.x() + 4), int(region.y() + 18),
                             name.replace("_", " ") + (" • reviewed" if reviewed else " • proposed"))
        painter.setPen(QPen(QColor("#66dbff"), 2))
        for segments in self.trajectory_segments.values():
            for segment in segments:
                for a, b in zip(segment, segment[1:]):
                    painter.drawLine(int(area.x() + a[0] * area.width()), int(area.y() + a[1] * area.height()),
                                     int(area.x() + b[0] * area.width()), int(area.y() + b[1] * area.height()))
        for track in self.tracks:
            x = area.x() + track.head[0] * area.width()
            y = area.y() + track.head[1] * area.height()
            color = QColor("#ffd66e") if track.identity_uncertain else QColor("#66dbff")
            painter.setPen(QPen(color, 3))
            painter.drawEllipse(QRectF(x - 9, y - 9, 18, 18))
            painter.drawText(int(x + 14), int(y), f"P{track.id}  {track.confidence:.0%}")
            for point, scores in zip(track.landmarks, getattr(track, "landmark_scores", ())):
                confidence = min(scores)
                # Never render invisible inferred limbs as confirmed landmarks.
                if confidence < 0.5 or not self.scene.accepts_point(point[0], point[1]):
                    continue
                painter.setPen(QPen(QColor("#8bdd98" if confidence >= 0.8 else "#ffd66e"), 3))
                painter.drawPoint(int(area.x() + point[0] * area.width()), int(area.y() + point[1] * area.height()))
            if track.shoulders:
                sx = area.x() + track.shoulders[0] * area.width()
                sy = area.y() + track.shoulders[1] * area.height()
                painter.drawLine(int(x), int(y), int(sx), int(sy))
        if self.pending_corner:
            x = area.x() + self.pending_corner[0] * area.width()
            y = area.y() + self.pending_corner[1] * area.height()
            painter.setPen(QPen(QColor("#ffffff"), 3))
            painter.drawEllipse(QRectF(x - 8, y - 8, 16, 16))

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton or not self.geometry_available:
            return
        area = self.image_rect()
        if area.contains(event.position()):
            self.point_selected.emit((event.position().x() - area.x()) / area.width(),
                                     (event.position().y() - area.y()) / area.height())


def button(label: str, callback) -> QPushButton:
    control = QPushButton(label)
    control.setMinimumHeight(60)
    control.setAccessibleName(label)
    control.clicked.connect(callback)
    return control


class Dashboard(QMainWindow):
    cleanup_finished = Signal(object, object, bool, bool)

    def __init__(self, model_path: Path, enable_camera: bool = True) -> None:
        super().__init__()
        self.setWindowTitle("Tyler Safety Monitor — Calibration and Replay")
        self.resize(1400, 900)
        self.settings, settings_status = load_settings()
        self.model_path = model_path
        self.capture = None
        self.pose = None
        self.sound = TestSound()
        self.tracker = PersonTracker()
        self.last_sequence = -1
        self.last_pose_timestamp = -1
        self.last_pose_seen_at = 0.0
        self.last_tray_state = None
        self.edit_mode = None
        self.shut_down = False
        self._retiring = None
        self._cleanup_thread = None
        self._restart_requested = False
        self._blocked_pose = None
        self._cleanup_failed = False
        self._failed_workers = None
        self._pose_inputs = {}
        self._model_timestamp = -1
        self._capture_generation = 0
        self.cleanup_finished.connect(self.finish_cleanup)
        self.preview = Preview()
        self.preview.scene = self.settings.scene
        self.preview.point_selected.connect(self.select_corner)

        central = QWidget()
        layout = QHBoxLayout(central)
        main = QVBoxLayout()
        banner = QLabel("OBSERVATION ONLY • Caregiver messaging and emergency actions disabled")
        banner.setWordWrap(True)
        banner.setStyleSheet("background:#5b3d11;color:#ffe4ac;padding:14px;font-weight:700")
        main.addWidget(banner)
        capture_row = QHBoxLayout()
        self.capture_banner = QLabel("Calibration idle • no personal data collected")
        self.capture_banner.setWordWrap(True)
        capture_row.addWidget(self.capture_banner, 1)
        self.capture_stop = button("Stop / Review Capture", lambda: self.tools.stop_capture())
        capture_row.addWidget(self.capture_stop)
        main.addLayout(capture_row)
        main.addWidget(self.preview, 1)
        # Keep the essential volume controls visible without scrolling the
        # setup panel, even on Windows displays with large text scaling.
        volume_row = QHBoxLayout()
        self.volume_label = QLabel()
        volume_row.addWidget(self.volume_label)
        volume_row.addWidget(button("Decrease", lambda: self.change_volume(-0.1)))
        volume_row.addWidget(button("Increase", lambda: self.change_volume(0.1)))
        volume_row.addWidget(button("Test Sound", self.test_sound))
        volume_row.addWidget(button("Stop Test Sound", self.sound.stop))
        main.addLayout(volume_row)
        self.health = QLabel("Camera stopped")
        self.health.setWordWrap(True)
        self.health.setMinimumHeight(100)
        main.addWidget(self.health)
        self.pose_status = QLabel("Pose model not started")
        self.pose_status.setWordWrap(True)
        main.addWidget(self.pose_status)
        main.addWidget(QLabel("Tracks are person candidates. No fall classification or caregiver confirmation."))
        legend = QLabel("Landmark scores: green ≥80%, amber 50–80%, hidden below 50%. Visibility/presence scores are not safety accuracy.")
        legend.setWordWrap(True)
        main.addWidget(legend)
        layout.addLayout(main, 3)

        panel = QWidget()
        controls = QVBoxLayout(panel)
        controls.addWidget(QLabel("Camera"))
        self.camera_index = QSpinBox()
        self.camera_index.setRange(0, 20)
        self.camera_index.setValue(self.settings.camera_index)
        self.camera_index.setMinimumHeight(50)
        self.camera_index.setAccessibleName("Camera number")
        controls.addWidget(self.camera_index)
        self.backend = QComboBox()
        self.backend.addItem("DirectShow", "dshow")
        self.backend.addItem("Media Foundation", "msmf")
        self.backend.setCurrentIndex(0 if self.settings.backend == "dshow" else 1)
        self.backend.setMinimumHeight(50)
        self.backend.setAccessibleName("Camera backend")
        controls.addWidget(self.backend)
        self.fps = QComboBox()
        self.fps.addItem("1080p • 30 FPS", 30)
        self.fps.addItem("1080p • 15 FPS", 15)
        self.fps.setCurrentIndex(0 if self.settings.fps == 30 else 1)
        self.fps.setMinimumHeight(50)
        self.fps.setAccessibleName("Requested camera frame rate")
        controls.addWidget(self.fps)
        controls.addWidget(button("Start / Retry Camera", self.start_camera))
        controls.addWidget(button("Pause Camera", self.pause_camera))

        controls.addWidget(QLabel("Inference region • two separate taps"))
        controls.addWidget(button("Set ROI", lambda: self.begin_edit("roi")))
        controls.addWidget(button("Add Exclusion Mask", lambda: self.begin_edit("mask")))
        controls.addWidget(button("Cancel Region Edit", self.cancel_edit))
        controls.addWidget(button("Full Frame ROI", self.full_roi))
        controls.addWidget(button("Undo Last Mask", self.undo_mask))
        self.edit_status = QLabel("Review the picture reflection and caregiver-entry area before use.")
        self.edit_status.setWordWrap(True)
        controls.addWidget(self.edit_status)

        controls.addWidget(button("Save Settings", self.save))
        self.settings_status = QLabel(settings_status)
        self.settings_status.setWordWrap(True)
        controls.addWidget(self.settings_status)
        self.minimize_button = button("Minimize to Tray", self.minimize_dashboard)
        controls.addWidget(self.minimize_button)
        controls.addWidget(button("Exit Application", QApplication.instance().quit))
        controls.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(panel)
        scroll.setMinimumWidth(350)
        from .calibration_ui import MilestoneTools
        self.tools = MilestoneTools(self)
        tools_scroll = QScrollArea()
        tools_scroll.setWidgetResizable(True)
        tools_scroll.setWidget(self.tools)
        self.tabs = QTabWidget()
        self.tabs.setMinimumWidth(440)
        self.tabs.addTab(scroll, "Camera / Masks")
        self.tabs.addTab(tools_scroll, "Calibration / Replay")
        layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
        self.setStyleSheet("""
            QWidget {background:#182235;color:#e4ecf7;font-size:16px;}
            QPushButton {background:#2b405c;border:1px solid #607d9e;border-radius:8px;padding:8px;}
            QPushButton:hover {background:#385475;}
            QPushButton:focus {border:3px solid #78d8ff;}
            QComboBox,QSpinBox {background:#263950;padding:8px;}
            QScrollBar:vertical {width:26px;}
            QScrollBar::handle:vertical {background:#607d9e;min-height:65px;}
        """)
        self.update_volume_label()

        self.tray_available = QSystemTrayIcon.isSystemTrayAvailable()
        if not self.tray_available:
            self.minimize_button.setText("Minimize to Taskbar")
            self.minimize_button.setAccessibleName("Minimize to Taskbar")
        self.tray = QSystemTrayIcon(self.status_icon("#e9bb64"), self)
        self.tray.setToolTip("Tyler Safety Monitor • observation only")
        menu = QMenu()
        for text, callback in (("Open Dashboard", self.open_dashboard),
                               ("Retry Camera", self.start_camera),
                               ("Pause Camera", self.pause_camera),
                               ("Exit", QApplication.instance().quit)):
            action = QAction(text, self)
            action.triggered.connect(callback)
            menu.addAction(action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_activated)
        if self.tray_available:
            self.tray.show()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(50)
        if enable_camera:
            self.start_camera()

    @staticmethod
    def status_icon(color: str) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setBrush(QColor(color))
        painter.setPen(QPen(QColor("#ffffff"), 3))
        painter.drawRoundedRect(6, 6, 52, 52, 12, 12)
        painter.setPen(QPen(QColor("#122034"), 6))
        painter.drawLine(17, 32, 28, 43)
        painter.drawLine(28, 43, 48, 21)
        painter.end()
        return QIcon(pixmap)

    def tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.open_dashboard()

    def open_dashboard(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def minimize_dashboard(self) -> None:
        self.tools.stop_capture("Dashboard minimized; capture ended so controls remain visible during collection.")
        if self.tray_available:
            self.hide()
        else:
            self.showMinimized()

    def closeEvent(self, event) -> None:
        self.tools.stop_capture("Dashboard closed; capture ended and features retained for review.")
        if self.tray_available and not self.shut_down:
            event.ignore()
            self.hide()
        else:
            event.accept()
            QApplication.instance().quit()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized() and hasattr(self, "tools"):
            self.tools.stop_capture("Window minimized; feature collection stopped and data retained.")
        super().changeEvent(event)

    def hideEvent(self, event) -> None:
        if hasattr(self, "tools"):
            self.tools.stop_capture("Dashboard hidden; feature collection stopped and data retained.")
        super().hideEvent(event)

    def read_controls(self) -> AppSettings:
        return replace(self.settings, camera_index=self.camera_index.value(),
                       backend=self.backend.currentData(), fps=self.fps.currentData())

    def start_camera(self) -> None:
        if self._cleanup_failed and self._blocked_pose is None:
            self.pose_status.setText("Worker cleanup fault. Exit and restart the application before retrying.")
            return
        if self._blocked_pose is not None:
            if getattr(self._blocked_pose, "is_alive", False):
                self.pose_status.setText("Pose worker did not stop. Exit and restart the application before retrying.")
                return
            self._blocked_pose = None
            self._cleanup_failed = False
        if self._retiring is not None:
            self._restart_requested = True
            self.health.setText("Stopping previous camera; restart will begin when cleanup completes.")
            return
        if self.capture is not None or self.pose is not None:
            self.pause_camera()
            self._restart_requested = True
            self.health.setText("Stopping previous camera; restart will begin when cleanup completes.")
            return
        self._start_camera()

    def _start_camera(self) -> None:
        if self.tools.player is not None:
            self.tools.leave_replay()
        self.tools.trajectory.clear()
        self.preview.trajectory_segments = {}
        self.preview.zones = {}
        self.preview.reviewed_zones = set()
        self._pose_inputs.clear()
        self._model_timestamp = -1
        self._capture_generation += 1
        self.settings = self.read_controls()
        self.capture = CameraCapture(CameraSettings(index=self.settings.camera_index,
                                      backend=self.settings.backend, fps=self.settings.fps))
        self.capture.start()
        self.last_sequence = -1
        self.tracker = PersonTracker()
        self.last_pose_timestamp = -1
        self.pose = None
        if self.model_path.is_file():
            try:
                from .pose import PoseWorker
                self.pose = PoseWorker(self.model_path, self.settings.scene, num_poses=2)
                self.pose.start()
                self.pose_status.setText("Pose model starting • two-person capacity • observation only")
            except Exception as error:
                self.pose_status.setText(f"Pose initialization fault: {error}")
        else:
            self.pose_status.setText("Pose model missing. Download it explicitly using the documented model command.")

    def pause_camera(self) -> None:
        self.tools.stop_capture("Camera paused; previously collected features remain in memory.")
        self.tools.last_live_tracks = []
        self.tools.trajectory.clear()
        self.preview.trajectory_segments = {}
        self.preview.zones = {}
        self.preview.reviewed_zones = set()
        self._pose_inputs.clear()
        self._restart_requested = False
        self.sound.stop()
        capture, pose = self.capture, self.pose
        self.capture = self.pose = None
        if (capture is not None or pose is not None) and self._retiring is None:
            self._retiring = (capture, pose)
            def cleanup():
                cleanup_exception = False
                try:
                    if capture is not None:
                        capture.stop()
                    if pose is not None:
                        pose.close()
                    stopped = not getattr(pose, "is_alive", False)
                except Exception:
                    stopped = False
                    cleanup_exception = True
                self.cleanup_finished.emit(capture, pose, stopped, cleanup_exception)
            self._cleanup_thread = threading.Thread(target=cleanup, name="dashboard-cleanup", daemon=True)
            self._cleanup_thread.start()
        self.preview.tracks = []
        self.preview.caption = "Camera paused"
        self.preview.image = None
        self.preview.geometry_available = False
        self.preview.update()
        self.health.setText("Camera paused • no automatic monitoring or messaging")
        self.pose_status.setText("Pose processing paused")

    def finish_cleanup(self, capture, pose, stopped: bool, cleanup_exception: bool = False) -> None:
        self._retiring = None
        if not stopped:
            self._failed_workers = (capture, pose)
            # Unverified camera cleanup must never become retryable just because
            # an accompanying pose thread happened to exit.
            self._blocked_pose = None if cleanup_exception else pose
            self._cleanup_failed = True
            self._restart_requested = False
            self.pose_status.setText("Worker cleanup fault. Exit and restart the application before retrying.")
        elif self._restart_requested and not self.shut_down:
            self._restart_requested = False
            self._start_camera()

    def begin_edit(self, mode: str) -> None:
        if self.tools.state in {"delay", "capturing"}:
            self.edit_status.setText("Stop / Review calibration before editing the scene.")
            return
        if self.tools.player is not None and not mode.startswith("zone:"):
            self.edit_status.setText("Return to live view before changing camera ROI or masks.")
            return
        self.edit_mode = mode
        self.preview.pending_corner = None
        self.edit_status.setText("Tap the first corner in the preview, then the opposite corner.")
        self.preview.update()

    def cancel_edit(self) -> None:
        self.edit_mode = None
        self.preview.pending_corner = None
        self.edit_status.setText("Region edit canceled.")
        self.preview.update()

    def select_corner(self, x: float, y: float) -> None:
        if self.edit_mode is None:
            return
        if self.preview.pending_corner is None:
            self.preview.pending_corner = (x, y)
            self.edit_status.setText("First corner selected. Tap the opposite corner.")
        else:
            try:
                rect = Rect.from_corners(*self.preview.pending_corner, x, y)
                if self.edit_mode.startswith("zone:"):
                    self.tools.set_zone(self.edit_mode.split(":", 1)[1], rect)
                    self.edit_status.setText("Zone proposed. Review it in Calibration / Replay before saving.")
                    self.edit_mode = None
                    self.preview.pending_corner = None
                    self.preview.update()
                    return
                elif self.edit_mode == "roi":
                    scene = replace(self.settings.scene, roi=rect)
                else:
                    scene = replace(self.settings.scene, exclusions=self.settings.scene.exclusions + (rect,))
                self.set_scene(scene)
                self.edit_status.setText("Region applied. Save Settings to retain it locally.")
                self.edit_mode = None
                self.preview.pending_corner = None
            except ValueError as error:
                self.edit_status.setText(f"Choose a nonempty region: {error}")
        self.preview.update()

    def set_scene(self, scene: SceneConfig) -> None:
        if self.tools.player is not None:
            self.edit_status.setText("Return to live view before changing camera ROI or masks.")
            return
        self.settings = replace(self.settings, scene=scene)
        self.preview.scene = scene
        self.preview.tracks = []
        self.tracker = PersonTracker()
        self.last_pose_timestamp = -1
        self._pose_inputs.clear()
        if self.pose is not None:
            self.pose.set_scene(scene)
        self.tools.scene_changed()
        self.preview.update()

    def full_roi(self) -> None:
        if self.tools.player is not None:
            self.edit_status.setText("Return to live view before changing camera ROI or masks.")
            return
        self.cancel_edit()
        self.set_scene(replace(self.settings.scene, roi=Rect(0, 0, 1, 1)))
        self.edit_status.setText("Full frame ROI applied; existing exclusions retained.")

    def undo_mask(self) -> None:
        if self.tools.player is not None:
            self.edit_status.setText("Return to live view before changing camera ROI or masks.")
            return
        self.cancel_edit()
        self.set_scene(replace(self.settings.scene, exclusions=self.settings.scene.exclusions[:-1]))
        self.edit_status.setText("Last exclusion removed. Review the preview.")

    def update_volume_label(self) -> None:
        self.volume_label.setText(f"Alert Volume: {self.settings.alert_volume:.0%}")

    def change_volume(self, delta: float) -> None:
        volume = round(max(0.0, min(1.0, self.settings.alert_volume + delta)), 2)
        self.settings = replace(self.settings, alert_volume=volume)
        self.update_volume_label()
        if self.sound.sink is not None:
            self.sound.sink.setVolume(volume)

    def test_sound(self) -> None:
        try:
            self.sound.play(self.settings.alert_volume)
            self.settings_status.setText("Test Sound uses the selected app volume. Windows volume is unchanged.")
        except Exception as error:
            self.settings_status.setText(f"Test Sound fault: {error}")

    def save(self) -> None:
        try:
            self.settings = self.read_controls()
            save_settings(self.settings)
            self.settings_status.setText("Saved a new local settings revision. Previous revisions retained.")
        except (OSError, ValueError, RuntimeError) as error:
            self.settings_status.setText(f"Settings were not saved: {error}")

    def refresh(self) -> None:
        self.tools.tick()
        if self.tools.render_replay():
            return
        if self.capture is None:
            return
        metrics = self.capture.snapshot()
        self.tools.show_zones()
        age = "no frames" if metrics.frame_age is None else f"{metrics.frame_age:.2f}s old"
        self.health.setText(
            f"Camera: {metrics.state} • {metrics.detail}\n"
            f"{metrics.actual_width} × {metrics.actual_height} • {metrics.actual_fourcc} • "
            f"captured {metrics.delivered_fps:.1f} FPS / received {metrics.received_fps:.1f} FPS • {age}\n"
            f"Brightness {metrics.brightness or 0:.1f} • blur metric {metrics.blur or 0:.1f} • "
            f"read failures {metrics.read_failures} • reconnects {metrics.reconnect_events}"
        )
        if metrics.state != self.last_tray_state:
            self.last_tray_state = metrics.state
            self.tray.setIcon(self.status_icon("#58dfb1" if metrics.state == "LIVE" else "#e9bb64"))
            self.tray.setToolTip(f"Tyler Safety Monitor • {metrics.state} • alerts disabled")
            if metrics.state == "FAULT" and self.tray_available:
                self.tray.showMessage("Camera unavailable", "Open dashboard to retry. Emergency alerts are disabled.",
                                      QSystemTrayIcon.MessageIcon.Warning)
        packet = self.capture.latest_frame()
        if packet is not None and packet.sequence != self.last_sequence and metrics.state == "LIVE":
            self.last_sequence = packet.sequence
            self.preview.set_frame(packet.image)
            if self.pose is not None:
                self._model_timestamp = max(int(packet.captured_at * 1000), self._model_timestamp + 1)
                if self.pose.submit(packet.image, self._model_timestamp):
                    self._pose_inputs[self._model_timestamp] = (packet.sequence, packet.captured_at)
                    while len(self._pose_inputs) > 256:
                        self._pose_inputs.pop(next(iter(self._pose_inputs)))
        if self.pose is not None:
            result = self.pose.latest_result
            stats = self.pose.stats
            if result is not None and result.timestamp_ms > self.last_pose_timestamp:
                self.last_pose_timestamp = result.timestamp_ms
                self.last_pose_seen_at = result.timestamp_ms / 1000
                if not 0 <= time.monotonic() - self.last_pose_seen_at <= 1.0:
                    self.preview.tracks = []
                else:
                    try:
                        self.preview.tracks = self.tracker.update(result.observations, self.last_pose_seen_at)
                        source = self._pose_inputs.get(result.timestamp_ms)
                        # Unmatched native results may display, but must never be
                        # recorded with an invented frame index or source time.
                        if source is not None:
                            self.tools.observe(result, self.preview.tracks, *source)
                    except ValueError:
                        self.preview.tracks = []
            error = self.pose.error
            pose_state = error or ("two-person capacity; candidates only" if getattr(self.pose, "ready", True)
                                   else "initializing local model")
            self.pose_status.setText(f"Pose: {pose_state} • "
                                     f"submitted {stats.submitted} / completed {stats.completed} / skipped {stats.dropped}")
        if metrics.state != "LIVE" or time.monotonic() - self.last_pose_seen_at > 1.0:
            self.preview.tracks = []
            self.tools.last_live_tracks = []
            self.tools.trajectory.clear()
            self.preview.trajectory_segments = {}
            if self.tools.state in {"delay", "capturing"}:
                self.tools.stop_capture("Camera or pose observations unavailable; uncertainty remains visible.")
        self.preview.update()

    def shutdown(self) -> None:
        if self.shut_down:
            return
        self.shut_down = True
        self.timer.stop()
        self.pause_camera()
        if self._cleanup_thread is not None:
            # Exiting may wait for bounded cleanup; ordinary controls never do.
            self._cleanup_thread.join(timeout=3.5)
        self.tray.hide()
