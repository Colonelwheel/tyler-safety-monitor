"""Bounded private feature replay; no risk decisions or confirmed identities."""
from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import re
from pathlib import Path
from uuid import uuid4

from .scene import SceneConfig
from .settings import data_directory
from .tracking import PoseObservation, Track

MAX_BYTES = 32 * 1024 * 1024
MAX_SAMPLES = 18_000
MAX_DURATION = 1_200.0
PROVENANCE_KEYS = {"source_kind", "model_sha256", "model_name", "frame_width",
                   "frame_height", "requested_fps", "timestamp_basis",
                   "scene_generation", "clip_sha256", "profile_id", "num_poses"}
PROVENANCE_KEYS |= {"capture_step", "captured_at_utc", "dependencies"}


def _time(value, name="timestamp") -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number")
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return value


def observation_to_dict(observation: PoseObservation) -> dict:
    return {"head": list(observation.head),
            "shoulders": list(observation.shoulders) if observation.shoulders else None,
            "confidence": observation.confidence,
            "landmarks": [list(point) for point in observation.landmarks],
            "landmark_scores": [list(pair) for pair in observation.landmark_scores]}


def observation_from_dict(data: dict) -> PoseObservation:
    required = {"head", "shoulders", "confidence", "landmarks"}
    if not isinstance(data, dict) or not required <= set(data) or set(data) - (required | {"landmark_scores"}):
        raise ValueError("invalid observation fields")
    if not isinstance(data["landmarks"], list) or len(data["landmarks"]) > 33:
        raise ValueError("landmarks must be a bounded list")
    for point in [data["head"], data["shoulders"], *data["landmarks"]]:
        if point is not None and (not isinstance(point, (list, tuple))
                                  or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in point)):
            raise ValueError("invalid observation coordinates")
    if isinstance(data["confidence"], bool) or not isinstance(data["confidence"], (int, float)):
        raise ValueError("invalid observation confidence")
    scores = data.get("landmark_scores", [])
    if (not isinstance(scores, list) or len(scores) > 33
            or any(not isinstance(pair, (list, tuple)) or len(pair) != 2
                   or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in pair)
                   for pair in scores)):
        raise ValueError("invalid landmark scores")
    return PoseObservation(data["head"], data["shoulders"], data["confidence"], data["landmarks"], scores)


@dataclass(frozen=True)
class FeatureSample:
    timestamp: float
    frame_index: int
    observations: tuple[PoseObservation, ...]
    inference_timestamp_ms: int | None = None
    capture_step: str | None = None

    def __post_init__(self):
        object.__setattr__(self, "timestamp", _time(self.timestamp))
        if type(self.frame_index) is not int or not 0 <= self.frame_index < 2**53:
            raise ValueError("frame index must be a nonnegative integer")
        observations = tuple(self.observations)
        if len(observations) > 16 or any(not isinstance(o, PoseObservation) or len(o.landmarks) > 33 for o in observations):
            raise ValueError("invalid or excessive observations")
        object.__setattr__(self, "observations", observations)
        if self.inference_timestamp_ms is not None and (type(self.inference_timestamp_ms) is not int
                                                       or not 0 <= self.inference_timestamp_ms < 2**53):
            raise ValueError("invalid inference timestamp")
        if self.capture_step is not None and (not isinstance(self.capture_step, str)
                or self.capture_step not in {"ordinary", "adjustments", "intentional_lean", "darkest"}):
            raise ValueError("unsupported safe capture step")

    def to_dict(self):
        return {"timestamp": self.timestamp, "frame_index": self.frame_index,
                "inference_timestamp_ms": self.inference_timestamp_ms,
                "capture_step": self.capture_step,
                "observations": [observation_to_dict(o) for o in self.observations]}

    @classmethod
    def from_dict(cls, data):
        allowed = {"timestamp", "frame_index", "observations", "inference_timestamp_ms", "capture_step"}
        if not isinstance(data, dict) or set(data) - allowed or not {"timestamp", "frame_index", "observations"} <= set(data):
            raise ValueError("invalid sample fields")
        if not isinstance(data["observations"], list) or len(data["observations"]) > 16:
            raise ValueError("observations must be a bounded list")
        return cls(data["timestamp"], data["frame_index"],
                   tuple(observation_from_dict(o) for o in data["observations"]),
                   data.get("inference_timestamp_ms"), data.get("capture_step"))


