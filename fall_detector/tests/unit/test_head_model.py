from pathlib import Path
import io
import hashlib
import pytest
from tyler_safety_monitor import head_model


def fake_model(monkeypatch):
    payload = b"0000TFL3synthetic model bytes"
    monkeypatch.setattr(head_model, "FACE_MODEL_SHA256", hashlib.sha256(payload).hexdigest())
    return payload


def test_verified_existing_model_is_read_only_and_does_not_download(tmp_path, monkeypatch):
    payload = fake_model(monkeypatch)
    target = tmp_path / "blaze_face_full_range_trial.tflite"
    target.write_bytes(payload)
    monkeypatch.setattr(head_model.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network forbidden"))
    assert head_model.prepare_head_model(tmp_path) == target
    assert target.read_bytes() == payload


def test_invalid_existing_model_is_preserved_without_network(tmp_path, monkeypatch):
    target = tmp_path / "blaze_face_full_range_trial.tflite"
    target.write_bytes(b"existing unrelated bytes")
    monkeypatch.setattr(head_model.urllib.request, "urlopen", lambda *a, **k: pytest.fail("network forbidden"))
    with pytest.raises(ValueError): head_model.prepare_head_model(tmp_path)
    assert target.read_bytes() == b"existing unrelated bytes"


def test_explicit_download_validates_before_exclusive_creation(tmp_path, monkeypatch):
    payload = fake_model(monkeypatch)
    seen = []
    def download(url, timeout):
        seen.append((url, timeout))
        return io.BytesIO(payload)
    monkeypatch.setattr(head_model.urllib.request, "urlopen", download)
    assert head_model.prepare_head_model(tmp_path).read_bytes() == payload
    assert seen == [(head_model.FACE_MODEL_URL, 30)]


def test_changed_remote_bytes_create_no_model(tmp_path, monkeypatch):
    monkeypatch.setattr(head_model.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(b"0000TFL3changed bytes"))
    with pytest.raises(ValueError): head_model.prepare_head_model(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_destination_created_during_download_is_never_replaced(tmp_path, monkeypatch):
    payload = fake_model(monkeypatch)
    target = tmp_path / "blaze_face_full_range_trial.tflite"
    def download(*a, **k):
        target.write_bytes(b"another writer's data")
        return io.BytesIO(payload)
    monkeypatch.setattr(head_model.urllib.request, "urlopen", download)
    with pytest.raises(FileExistsError): head_model.prepare_head_model(tmp_path)
    assert target.read_bytes() == b"another writer's data"
