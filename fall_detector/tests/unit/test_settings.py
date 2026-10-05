from dataclasses import replace
import pytest

from tyler_safety_monitor.scene import Rect, SceneConfig
from tyler_safety_monitor.settings import AppSettings, load_settings, save_settings


def test_settings_roundtrip_retains_nonsecret_geometry_and_volume():
    settings = AppSettings(backend="msmf", fps=15, alert_volume=0,
                           scene=SceneConfig(Rect(0.1, 0.2, 0.7, 0.6), (Rect(0.3, 0.3, 0.1, 0.1),)))
    assert AppSettings.from_dict(settings.to_dict()) == settings


@pytest.mark.parametrize("patch", [
    {"alert_volume": float("nan")}, {"alert_volume": 1.1}, {"alert_volume": True},
    {"camera_index": True}, {"camera_index": 21}, {"fps": 60}, {"backend": "unknown"},
    {"scene": []}, {"scene": {"roi": {"x": 0, "y": 0, "width": 0, "height": 1}}},
    {"caregiver_number": "redacted"},
])
def test_invalid_or_private_fields_do_not_enter_settings(patch):
    data = AppSettings().to_dict()
    data.update(patch)
    with pytest.raises((ValueError, TypeError)):
        AppSettings.from_dict(data)


def test_saves_append_revisions_without_rewriting_existing_files(tmp_path):
    first_settings = AppSettings(alert_volume=0.2)
    first = save_settings(first_settings, tmp_path)
    first_bytes = first.read_bytes()
    unrelated = tmp_path / "existing-unrelated.txt"
    unrelated.write_text("preserve", encoding="utf-8")
    second_settings = replace(first_settings, alert_volume=0.8)
    second = save_settings(second_settings, tmp_path)
    assert first != second
    assert first.read_bytes() == first_bytes
    assert unrelated.read_text(encoding="utf-8") == "preserve"
    assert len(list(tmp_path.glob("settings-*.json"))) == 2
    loaded, status = load_settings(tmp_path)
    assert loaded == second_settings
    assert "loaded" in status


def test_corrupt_latest_revision_is_visible_and_does_not_silently_restore_old_roi(tmp_path):
    old = save_settings(AppSettings(scene=SceneConfig(Rect(0.2, 0.5, 0.7, 0.4))), tmp_path)
    old_bytes = old.read_bytes()
    newest = tmp_path / "settings-99999999-corrupt.json"
    newest.write_text("{unfinished", encoding="utf-8")
    loaded, status = load_settings(tmp_path)
    assert loaded == AppSettings()
    assert "Settings fault" in status and "Review ROI and exclusions" in status
    assert old.read_bytes() == old_bytes
    assert newest.read_text(encoding="utf-8") == "{unfinished"


def test_latest_oversized_revision_faults_without_modification(tmp_path):
    latest = tmp_path / "settings-99999999-large.json"
    latest.write_text(" " * (128 * 1024 + 1), encoding="utf-8")
    before = latest.stat().st_size
    _, status = load_settings(tmp_path)
    assert "Settings fault" in status and "too large" in status
    assert latest.stat().st_size == before


def test_missing_directory_load_is_read_only(tmp_path):
    directory = tmp_path / "not-created"
    settings, status = load_settings(directory)
    assert settings == AppSettings()
    assert "not been calibrated" in status
    assert not directory.exists()