@dataclass(frozen=True)
class FeatureSequence:
    scene: SceneConfig
    provenance: dict
    samples: tuple[FeatureSample, ...]

    def __post_init__(self):
        if not isinstance(self.scene, SceneConfig) or len(self.scene.exclusions) > 64:
            raise ValueError("invalid scene")
        if not isinstance(self.provenance, dict) or set(self.provenance) - PROVENANCE_KEYS:
            raise ValueError("unsupported provenance fields; identity metadata is not accepted")
        for key, value in self.provenance.items():
            if key == "dependencies":
                if (not isinstance(value, dict) or set(value) - {"python", "mediapipe", "opencv", "numpy", "pyside6"}
                        or any(not isinstance(v, str) or len(v) > 64 for v in value.values())):
                    raise ValueError("invalid dependency provenance")
                continue
            if (isinstance(value, bool) or not isinstance(value, (str, int, float))
                    or isinstance(value, str) and len(value) > 256
                    or isinstance(value, (int, float)) and not math.isfinite(value)):
                raise ValueError("invalid provenance value")
        dimensions = {"frame_width", "frame_height"} & set(self.provenance)
        if dimensions and dimensions != {"frame_width", "frame_height"}:
            raise ValueError("frame dimensions must be provided together")
        if any(type(self.provenance[key]) is not int or not 1 <= self.provenance[key] <= 32768
               for key in dimensions):
            raise ValueError("frame dimensions must be bounded positive integers")
        for key in ("model_sha256", "clip_sha256"):
            if key in self.provenance and (not isinstance(self.provenance[key], str)
                    or re.fullmatch(r"[0-9a-fA-F]{64}", self.provenance[key]) is None):
                raise ValueError("provenance hashes must contain 64 hexadecimal characters")
        if "num_poses" in self.provenance and (type(self.provenance["num_poses"]) is not int
                or not 1 <= self.provenance["num_poses"] <= 16):
            raise ValueError("pose capacity must be a bounded positive integer")
        if "requested_fps" in self.provenance and (not isinstance(self.provenance["requested_fps"], (int, float))
                or self.provenance["requested_fps"] <= 0):
            raise ValueError("frame rate must be finite and positive")
        object.__setattr__(self, "provenance", dict(self.provenance))
        samples = tuple(self.samples)
        if not 1 <= len(samples) <= MAX_SAMPLES or any(not isinstance(s, FeatureSample) for s in samples):
            raise ValueError("sequence requires a bounded nonempty sample list")
        for before, after in zip(samples, samples[1:]):
            if after.timestamp <= before.timestamp or after.frame_index <= before.frame_index:
                raise ValueError("sample timestamps and frame indices must increase strictly")
            if (before.inference_timestamp_ms is not None and after.inference_timestamp_ms is not None
                    and after.inference_timestamp_ms <= before.inference_timestamp_ms):
                raise ValueError("inference timestamps must increase strictly")
        if samples[-1].timestamp - samples[0].timestamp > MAX_DURATION:
            raise ValueError("feature sequence exceeds duration limit")
        object.__setattr__(self, "samples", samples)

    @property
    def duration(self):
        return self.samples[-1].timestamp - self.samples[0].timestamp

    def to_dict(self):
        return {"schema_version": 1, "scene": self.scene.to_dict(),
                "provenance": dict(self.provenance), "samples": [s.to_dict() for s in self.samples]}

    @classmethod
    def from_dict(cls, data):
        if (not isinstance(data, dict) or set(data) != {"schema_version", "scene", "provenance", "samples"}
                or type(data["schema_version"]) is not int or data["schema_version"] != 1):
            raise ValueError("unsupported feature sequence schema")
        if not isinstance(data["samples"], list) or not 1 <= len(data["samples"]) <= MAX_SAMPLES:
            raise ValueError("invalid sample count")
        return cls(SceneConfig.from_dict(data["scene"]), data["provenance"],
                   tuple(FeatureSample.from_dict(s) for s in data["samples"]))


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON fields")
        result[key] = value
    return result


def load_feature_sequence(path: Path | str) -> FeatureSequence:
    with Path(path).open("rb") as stream:
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("feature file exceeds size limit")
    try:
        return FeatureSequence.from_dict(json.loads(payload, object_pairs_hook=_unique_keys))
    except (TypeError, OverflowError, RecursionError, UnicodeError) as error:
        raise ValueError("invalid feature data") from error


