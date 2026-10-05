"""One-pointer calibration and feature replay; all real data saves are opt-in.

Camera images are never recorded by this panel. Native clip analysis belongs to
the explicit offline command, keeping the dashboard responsive and camera-free
when replaying. No risk decision or 30-second safety timer is implemented here.
"""
from __future__ import annotations

from dataclasses import replace
import importlib.metadata
import hashlib
from pathlib import Path
import time

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from .calibration import (
    CalibrationProfile, build_provenance, load_profile, propose_zone, save_profile,
)
from .replay import (
    FeatureSample, FeatureSequence, ReplayPlayer, TrajectoryHistory,
    load_sequence, save_sequence,
)
from .scene import SceneConfig
from .settings import data_directory
from .tracking import PersonTracker, PoseObservation


STEPS = {
    "ordinary": "Stay in your ordinary safe posture. No special movement is needed.",
    "adjustments": "Only make routine small adjustments you already consider safe.",
    "intentional_lean": "Optional: lower your head only to an already-safe position, then recover. Stop whenever you want. Do not seek your deepest possible position.",
    "darkest": "Use ordinary safe posture in your usual darkest lighting. Assistance with lighting may remain pending.",
}
ZONE_NAMES = ("safe", "intentional_lean", "soft_boundary", "hard_boundary",
              "expected_person", "caregiver_entry")


