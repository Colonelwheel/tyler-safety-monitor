import json
from tyler_safety_monitor import launch_diagnostics as diagnostic


def test_missing_model_reports_exact_path_and_file_error(tmp_path):
    path = tmp_path / "missing model.task"
    result = diagnostic.probe_path(path)
    assert result["path"] == str(path)
    assert result["error"] == "FileNotFoundError"
    assert result["errno"] == 2


def test_reports_preserve_existing_files_and_exclude_contents(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    runtime = tmp_path / "TylerSafetyMonitor"
    model = runtime / "models" / "pose_landmarker_full.task"
    model.parent.mkdir(parents=True)
    model.write_bytes(b"private synthetic contents")
    config = runtime / "config"
    config.mkdir()
    settings = config / "settings-sentinel.json"
    settings.write_text("private settings contents", encoding="utf-8")
    first = diagnostic.write_startup_diagnostic(model, "model starting")
    before = first.read_bytes()
    second = diagnostic.write_startup_diagnostic(model, "model starting")
    report = json.loads(second.read_text(encoding="utf-8"))
    assert first != second
    assert first.read_bytes() == before
    assert model.read_bytes() == b"private synthetic contents"
    assert settings.read_text(encoding="utf-8") == "private settings contents"
    assert report["model"]["is_file"] and report["model"]["readable"]
    assert report["settings_directory"]["path"] == str(config)
    assert b"private synthetic contents" not in second.read_bytes()
    assert b"private settings contents" not in second.read_bytes()
