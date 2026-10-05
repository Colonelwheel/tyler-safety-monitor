"""Synthetic feature scheduling/validation checks; no cameras, media or models."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

import numpy as np

import pytest

from tyler_safety_monitor.replay import (FeatureSample, FeatureSequence, ReplayPlayer,
                                        TrajectoryHistory, load_sequence, save_sequence)
from tyler_safety_monitor.scene import Rect, SceneConfig
from tyler_safety_monitor.tracking import PersonTracker, PoseObservation


def sequence():
    observation = PoseObservation((.5, .6), None, .9, ((.5, .6, .1),), ((.9, .8),))
    return FeatureSequence(SceneConfig(Rect(.2, .1, .7, .8)),
                           {"source_kind": "synthetic", "timestamp_basis": "source_capture_sidecar"},
                           tuple(FeatureSample(t, i, (observation,), i * 1000, "ordinary")
                                 for i, t in enumerate((100., 101., 103.))))


def test_roundtrip_preserves_source_times_scene_confidence_and_model_time(tmp_path):
    original = sequence()
    saved = save_sequence(original, directory=tmp_path)
    loaded = load_sequence(saved)
    assert loaded == original
    assert loaded.samples[1].timestamp == 101
    assert loaded.samples[1].inference_timestamp_ms == 1000
    assert loaded.scene.roi == original.scene.roi
    assert loaded.samples[0].observations[0].landmark_scores == ((.9, .8),)
    assert loaded.samples[0].capture_step == "ordinary"


def test_saves_create_revisions_and_never_overwrite(tmp_path):
    original = sequence()
    first = save_sequence(original, directory=tmp_path)
    before = first.read_bytes()
    second = save_sequence(original, directory=tmp_path)
    assert first != second
    with pytest.raises(FileExistsError):
        save_sequence(original, path=first)
    assert first.read_bytes() == before


@pytest.mark.parametrize("change", [
    lambda data: data.update(schema_version=True),
    lambda data: data.update(identity="someone"),
    lambda data: data["provenance"].update(caregiver_name="someone"),
    lambda data: data["samples"][1].update(timestamp=100),
    lambda data: data["samples"][1].update(timestamp=float("nan")),
    lambda data: data["samples"][1].update(frame_index=True),
    lambda data: data["samples"][1].update(inference_timestamp_ms=0),
    lambda data: data["samples"][1].update(capture_step="unsafe"),
    lambda data: data["samples"][1].update(capture_step=True),
    lambda data: data["samples"][1]["observations"][0].update(confidence=True),
    lambda data: data["samples"][1]["observations"][0].update(head=[2, .5]),
    lambda data: data.update(samples=[]),
    lambda data: data["provenance"].update(frame_width=100),
    lambda data: data["provenance"].update(frame_width=100, frame_height=0),
    lambda data: data["provenance"].update(frame_width="100", frame_height=100),
    lambda data: data["provenance"].update(frame_width=100, frame_height=32769),
    lambda data: data["provenance"].update(model_sha256="unknown"),
    lambda data: data["provenance"].update(clip_sha256=32),
    lambda data: data["provenance"].update(num_poses=0),
    lambda data: data["provenance"].update(num_poses=17),
    lambda data: data["provenance"].update(num_poses=2.0),
    lambda data: data["provenance"].update(requested_fps=0),
    lambda data: data["provenance"].update(requested_fps="15"),
])
def test_invalid_or_identity_data_is_rejected(change):
    data = sequence().to_dict()
    change(data)
    with pytest.raises(ValueError):
        FeatureSequence.from_dict(data)


def test_loader_rejects_duplicate_fields_and_oversized_file(tmp_path, monkeypatch):
    path = tmp_path / "invalid.json"
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(ValueError):
        load_sequence(path)
    monkeypatch.setattr("tyler_safety_monitor.replay.MAX_BYTES", 4)
    with pytest.raises(ValueError):
        load_sequence(path)


def test_playback_uses_source_spacing_and_pause_does_not_advance():
    player = ReplayPlayer(sequence())
    assert player.advance(10) == ()
    player.play(10)
    assert [s.timestamp for s in player.advance(10)] == [100]
    assert player.advance(10.9) == ()
    player.pause(10.9)
    assert player.advance(20) == ()
    assert player.position(20) == pytest.approx(.9)
    player.play(20)
    assert [s.timestamp for s in player.advance(20.1)] == [101]
    assert [s.timestamp for s in player.advance(22.1)] == [103]
    assert player.finished and not player.playing


def test_seek_reset_and_large_clock_steps_are_deterministic():
    player = ReplayPlayer(sequence())
    player.play(0)
    assert len(player.advance(10)) == 3
    player.seek(1, 10)
    assert not player.finished
    player.play(10)
    assert [s.timestamp for s in player.advance(10)] == [101]
    player.reset(11)
    assert [s.timestamp for s in player.advance(11)] == [100]
    with pytest.raises(ValueError):
        player.advance(10)
    with pytest.raises(ValueError):
        player.seek(4, 11)


def test_trajectory_breaks_for_absence_uncertainty_and_gaps_and_bounds_age():
    tracker = PersonTracker()
    history = TrajectoryHistory(max_age=2, max_points=3, gap_seconds=.5)
    observation = PoseObservation((.5, .6), None, .9)
    track = tracker.update([observation], 1)[0]
    history.update([track], 1)
    history.update([track], 1.1)
    assert len(history.segments[track.id]) == 1
    history.update([], 1.2)
    history.update([track], 1.3)
    assert len(history.segments[track.id]) == 2
    history.update([replace(track, identity_uncertain=True)], 1.4)
    history.update([track], 1.5)
    assert len(history.segments[track.id]) == 3
    assert sum(map(len, history.segments[track.id])) == 3
    history.update([track], 2.2)
    assert len(history.segments[track.id][-1]) == 1
    history.update([], 5)
    assert history.segments == {}
    history.clear()
    history.update([track], 0)
    with pytest.raises(ValueError):
        history.update([track], 0)


def clip_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "replay_clip.py"
    spec = importlib.util.spec_from_file_location("synthetic_replay_clip", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_output_containment_and_sidecar_preserves_irregular_timestamps(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    module = clip_module()
    root = tmp_path / "TylerSafetyMonitor" / "calibration" / "replays"
    assert module.validate_output(root / "new.json") == root / "new.json"
    for path in (tmp_path / "outside.json", root / ".." / "outside.json", root / "clip.mp4"):
        with pytest.raises(ValueError):
            module.validate_output(path)
    sidecar = tmp_path / "timestamps.json"
    sidecar.write_text(json.dumps({"schema_version": 1, "timestamps": [500, 500.1, 500.4]}), encoding="utf-8")
    assert module.load_timestamps(sidecar) == (500, 500.1, 500.4)
    invalid = tmp_path / "invalid-times.json"
    invalid.write_text(json.dumps({"schema_version": 1, "timestamps": [2, 1]}), encoding="utf-8")
    with pytest.raises(ValueError):
        module.load_timestamps(invalid)


def test_provenance_supports_bounded_dependency_versions_but_rejects_identity():
    data = sequence().to_dict()
    data["provenance"].update(capture_step="ordinary_safe_positions", captured_at_utc="2026-10-05T12:00:00Z",
                              dependencies={"python": "3.12.8", "mediapipe": "1.0.1"})
    assert FeatureSequence.from_dict(data).provenance["dependencies"]["python"] == "3.12.8"
    data["provenance"]["dependencies"]["person"] = "someone"
    with pytest.raises(ValueError):
        FeatureSequence.from_dict(data)


def test_old_feature_observations_without_landmark_scores_still_load():
    data = sequence().to_dict()
    for sample in data["samples"]:
        del sample["observations"][0]["landmark_scores"]
        del sample["capture_step"]
    assert FeatureSequence.from_dict(data).samples[0].observations[0].landmark_scores == ()
    assert FeatureSequence.from_dict(data).samples[0].capture_step is None


def test_clip_analysis_orders_every_synthetic_frame_and_preserves_source_times(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("tyler_safety_monitor.pose.isolate_model_cache", lambda: None)
    module = clip_module()
    clip = tmp_path / "synthetic.fake"
    model = tmp_path / "synthetic.task"
    clip.write_bytes(b"unchanged fake clip")
    model.write_bytes(b"fake local model")
    sidecar = tmp_path / "times.json"
    sidecar.write_text(json.dumps({"schema_version": 1, "timestamps": [90, 90.1001, 90.4002]}), encoding="utf-8")
    frames = [np.zeros((6, 8, 3), dtype=np.uint8) for _ in range(3)]
    released, received = [], []

    class Capture:
        def isOpened(self):
            return True

        def get(self, prop):
            return 10 if prop == "fps" else 3

        def read(self):
            return (True, frames.pop(0)) if frames else (False, None)

        def release(self):
            released.append(True)

    class Detector:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def detect_for_video(self, image, timestamp):
            received.append(timestamp)
            landmark = SimpleNamespace(x=.5, y=.5, z=.1, visibility=.9, presence=.8)
            return SimpleNamespace(pose_landmarks=[[landmark] * 33])

    cv2 = SimpleNamespace(VideoCapture=lambda path: Capture(), CAP_PROP_FPS="fps",
                          CAP_PROP_FRAME_COUNT="count", COLOR_BGR2RGB="rgb",
                          cvtColor=lambda frame, mode: frame)
    mediapipe = ModuleType("mediapipe")
    tasks = ModuleType("mediapipe.tasks")
    python = ModuleType("mediapipe.tasks.python")
    python.BaseOptions = lambda **kwargs: SimpleNamespace(**kwargs)
    python.vision = SimpleNamespace(PoseLandmarkerOptions=lambda **kwargs: SimpleNamespace(**kwargs),
                                    RunningMode=SimpleNamespace(VIDEO="VIDEO"),
                                    PoseLandmarker=SimpleNamespace(create_from_options=lambda options: Detector()))
    tasks.python = python
    mediapipe.tasks = tasks
    mediapipe.ImageFormat = SimpleNamespace(SRGB="rgb")
    mediapipe.Image = lambda **kwargs: SimpleNamespace(**kwargs)
    for name, value in (("cv2", cv2), ("mediapipe", mediapipe), ("mediapipe.tasks", tasks),
                        ("mediapipe.tasks.python", python)):
        monkeypatch.setitem(sys.modules, name, value)
    output = tmp_path / "TylerSafetyMonitor" / "calibration" / "replays" / "features.json"
    assert module.analyze_clip(clip, model, output, SceneConfig(Rect(.25, .25, .5, .5)), sidecar) == 3
    result = load_sequence(output)
    assert received == [0, 100, 400]
    assert [sample.timestamp for sample in result.samples] == [90, 90.1001, 90.4002]
    assert [sample.frame_index for sample in result.samples] == [0, 1, 2]
    assert result.samples[0].observations[0].head == (.5, .5)
    assert result.samples[0].observations[0].landmark_scores[0] == (.9, .8)
    assert result.provenance["clip_sha256"] == module.file_digest(clip)
    assert result.provenance["model_name"] == "custom"
    assert result.provenance["dependencies"]["python"]
    assert clip.read_bytes() == b"unchanged fake clip"
    assert released == [True]