class MilestoneTools(QWidget):
    def __init__(self, dashboard):
        super().__init__()
        self.dashboard = dashboard
        self.clock = time.monotonic
        self.state = "idle"
        self.deadline = 0.0
        self.samples = []
        self.points = {"safe": [], "intentional_lean": []}
        self.steps_taken = []
        self.capture_scene = None
        self.capture_dimensions = None
        self.capture_candidate = None
        self.capture_generation = None
        self.capture_provenance = None
        self.loaded_profile = False
        self.loaded_model_hash = None
        self.capture_step = None
        self.profile = None
        self.player = None
        self.replay_sequence = None
        self.replay_tracker = PersonTracker()
        self.trajectory = TrajectoryHistory()
        self.last_live_tracks = []
        self.saved_sample_count = 0
        layout = QVBoxLayout(self)
        heading = QLabel("CALIBRATION TOOLING • Alerts disabled\nCaregiver and assisted steps remain pending until supervised validation.")
        heading.setWordWrap(True)
        layout.addWidget(heading)
        self.step = QComboBox()
        for name, label in (("ordinary", "Ordinary safe posture"),
                            ("adjustments", "Routine small movements"),
                            ("intentional_lean", "Optional already-safe head down / recover"),
                            ("darkest", "Darkest lighting • ordinary posture")):
            self.step.addItem(label, name)
        self.step.setMinimumHeight(50)
        self.step.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.step.setMinimumContentsLength(18)
        self.step.setAccessibleName("Safe calibration step")
        layout.addWidget(self.step)
        self.instructions = QLabel()
        self.instructions.setWordWrap(True)
        layout.addWidget(self.instructions)
        self.step.currentIndexChanged.connect(self.explain_step)
        self.explain_step()
        self.scene_review = QCheckBox("Fixed camera / masks reviewed")
        self.scene_review.setMinimumHeight(50)
        layout.addWidget(self.scene_review)
        self.candidate = QComboBox()
        self.candidate.addItem("Choose your person candidate", None)
        self.candidate.setAccessibleName("Candidate to use for zone proposals")
        self.candidate.setMinimumHeight(50)
        self.candidate.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.candidate.setMinimumContentsLength(18)
        layout.addWidget(self.candidate)
        self.add_button(layout, "Start Feature Capture", self.request_capture)
        self.stop_button = self.add_button(layout, "Stop / Review Capture", self.stop_capture)
        self.status = QLabel("No capture started. Five-second delay, then at most 15 seconds. Images are not saved.")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addWidget(QLabel("Intentional-lean wiggle room • proposal only"))
        self.margin = QDoubleSpinBox()
        self.margin.setRange(0, 2)
        self.margin.setSingleStep(0.1)
        self.margin.setDecimals(1)
        self.margin.setSuffix("% of frame")
        self.margin.setMinimumHeight(50)
        self.margin.setAccessibleName("Reviewable intentional lean margin, percent of frame")
        self.margin.valueChanged.connect(self.margin_changed)
        layout.addWidget(self.margin)
        margin_buttons = QHBoxLayout()
        self.add_button(margin_buttons, "Less Wiggle Room", lambda: self.margin.setValue(self.margin.value() - 0.1))
        self.add_button(margin_buttons, "More Wiggle Room", lambda: self.margin.setValue(self.margin.value() + 0.1))
        layout.addLayout(margin_buttons)
        margin_note = QLabel("Starts at zero. A small extra distance can be proposed for day-to-day variation; review it visually. This is not an approved danger threshold. The ordinary-lean 30-second rule belongs to Milestone 2.")
        margin_note.setWordWrap(True)
        layout.addWidget(margin_note)
        self.zone = QComboBox()
        self.zone.setMinimumHeight(50)
        self.zone.setAccessibleName("Calibration zone to edit or review")
        for name in ZONE_NAMES:
            self.zone.addItem(name.replace("_", " "), name)
        layout.addWidget(self.zone)
        self.add_button(layout, "Propose Zone from Captured Points", self.propose)
        self.add_button(layout, "Draw Proposed Zone • Two Taps", self.draw_zone)
        self.add_button(layout, "Mark Selected Zone Reviewed", self.review_zone)
        self.add_button(layout, "Save New Profile / Features", self.request_save)
        self.add_button(layout, "New Session • Keep Saved Files", self.new_session)
        self.add_button(layout, "Open Local Profile", self.open_profile)
        self.add_button(layout, "Synthetic Replay Demo", self.demo)
        self.add_button(layout, "Open Feature Replay", self.open_replay)
        self.play_button = self.add_button(layout, "Play / Pause Replay", self.toggle_play)
        self.add_button(layout, "Replay from Beginning", self.rewind)
        self.add_button(layout, "Live View • Camera Stays Paused", self.leave_replay)
        for label in self.findChildren(QLabel):
            label.setWordWrap(True)
        layout.addStretch()

    @staticmethod
    def add_button(layout, label, callback):
        control = QPushButton(label)
        control.setAccessibleName(label)
        control.setMinimumHeight(60)
        control.clicked.connect(callback)
        layout.addWidget(control)
        return control

    def explain_step(self):
        self.instructions.setText(STEPS[self.step.currentData()])

    def message(self, text):
        self.status.setText(text)
        if hasattr(self.dashboard, "capture_banner"):
            # Keep capture state and Stop / Review outside the scroll panel.
            if self.state in {"delay", "capturing"}:
                self.dashboard.capture_banner.setText(text)
            else:
                self.dashboard.capture_banner.setText(f"Calibration {self.state} • {len(self.samples)} samples in memory • alerts disabled")

    def confirm(self, title, text):
        return QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes |
                                    QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def request_capture(self):
        if self.state in {"delay", "capturing"}:
            return
        if self.loaded_profile:
            self.message("Loaded profile remains available for review. Choose New Session before collecting additional data.")
            return
        d = self.dashboard
        if self.player is not None or d.capture is None or d.pose is None:
            self.message("Start the live camera and pose worker before calibration. No capture started.")
            return
        if d.capture.snapshot().state != "LIVE" or not getattr(d.pose, "ready", False):
            self.message("Wait for live camera and ready pose worker. No capture started.")
            return
        selected = self.candidate.currentData()
        tracks = [t for t in self.last_live_tracks if t.id == selected and not t.identity_uncertain]
        if not self.scene_review.isChecked() or len(tracks) != 1:
            self.message("Review the fixed camera/masks and choose a currently visible, unambiguous person candidate first.")
            return
        if self.samples and selected != self.capture_candidate:
            self.message("This session uses a different person candidate. Save it, then choose New Session before changing candidates.")
            return
        metrics = d.capture.snapshot()
        dimensions = (metrics.actual_width, metrics.actual_height)
        if self.capture_scene is not None and (self.capture_scene != d.settings.scene or
                                               self.capture_dimensions != dimensions or
                                               self.capture_generation != d._capture_generation):
            self.message("Scene or camera session changed. Existing unsaved data retained; save it, then choose New Session before collecting more.")
            return
        step = self.step.currentData()
        if not self.confirm("Approve this feature-only capture?",
                f"{STEPS[step]}\n\nAfter a visible five-second delay, collect up to 15 seconds of local pose coordinates and confidence scores in memory. Stop / Review ends early. No photographs, video or audio are saved.\n\nSaving later requires another confirmation and creates new files under {data_directory() / 'calibration'}. Assisted and caregiver captures remain pending. Proceed only when ready."):
            return
        self.capture_scene = d.settings.scene
        self.capture_dimensions = dimensions
        self.capture_candidate = selected
        self.capture_generation = d._capture_generation
        if self.capture_provenance is None:
            try:
                dependencies = {n: importlib.metadata.version(n) for n in ("mediapipe", "PySide6", "opencv-contrib-python")}
                self.capture_provenance = build_provenance(d.settings.scene, d.model_path,
                    f"camera {d.capture.settings.index} / {d.capture.settings.backend}",
                    dimensions[0], dimensions[1], dependencies)
            except (OSError, ValueError, RuntimeError) as error:
                self.message(f"Capture not started: {error}")
                return
        self.capture_step = step
        d.cancel_edit()
        self.state = "delay"
        self.deadline = self.clock() + 5
        self.step.setEnabled(False)
        self.candidate.setEnabled(False)
        self.message("Capture delay • 5 seconds • Stop / Review cancels. No movement required yet.")

    def tick(self):
        now = self.clock()
        if self.state == "delay":
            if now >= self.deadline:
                self.state = "capturing"
                self.deadline = now + 15
            else:
                self.message(f"Capture delay • {max(1, int(self.deadline - now + 0.999))} seconds • Stop cancels")
        if self.state == "capturing":
            if now >= self.deadline:
                self.stop_capture()
            else:
                self.message(f"CAPTURING FEATURES • {max(1, int(self.deadline - now + 0.999))} seconds remaining • Stop whenever you want • no imagery saved")

    def stop_capture(self, reason=""):
        if self.state in {"delay", "capturing"}:
            self.state = "review"
            self.step.setEnabled(True)
            self.candidate.setEnabled(True)
            self.message(f"Capture stopped. {len(self.samples)} feature samples retained in memory. Review proposals before saving. {reason if isinstance(reason, str) else ''}")

    def observe(self, result, tracks, frame_index, captured_at):
        self.last_live_tracks = tracks
        if self.state not in {"delay", "capturing"}:
            selected = self.candidate.currentData()
            ids = [self.candidate.itemData(i) for i in range(1, self.candidate.count())]
            live = [t.id for t in tracks]
            if ids != live:
                self.candidate.clear()
                self.candidate.addItem("Choose your person candidate", None)
                for t in tracks:
                    self.candidate.addItem(f"P{t.id} • candidate {'uncertain' if t.identity_uncertain else 'visible'}", t.id)
                index = self.candidate.findData(selected)
                self.candidate.setCurrentIndex(max(0, index))
            else:
                for i, t in enumerate(tracks, 1):
                    self.candidate.setItemText(i, f"P{t.id} • candidate {'uncertain' if t.identity_uncertain else 'visible'}")
        self.trajectory.update(tracks, captured_at)
        self.dashboard.preview.trajectory_segments = self.trajectory.segments
        if self.state != "capturing" or self.clock() >= self.deadline:
            return
        # Results captured before the visible delay completed do not qualify.
        if captured_at < self.deadline - 15:
            return
        if self.samples and (captured_at <= self.samples[-1].timestamp or frame_index <= self.samples[-1].frame_index):
            return
        if len(self.samples) >= 18000 or (self.samples and captured_at - self.samples[0].timestamp > 1200):
            self.stop_capture("Session limit reached; save before beginning a new application session.")
            return
        self.samples.append(FeatureSample(captured_at, frame_index, tuple(result.observations), result.timestamp_ms, self.capture_step))
        if self.capture_step not in self.steps_taken:
            self.steps_taken.append(self.capture_step)
        eligible = [t for t in tracks if t.id == self.capture_candidate and not t.identity_uncertain]
        if len(eligible) == 1:
            name = "intentional_lean" if self.capture_step == "intentional_lean" else "safe"
            self.points[name].append(eligible[0].head)

    def ensure_profile(self):
        if self.profile is not None:
            return
        dimensions = self.capture_dimensions
        if dimensions is None or self.capture_scene is None:
            raise ValueError("Capture safe features first; a profile needs scene/model provenance.")
        if not self.samples:
            raise ValueError("No accepted feature samples captured. Check camera/pose health before retrying.")
        self.profile = CalibrationProfile(self.capture_scene, self.capture_provenance,
                      capture_steps=tuple(self.steps_taken))

    def propose(self):
        try:
            if self.state in {"delay", "capturing"}:
                raise ValueError("Stop capture before reviewing zones.")
            self.ensure_profile()
            name = self.zone.currentData()
            if name not in self.points:
                raise ValueError("Only safe/intentional-lean envelopes can be proposed from samples. Danger and entry boundaries require manual review; no thresholds are inferred.")
            margin = self.margin.value() / 100 if name == "intentional_lean" else 0
            zone = propose_zone(self.points[name], margin)
            self.set_zone(name, zone)
            self.message("Observed envelope proposed. Review day-to-day variation and uncertainty; this is not a safety threshold.")
        except (OSError, ValueError, RuntimeError) as error:
            self.message(str(error))

    def draw_zone(self):
        try:
            if self.state in {"delay", "capturing"}:
                raise ValueError("Stop capture before editing zones.")
            self.ensure_profile()
            if not self.profile_matches_view():
                raise ValueError("Profile scene differs from this view; return to its original scene before editing.")
            self.dashboard.begin_edit("zone:" + self.zone.currentData())
        except (OSError, ValueError, RuntimeError) as error:
            self.message(str(error))

    def set_zone(self, name, rect):
        zones = dict(self.profile.zones)
        zones[name] = rect
        reviewed = tuple(n for n in self.profile.reviewed_zones if n != name)
        self.profile = replace(self.profile, zones=zones, reviewed_zones=reviewed,
                               lean_margin=self.margin.value() / 100,
                               capture_steps=tuple(self.steps_taken) or self.profile.capture_steps)
        self.show_zones()

    def margin_changed(self):
        if self.profile is not None:
            self.profile = replace(self.profile, lean_margin=self.margin.value() / 100,
                reviewed_zones=tuple(n for n in self.profile.reviewed_zones if n != "intentional_lean"))
            if self.points["intentional_lean"]:
                try:
                    self.set_zone("intentional_lean", propose_zone(self.points["intentional_lean"], self.margin.value() / 100))
                except ValueError:
                    pass
            self.show_zones()
        self.message("Margin changed. Intentional-lean proposal needs visual review; danger zones were not expanded.")

    def review_zone(self):
        name = self.zone.currentData()
        if self.profile is None or name not in self.profile.zones:
            self.message("Draw or propose the selected zone before reviewing it.")
            return
        if not self.profile_matches_view():
            self.message("Cannot review a zone against a different or unverifiable camera/model/scene.")
            return
        self.profile = replace(self.profile, reviewed_zones=tuple(sorted(set(self.profile.reviewed_zones) | {name})))
        self.show_zones()
        self.message(f"{name.replace('_', ' ')} marked reviewed for visualization. Detection remains disabled; no safety accuracy established.")

    def show_zones(self):
        preview = self.dashboard.preview
        matches = self.profile_matches_view()
        preview.zones = self.profile.zones if matches else {}
        preview.reviewed_zones = set(self.profile.reviewed_zones) if matches else set()
        preview.update()

    def profile_matches_view(self):
        if self.profile is None or self.profile.scene != self.dashboard.preview.scene:
            return False
        camera = self.profile.provenance["camera"]
        digest = self.profile.provenance["model"]["sha256"]
        if self.player is not None:
            provenance = self.replay_sequence.provenance
            return (provenance.get("model_sha256") == digest and
                    provenance.get("frame_width") == camera["frame_width"] and
                    provenance.get("frame_height") == camera["frame_height"])
        d = self.dashboard
        if d.capture is None:
            return False
        metrics = d.capture.snapshot()
        current_digest = (self.loaded_model_hash if self.loaded_profile else
                          (self.capture_provenance or {}).get("model", {}).get("sha256"))
        return (current_digest == digest and camera["source"] ==
                f"camera {d.capture.settings.index} / {d.capture.settings.backend}" and
                metrics.state == "LIVE" and
                metrics.actual_width == camera["frame_width"] and
                metrics.actual_height == camera["frame_height"])

    def request_save(self):
        if self.state in {"delay", "capturing"}:
            self.message("Stop / Review before saving.")
            return
        try:
            self.ensure_profile()
            destination = data_directory() / "calibration"
            if not self.confirm("Save new local calibration files?",
                f"Create a new profile and, if new samples exist, a feature replay under {destination}. Features contain personalized pose coordinates/confidence, not images or audio. Existing files are preserved. Zones retain proposed/reviewed status; no danger detection is enabled. Save?"):
                return
            feature_path = None
            if self.samples and self.saved_sample_count != len(self.samples):
                provenance = {"source_kind": "live_features", "timestamp_basis": "capture_read_completion_monotonic_seconds",
                    "frame_width": self.capture_dimensions[0], "frame_height": self.capture_dimensions[1],
                    "model_name": self.profile.provenance["model"]["name"],
                    "model_sha256": self.profile.provenance["model"]["sha256"], "num_poses": 2,
                    "captured_at_utc": self.capture_provenance["created_at"]}
                feature_path = save_sequence(FeatureSequence(self.capture_scene, provenance, tuple(self.samples)))
                self.saved_sample_count = len(self.samples)
            profile = replace(self.profile, capture_steps=tuple(self.steps_taken) or self.profile.capture_steps)
            path = save_profile(profile)
            self.message(f"New profile saved: {path}\n" + (f"New feature replay: {feature_path}" if feature_path else "Existing files retained."))
        except (OSError, ValueError, RuntimeError) as error:
            self.message(f"Save incomplete; any successfully created files were preserved. {error}")

    def open_profile(self):
        if self.state in {"delay", "capturing"} or self.samples:
            self.message("Existing capture data retained. Open profiles in a new application session to avoid mixing provenance.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open local calibration profile", str(data_directory() / "calibration" / "profiles"), "JSON (*.json)")
        if path:
            try:
                self.profile = load_profile(Path(path))
                self.dashboard.cancel_edit()
                self.loaded_profile = True
                self.loaded_model_hash = None
                if self.dashboard.model_path.is_file():
                    with self.dashboard.model_path.open("rb") as stream:
                        self.loaded_model_hash = hashlib.file_digest(stream, "sha256").hexdigest()
                self.margin.blockSignals(True)
                self.margin.setValue(self.profile.lean_margin * 100)
                self.margin.blockSignals(False)
                self.show_zones()
                self.message("Profile loaded for review. Zones hidden if camera/model/dimensions/scene differ or cannot be verified. Confirm the physical camera remains fixed; danger detection remains disabled.")
            except (OSError, ValueError, RuntimeError) as error:
                self.message(f"Profile not loaded: {error}")

    def open_replay(self):
        if self.state in {"delay", "capturing"}:
            self.message("Stop / Review capture first.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Open approved local feature replay", str(data_directory() / "calibration" / "replays"), "JSON (*.json)")
        if path:
            try:
                self.install_replay(load_sequence(Path(path)))
            except (OSError, ValueError, RuntimeError) as error:
                self.message(f"Replay not loaded: {error}")

    def demo(self):
        if self.state in {"delay", "capturing"}:
            self.message("Stop / Review capture first.")
            return
        samples = []
        for i in range(80):
            observations = () if 30 <= i < 38 else (PoseObservation((0.5 + i * 0.0005, 0.4 + (i % 20) * 0.004), None, 0.85),)
            if i >= 50:
                observations += (PoseObservation((0.25 + (i - 50) * 0.003, 0.5), None, 0.7),)
            samples.append(FeatureSample(i / 10, i, observations))
        self.install_replay(FeatureSequence(SceneConfig(), {"source_kind": "synthetic", "timestamp_basis": "synthetic_seconds"}, tuple(samples)))

    def install_replay(self, sequence):
        self.dashboard.pause_camera()
        self.dashboard.cancel_edit()
        self.replay_sequence = sequence
        self.player = ReplayPlayer(sequence)
        self.reset_replay_view()
        self.dashboard.preview.scene = sequence.scene
        width = sequence.provenance.get("frame_width", 16)
        height = sequence.provenance.get("frame_height", 9)
        self.dashboard.preview.frame_ratio = width / height
        self.dashboard.preview.geometry_available = True
        self.show_zones()
        self.message("FEATURE REPLAY • camera paused • no imagery. Play / Pause or Replay from Beginning. Identity is unvalidated.")
        self.dashboard.health.setText("Feature replay • no camera access • original normalized scene coordinates")
        self.dashboard.pose_status.setText("Replay confidence describes landmark visibility/presence, not safety accuracy.")

    def reset_replay_view(self):
        self.replay_tracker = PersonTracker()
        self.trajectory.clear()
        p = self.dashboard.preview
        p.tracks = []
        p.trajectory_segments = {}
        p.image = None
        p.caption = "FEATURE REPLAY • no camera imagery"
        p.update()

    def toggle_play(self):
        if self.player is None:
            self.message("Open a feature replay or start the synthetic demo first.")
            return
        now = self.clock()
        if self.player.playing:
            self.player.pause(now)
            self.message("Replay paused • Play / Pause resumes")
        else:
            self.player.play(now)
            self.message("Replay playing • camera remains paused")

    def rewind(self):
        if self.player is not None:
            self.player.seek(0, self.clock())
            self.reset_replay_view()
            self.message("Replay reset to beginning; candidate IDs and trajectories reset.")

    def render_replay(self):
        if self.player is None:
            return False
        for sample in self.player.advance(self.clock()):
            tracks = self.replay_tracker.update(sample.observations, sample.timestamp)
            self.trajectory.update(tracks, sample.timestamp)
            self.dashboard.preview.tracks = tracks
        self.dashboard.preview.trajectory_segments = self.trajectory.segments
        self.dashboard.preview.caption = f"FEATURE REPLAY • {self.player.position(self.clock()):.1f}s • no imagery"
        self.dashboard.preview.update()
        return True

    def leave_replay(self):
        self.player = self.replay_sequence = None
        self.dashboard.cancel_edit()
        p = self.dashboard.preview
        p.scene = self.dashboard.settings.scene
        p.image = None
        p.geometry_available = False
        p.tracks = []
        p.caption = "Camera paused • Start / Retry Camera when ready"
        self.trajectory.clear()
        p.trajectory_segments = {}
        self.show_zones()
        self.message("Live view selected. Camera stays paused until Start / Retry Camera.")

    def scene_changed(self):
        self.stop_capture("Scene changed; no further samples collected. Previous data retained.")
        self.scene_review.setChecked(False)
        self.last_live_tracks = []
        self.trajectory.clear()
        self.dashboard.preview.trajectory_segments = {}
        self.show_zones()

    def new_session(self):
        if self.state in {"delay", "capturing"}:
            self.message("Stop / Review capture first.")
            return
        if (self.samples or self.profile is not None) and not self.confirm("Start a new calibration session?",
                "Clear this session's in-memory samples and zone edits? Save them first if needed. All existing saved profile and replay files will be retained; no files are removed or replaced."):
            return
        self.dashboard.cancel_edit()
        self.samples = []
        self.points = {"safe": [], "intentional_lean": []}
        self.steps_taken = []
        self.profile = None
        self.loaded_profile = False
        self.loaded_model_hash = None
        self.capture_scene = self.capture_dimensions = self.capture_provenance = None
        self.capture_candidate = self.capture_generation = self.capture_step = None
        self.saved_sample_count = 0
        self.state = "idle"
        self.scene_review.setChecked(False)
        self.margin.setValue(0)
        self.show_zones()
        self.message("New session ready; saved files retained. Review the fixed camera and masks before collection.")
