from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace

import pytest

from tyler_safety_monitor import calibration
from tyler_safety_monitor.calibration import (
    CalibrationProfile, build_provenance, load_profile, propose_zone,
    save_profile, scene_digest,
)
from tyler_safety_monitor.scene import Rect, SceneConfig


def profile():
    scene = SceneConfig(Rect(0.1, 0.1, 0.8, 0.8), (Rect(0.7, 0.1, 0.1, 0.2),))
    provenance = {
        "created_at": "2026-10-05T12:00:00+00:00",
        "scene_sha256": scene_digest(scene),
        "model": {"name": "synthetic.task", "sha256": "a" * 64},
        "camera": {"source": "synthetic", "frame_width": 1920, "frame_height": 1080},
        "dependencies": {"synthetic": "1.0"},
    }
    return CalibrationProfile(scene, provenance,
                              {"safe": Rect(0.3, 0.4, 0.1, 0.1),
                               "intentional_lean": Rect(0.3, 0.5, 0.15, 0.15)},
                              ("safe",), 0.005, ("ordinary", "intentional_lean"))


def test_profile_roundtrip_keeps_review_separate_from_proposals():
    original = profile()
    data = original.to_dict()
    assert CalibrationProfile.from_dict(data) == original
    assert data["zones"]["safe"]["status"] == "reviewed"
    assert data["zones"]["intentional_lean"]["status"] == "proposed"
    assert "soft_boundary" not in data["zones"]
    assert "hard_boundary" not in data["zones"]


def test_empty_profile_has_no_inferred_zones_or_margin():
    original = profile()
    empty = CalibrationProfile(original.scene, original.provenance)
    assert empty.zones == {} and empty.reviewed_zones == ()
    assert empty.lean_margin == 0 and empty.capture_steps == ()


@pytest.mark.parametrize("patch", [
    {"schema_version": True}, {"schema_version": 2}, {"schema_version": 1.0},
    {"threshold": 0.5}, {"lean_margin": float("nan")}, {"lean_margin": True},
    {"lean_margin": 0.02001}, {"lean_margin": -0.0001},
    {"capture_steps": "ordinary"}, {"capture_steps": ["ordinary", "ordinary"]},
    {"capture_steps": ["caregiver_complete"]}, {"zones": []},
    {"zones": {"unknown": {"rect": Rect(0, 0, 1, 1).to_dict(), "status": "reviewed"}}},
    {"zones": {"safe": {"rect": Rect(0, 0, 1, 1).to_dict(), "status": "approved"}}},
    {"zones": {"safe": {"rect": {"x": 0, "y": 0, "width": 0, "height": 1}, "status": "reviewed"}}},
    {"scene": {}}, {"scene": {"roi": Rect(0, 0, 1, 1).to_dict(), "exclusions": [], "extra": True}},
])
def test_profile_rejects_invalid_or_extra_fields(patch):
    data = profile().to_dict()
    data.update(patch)
    with pytest.raises(ValueError):
        CalibrationProfile.from_dict(data)


@pytest.mark.parametrize("section,patch", [
    (None, {"created_at": "2026-10-05T12:00:00"}),
    (None, {"created_at": "nonsense"}),
    (None, {"scene_sha256": "b" * 64}),
    (None, {"phone_number": "private"}),
    (None, {"dependencies": {}}),
    (None, {"dependencies": {"synthetic": True}}),
    ("model", {"sha256": "x" * 64}),
    ("model", {"name": ""}),
    ("model", {"path": "extra"}),
    ("camera", {"frame_width": 0}),
    ("camera", {"frame_width": True}),
    ("camera", {"frame_height": 32769}),
    ("camera", {"source": ""}),
])
def test_provenance_requires_valid_timestamp_geometry_model_camera_dependencies(section, patch):
    data = profile().to_dict()
    target = data["provenance"] if section is None else data["provenance"][section]
    target.update(patch)
    with pytest.raises(ValueError):
        CalibrationProfile.from_dict(data)


def test_missing_required_fields_are_not_silently_defaulted():
    data = profile().to_dict()
    for field in data:
        incomplete = deepcopy(data)
        del incomplete[field]
        with pytest.raises(ValueError):
            CalibrationProfile.from_dict(incomplete)


def test_reviewed_zone_must_exist_and_be_unique():
    original = profile()
    for reviewed in (("hard_boundary",), ("safe", "safe"), (True,), "safe"):
        with pytest.raises(ValueError):
            replace(original, reviewed_zones=reviewed)


def test_inputs_and_serialized_data_do_not_share_mutable_provenance():
    original = profile()
    input_provenance = deepcopy(original.provenance)
    copied = CalibrationProfile(original.scene, input_provenance)
    input_provenance["camera"]["source"] = "changed"
    assert copied.provenance["camera"]["source"] == "synthetic"
    output = copied.to_dict()
    output["provenance"]["model"]["name"] = "changed"
    assert copied.provenance["model"]["name"] == "synthetic.task"


def test_mutation_is_revalidated_before_creating_files(tmp_path):
    original = profile()
    original.provenance["model"]["sha256"] = "invalid"
    directory = tmp_path / "should-not-exist"
    with pytest.raises(ValueError):
        save_profile(original, directory)
    assert not directory.exists()