def save_feature_sequence(sequence: FeatureSequence, path: Path | str | None = None,
                          directory: Path | None = None) -> Path:
    """Create exclusively, retaining every earlier revision and partial failure."""
    # Revalidate mutable provenance before writing anything.
    validated = FeatureSequence.from_dict(sequence.to_dict())
    payload = (json.dumps(validated.to_dict(), allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    if len(payload) > MAX_BYTES:
        raise ValueError("feature file exceeds size limit")
    if path is None:
        directory = directory if directory is not None else data_directory() / "calibration" / "replays"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        path = directory / f"features-{stamp}-{uuid4().hex}.json"
    target = Path(path)
    if target.exists():
        raise FileExistsError("feature destination already exists; existing data preserved")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as stream:
        stream.write(payload)
    return target


# Short names used by the calibration/dashboard integration.
load_sequence = load_feature_sequence
save_sequence = save_feature_sequence


class ReplayPlayer:
    """Playback scheduling uses a supplied clock; sample source times stay intact."""
    def __init__(self, sequence: FeatureSequence):
        self.sequence = sequence
        self._times = [s.timestamp - sequence.samples[0].timestamp for s in sequence.samples]
        self._position = 0.0
        self._anchor = None
        self._index = 0
        self._last_clock = None

    @property
    def finished(self):
        return self._index == len(self.sequence.samples)

    @property
    def playing(self):
        return self._anchor is not None

    def _clock(self, now):
        now = _time(now, "playback clock")
        if self._last_clock is not None and now < self._last_clock:
            raise ValueError("playback clock must not regress")
        self._last_clock = now
        return now

    def position(self, now):
        now = self._clock(now)
        elapsed = 0 if self._anchor is None else now - self._anchor
        return min(self.sequence.duration, self._position + elapsed)

    def play(self, now):
        now = self._clock(now)
        if self._anchor is None and not self.finished:
            self._anchor = now

    def pause(self, now):
        self._position = self.position(now)
        self._anchor = None

    def seek(self, seconds, now):
        seconds = _time(seconds, "seek position")
        if seconds > self.sequence.duration:
            raise ValueError("seek exceeds sequence duration")
        now = self._clock(now)
        playing = self.playing
        self._position = seconds
        self._anchor = now if playing else None
        self._index = bisect_left(self._times, seconds)

    def reset(self, now):
        self.seek(0, now)

    def advance(self, now):
        position = self.position(now)
        if not self.playing:
            return ()
        start = self._index
        while self._index < len(self._times) and self._times[self._index] <= position:
            self._index += 1
        if self.finished:
            self._position = self.sequence.duration
            self._anchor = None
        return self.sequence.samples[start:self._index]


class TrajectoryHistory:
    """Bounded paths with explicit breaks for gaps, absence, and ambiguity."""
    def __init__(self, max_age: float = 30, max_points: int = 450, gap_seconds: float = .5):
        self.max_age = _time(max_age, "history age")
        self.gap_seconds = _time(gap_seconds, "gap limit")
        if self.max_age <= 0 or self.gap_seconds <= 0 or type(max_points) is not int or not 1 <= max_points <= 10_000:
            raise ValueError("invalid trajectory bounds")
        self.max_points = max_points
        self.clear()

    def clear(self):
        self._paths = {}
        self._visible = set()
        self._last = None

    @property
    def segments(self):
        return {id_: [[point for _, point in segment] for segment in paths]
                for id_, paths in self._paths.items()}

    def update(self, tracks, timestamp):
        timestamp = _time(timestamp)
        if self._last is not None and timestamp <= self._last:
            raise ValueError("trajectory timestamps must increase strictly")
        tracks = tuple(tracks)
        if len(tracks) > 16 or any(not isinstance(t, Track) for t in tracks) or len({t.id for t in tracks}) != len(tracks):
            raise ValueError("invalid trajectory tracks")
        for track in tracks:
            if type(track.id) is not int or track.id < 1:
                raise ValueError("invalid candidate identifier")
            PoseObservation(track.head, None, track.confidence)
        gap = self._last is not None and timestamp - self._last > self.gap_seconds
        visible = set()
        for track in tracks:
            if track.identity_uncertain:
                continue
            visible.add(track.id)
            paths = self._paths.setdefault(track.id, [])
            if track.id not in self._visible or gap or not paths:
                paths.append([])
            paths[-1].append((timestamp, track.head))
        cutoff = timestamp - self.max_age
        for id_ in list(self._paths):
            paths = [[p for p in path if p[0] >= cutoff] for path in self._paths[id_]]
            paths = [path for path in paths if path]
            remaining = self.max_points
            kept = []
            for path in reversed(paths):
                if remaining <= 0:
                    break
                kept.append(path[-remaining:])
                remaining -= len(kept[-1])
            if kept:
                self._paths[id_] = list(reversed(kept))
            else:
                del self._paths[id_]
        # Bound IDs as well as points, retaining the most recently observed paths.
        if len(self._paths) > 16:
            keep = sorted(self._paths, key=lambda i: self._paths[i][-1][-1][0], reverse=True)[:16]
            self._paths = {i: self._paths[i] for i in keep}
        self._visible = visible
        self._last = timestamp
