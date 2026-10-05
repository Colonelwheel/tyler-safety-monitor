"""Reviewed local calibration geometry, without danger inference or recording.

Profiles are explicit new revisions. Importing this module creates no files;
saving requires a caller-approved action. Proposed zones only bound observations
and never establish a safe posture, a danger boundary, or a detection threshold.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence
from uuid import uuid4

from .scene import Rect, SceneConfig
from .settings import data_directory


ZONE_NAMES = (
    "safe", "intentional_lean", "soft_boundary", "hard_boundary",
    "expected_person", "caregiver_entry",
)
MAX_LEAN_MARGIN = 0.02
MAX_PROFILE_BYTES = 128 * 1024
CAPTURE_STEPS = ("ordinary", "adjustments", "intentional_lean", "darkest")
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def _text(value: object, name: str, limit: int = 128) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be nonempty text of at most {limit} characters")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{name} contains control characters")
    return value


def _margin(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("lean margin must be a finite number")
    if not math.isfinite(value) or not 0 <= value <= MAX_LEAN_MARGIN:
        raise ValueError("lean margin must be between 0 and 0.02 of the original frame")
    return float(value)


def scene_digest(scene: SceneConfig) -> str:
    if not isinstance(scene, SceneConfig):
        raise ValueError("scene must be a SceneConfig")
    content = json.dumps(scene.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _provenance(value: object, scene: SceneConfig) -> dict:
    required = {"created_at", "scene_sha256", "model", "camera", "dependencies"}
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError("provenance requires timestamp, scene, model, camera, and dependencies")
    stamp = _text(value["created_at"], "created_at", 64)
    try:
        parsed = datetime.fromisoformat(stamp)
    except ValueError as error:
        raise ValueError("created_at must be an ISO8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("created_at must include a timezone")
    if value["scene_sha256"] != scene_digest(scene):
        raise ValueError("scene provenance does not match profile geometry")
    model = value["model"]
    if not isinstance(model, dict) or set(model) != {"name", "sha256"}:
        raise ValueError("model provenance requires name and sha256")
    _text(model["name"], "model name")
    if not isinstance(model["sha256"], str) or not _DIGEST.fullmatch(model["sha256"]):
        raise ValueError("model sha256 must contain 64 lowercase hexadecimal characters")
    camera = value["camera"]
    if not isinstance(camera, dict) or set(camera) != {"source", "frame_width", "frame_height"}:
        raise ValueError("camera provenance requires source and frame dimensions")
    _text(camera["source"], "camera source")
    for key in ("frame_width", "frame_height"):
        if type(camera[key]) is not int or not 1 <= camera[key] <= 32768:
            raise ValueError("frame dimensions must be positive integers at most 32768")
    dependencies = value["dependencies"]
    if not isinstance(dependencies, dict) or not dependencies or len(dependencies) > 64:
        raise ValueError("dependency provenance must contain 1 to 64 versions")
    for name, version in dependencies.items():
        _text(name, "dependency name", 64)
        _text(version, "dependency version", 64)
    return deepcopy(value)


def build_provenance(
    scene: SceneConfig, model_path: Path, camera_source: str,
    frame_width: int, frame_height: int, dependencies: Mapping[str, str],
) -> dict:
    """Read model bytes for a digest; never import models or write a cache."""
    model_path = Path(model_path)
    with model_path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scene_sha256": scene_digest(scene),
        "model": {"name": model_path.name, "sha256": digest},
        "camera": {"source": camera_source, "frame_width": frame_width, "frame_height": frame_height},
        "dependencies": dict(dependencies),
    }
    return _provenance(result, scene)


@dataclass(frozen=True)
class CalibrationProfile:
    scene: SceneConfig
    provenance: dict
    zones: dict[str, Rect] = field(default_factory=dict)
    reviewed_zones: tuple[str, ...] = ()
    lean_margin: float = 0.0
    capture_steps: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scene, SceneConfig):
            raise ValueError("calibration scene must be a SceneConfig")
        object.__setattr__(self, "provenance", _provenance(self.provenance, self.scene))
        if not isinstance(self.zones, dict) or set(self.zones) - set(ZONE_NAMES):
            raise ValueError("unknown calibration zone names")
        if any(not isinstance(rect, Rect) for rect in self.zones.values()):
            raise ValueError("calibration zones must be normalized Rect values")
        object.__setattr__(self, "zones", dict(self.zones))
        if not isinstance(self.reviewed_zones, (tuple, list)):
            raise ValueError("reviewed_zones must be a sequence")
        reviewed = tuple(self.reviewed_zones)
        if any(not isinstance(name, str) for name in reviewed):
            raise ValueError("reviewed zone names must be text")
        if len(set(reviewed)) != len(reviewed) or set(reviewed) - set(self.zones):
            raise ValueError("reviewed zones must be unique existing zones")
        object.__setattr__(self, "reviewed_zones", reviewed)
        object.__setattr__(self, "lean_margin", _margin(self.lean_margin))
        if not isinstance(self.capture_steps, (tuple, list)) or len(self.capture_steps) > 64:
            raise ValueError("capture_steps must be a sequence of at most 64 steps")
        steps = tuple(_text(step, "capture step", 64) for step in self.capture_steps)
        if len(set(steps)) != len(steps) or set(steps) - set(CAPTURE_STEPS):
            raise ValueError("capture steps must be unique supported steps")
        object.__setattr__(self, "capture_steps", steps)

    def to_dict(self) -> dict:
        # Frozen dataclasses do not freeze contained dictionaries. Revalidate
        # before saving so a caller's mutated data cannot bypass the schema.
        validated = CalibrationProfile(
            self.scene, self.provenance, self.zones, self.reviewed_zones,
            self.lean_margin, self.capture_steps,
        )
        return {
            "schema_version": 1,
            "scene": validated.scene.to_dict(),
            "provenance": deepcopy(validated.provenance),
            "zones": {name: {"rect": rect.to_dict(),
                              "status": "reviewed" if name in validated.reviewed_zones else "proposed"}
                      for name, rect in validated.zones.items()},
            "lean_margin": validated.lean_margin,
            "capture_steps": list(validated.capture_steps),
        }

    @classmethod
    def from_dict(cls, data: object) -> CalibrationProfile:
        required = {"schema_version", "scene", "provenance", "zones", "lean_margin", "capture_steps"}
        if not isinstance(data, dict) or set(data) != required:
            raise ValueError("invalid calibration profile fields")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError("unsupported calibration schema")
        if not isinstance(data["scene"], dict) or set(data["scene"]) != {"roi", "exclusions"}:
            raise ValueError("profile scene requires roi and exclusions")
        scene = SceneConfig.from_dict(data["scene"])
        if not isinstance(data["zones"], dict):
            raise ValueError("zones must be an object")
        zones = {}
        reviewed = []
        for name, zone in data["zones"].items():
            if not isinstance(zone, dict) or set(zone) != {"rect", "status"}:
                raise ValueError("each zone requires rect and status")
            if zone["status"] not in ("proposed", "reviewed"):
                raise ValueError("zone status must be proposed or reviewed")
            zones[name] = Rect.from_dict(zone["rect"])
            if zone["status"] == "reviewed":
                reviewed.append(name)
        return cls(scene, data["provenance"], zones, tuple(reviewed),
                   data["lean_margin"], data["capture_steps"])


def save_profile(profile: CalibrationProfile, directory: Path | None = None) -> Path:
    """Create a new revision only; preserve unrelated and previous files."""
    if not isinstance(profile, CalibrationProfile):
        raise ValueError("a CalibrationProfile is required")
    serialized = json.dumps(profile.to_dict(), indent=2, allow_nan=False) + "\n"
    if len(serialized.encode("utf-8")) > MAX_PROFILE_BYTES:
        raise ValueError("calibration profile is too large")
    directory = Path(directory) if directory is not None else data_directory() / "calibration" / "profiles"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"profile-{stamp}-{uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    return path


def _unique_keys(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON fields are invalid")
        result[key] = value
    return result


def load_profile(path: Path) -> CalibrationProfile:
    """Read a selected revision, raising a visible fault on corrupt data."""
    try:
        with Path(path).open("rb") as stream:
            content = stream.read(MAX_PROFILE_BYTES + 1)
        if len(content) > MAX_PROFILE_BYTES:
            raise ValueError("calibration profile is too large")
        data = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_keys)
        return CalibrationProfile.from_dict(data)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, RecursionError, OverflowError) as error:
        raise ValueError("invalid calibration JSON or schema") from error


def propose_zone(points: Iterable[Sequence[float]], margin: float = 0) -> Rect:
    """Bound observed positions with a small explicit, reviewable image margin.

    Coordinates and margin are fractions of the original frame, not inches or
    anatomical distances. No margin is assumed by default. An empty or flat
    observation without margin cannot define a nonempty zone and is rejected.
    This helper does not propose soft/hard danger boundaries.
    """
    margin = _margin(margin)
    coordinates = []
    for point in points:
        if not isinstance(point, (tuple, list)) or len(point) != 2:
            raise ValueError("each observation must contain two normalized coordinates")
        for value in point:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("observation coordinates must be finite numbers")
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("observation coordinates must be inside [0, 1]")
        coordinates.append((float(point[0]), float(point[1])))
    if not coordinates:
        raise ValueError("observations are required to propose a zone")
    xs, ys = zip(*coordinates)
    left, top = max(0, min(xs) - margin), max(0, min(ys) - margin)
    right, bottom = min(1, max(xs) + margin), min(1, max(ys) + margin)
    if left >= right or top >= bottom:
        raise ValueError("observations have insufficient spread; review geometry manually")
    return Rect(left, top, right - left, bottom - top)