def test_append_only_saves_preserve_previous_and_unrelated_files(tmp_path):
    original = profile()
    first = save_profile(original, tmp_path)
    first_bytes = first.read_bytes()
    unrelated = tmp_path / "preserve.txt"
    unrelated.write_text("keep", encoding="utf-8")
    second = save_profile(replace(original, lean_margin=0.01), tmp_path)
    assert first != second
    assert first.read_bytes() == first_bytes
    assert unrelated.read_text(encoding="utf-8") == "keep"
    assert load_profile(first) == original
    assert load_profile(second).lean_margin == 0.01


def test_revision_collision_fails_without_overwriting(tmp_path, monkeypatch):
    class FixedDateTime(datetime):
        @staticmethod
        def now(tz):
            return datetime(2026, 10, 5, tzinfo=timezone.utc)
    monkeypatch.setattr(calibration, "datetime", FixedDateTime)
    monkeypatch.setattr(calibration, "uuid4", lambda: SimpleNamespace(hex="fixed"))
    first = save_profile(profile(), tmp_path)
    content = first.read_bytes()
    with pytest.raises(FileExistsError):
        save_profile(profile(), tmp_path)
    assert first.read_bytes() == content


@pytest.mark.parametrize("content", [
    b"{unfinished", b"\xff", b"{}", b'{"schema_version":1,"schema_version":1}',
    b" " * (calibration.MAX_PROFILE_BYTES + 1),
], ids=["unfinished", "bad-encoding", "empty-object", "duplicate-fields", "oversized"])
def test_corrupt_profile_is_rejected_without_rewriting(content, tmp_path):
    path = tmp_path / "bad.json"
    path.write_bytes(content)
    with pytest.raises(ValueError):
        load_profile(path)
    assert path.read_bytes() == content


def test_excessive_json_nesting_becomes_a_visible_validation_error(tmp_path):
    path = tmp_path / "deep.json"
    content = b"[" * 2000 + b"0" + b"]" * 2000
    path.write_bytes(content)
    with pytest.raises(ValueError, match="invalid calibration"):
        load_profile(path)
    assert path.read_bytes() == content


@pytest.mark.parametrize("path", [None, [], {}, True])
def test_wrong_path_types_are_validation_errors(path):
    with pytest.raises(ValueError, match="invalid calibration"):
        load_profile(path)


@pytest.mark.parametrize("scene", [
    None, [], "invalid", {"roi": None, "exclusions": []},
    {"roi": Rect(0, 0, 1, 1).to_dict(), "exclusions": None},
    {"roi": Rect(0, 0, 1, 1).to_dict(), "exclusions": [[]]},
])
def test_wrong_scene_types_load_as_validation_errors(scene, tmp_path):
    data = profile().to_dict()
    data["scene"] = scene
    path = tmp_path / "bad-scene.json"
    content = json.dumps(data).encode("utf-8")
    path.write_bytes(content)
    with pytest.raises(ValueError):
        load_profile(path)
    assert path.read_bytes() == content


@pytest.mark.parametrize("error", [TypeError, RecursionError, OverflowError])
def test_unexpected_schema_type_errors_are_normalized(error, tmp_path, monkeypatch):
    path = save_profile(profile(), tmp_path)
    content = path.read_bytes()

    def invalid_schema(cls, data):
        raise error("malformed input")

    monkeypatch.setattr(CalibrationProfile, "from_dict", classmethod(invalid_schema))
    with pytest.raises(ValueError, match="invalid calibration JSON or schema"):
        load_profile(path)
    assert path.read_bytes() == content


def test_model_provenance_is_read_only_and_records_only_basename(tmp_path):
    model = tmp_path / "synthetic.task"
    model.write_bytes(b"synthetic model input")
    original = profile()
    result = build_provenance(original.scene, model, "synthetic", 1920, 1080, {"test": "1"})
    assert result["model"] == {"name": model.name, "sha256": hashlib.sha256(model.read_bytes()).hexdigest()}
    assert result["scene_sha256"] == scene_digest(original.scene)
    assert list(tmp_path.iterdir()) == [model]


def test_proposal_bounds_union_of_samples_with_explicit_small_margin():
    points = [(0.3, 0.4), (0.4, 0.5), (0.35, 0.52)]
    zero = propose_zone(points)
    assert zero.x == 0.3 and zero.y == 0.4
    assert zero.width == pytest.approx(0.1) and zero.height == pytest.approx(0.12)
    expanded = propose_zone(points, 0.005)
    assert expanded.x == pytest.approx(0.295)
    assert expanded.y == pytest.approx(0.395)
    assert expanded.width == pytest.approx(0.11)
    assert expanded.height == pytest.approx(0.13)
    assert all(expanded.contains(*point) for point in points)


def test_proposal_clamps_margin_to_original_frame():
    assert propose_zone([(0, 0), (1, 1)], 0.02) == Rect(0, 0, 1, 1)
    assert propose_zone([(0, 0)], 0.01) == Rect(0, 0, 0.01, 0.01)


@pytest.mark.parametrize("points,margin", [
    ([], 0), ([(0.5, 0.5)], 0), ([(0.5, 0.1), (0.5, 0.2)], 0),
    ([(float("nan"), 0.2)], 0.01), ([(0.2, float("inf"))], 0.01),
    ([(True, 0.2)], 0.01), ([(0.2, 1.1)], 0.01), ([(0.2, -0.1)], 0.01),
    ([(0.2, 0.2, 0.2)], 0), ([(0.2, 0.2)], 0.03), ([(0.2, 0.2)], True),
])
def test_insufficient_or_invalid_observations_are_visible_errors(points, margin):
    with pytest.raises(ValueError):
        propose_zone(points, margin)
