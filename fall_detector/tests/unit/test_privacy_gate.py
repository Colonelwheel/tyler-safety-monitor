import importlib.util
from pathlib import Path


script = Path(__file__).resolve().parents[2] / "scripts" / "check_staged.py"
spec = importlib.util.spec_from_file_location("staged_privacy_gate", script)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def test_private_media_environment_and_runtime_configuration_are_blocked():
    for path in ("fall_detector/sample.jpg", "fall_detector/.env",
                 "fall_detector/config.local.json", "fall_detector/calibration/profile.txt",
                 "fall_detector/models/model.task", "fall_detector/events/event.mp4"):
        assert gate.issues_for(path, b"synthetic")


def test_source_and_redacted_example_are_allowed():
    assert gate.issues_for("fall_detector/src/example.py", b"print('example')") == []
    assert gate.issues_for("fall_detector/config.example.json", b'{"schema_version":1}') == []


def test_credentials_block_without_echoing_matched_value():
    synthetic = "SK" + "a" * 32
    findings = gate.issues_for("fall_detector/example.txt", synthetic.encode())
    assert findings == ["credential identifier"]
    assert synthetic not in str(findings)


def test_binary_artifact_is_blocked():
    assert gate.issues_for("fall_detector/unknown.data", b"text\0binary")
