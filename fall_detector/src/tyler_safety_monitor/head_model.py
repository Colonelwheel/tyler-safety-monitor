"""Explicit experimental-model acquisition; never called by normal startup."""
from __future__ import annotations
import hashlib
from pathlib import Path
import urllib.request
from .settings import data_directory

FACE_MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_full_range/float16/latest/blaze_face_full_range.tflite"
FACE_MODEL_SHA256 = "3698b18f063835bc609069ef052228fbe86d9c9a6dc8dcb7c7c2d69aed2b181b"
MAX_MODEL_BYTES = 8 * 1024 * 1024


def _validate(payload):
    if (len(payload) > MAX_MODEL_BYTES or payload[4:8] != b"TFL3"
            or hashlib.sha256(payload).hexdigest() != FACE_MODEL_SHA256):
        raise ValueError("Experimental model failed integrity validation; no existing file changed.")


def prepare_head_model(directory: Path | None = None) -> Path:
    """Called only by the explicit comparison action; exclusive new-file writes.

    Google latest may change. A different digest is rejected, not auto-adopted.
    Existing local files are validated read-only and are never replaced.
    """
    directory = data_directory() / "models" if directory is None else Path(directory)
    target = directory / "blaze_face_full_range_trial.tflite"
    if target.exists():
        with target.open("rb") as source:
            _validate(source.read(MAX_MODEL_BYTES + 1))
        return target
    with urllib.request.urlopen(FACE_MODEL_URL, timeout=30) as response:
        payload = response.read(MAX_MODEL_BYTES + 1)
    _validate(payload)
    directory.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        output.write(payload)
    return target
