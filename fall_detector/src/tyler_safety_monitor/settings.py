"""Validated nonsecret settings with append-only local revisions."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
from uuid import uuid4

from .scene import SceneConfig


def data_directory() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        raise RuntimeError("LOCALAPPDATA is unavailable; local settings cannot be stored")
    return Path(base) / "TylerSafetyMonitor"


@dataclass(frozen=True)
class AppSettings:
    camera_index: int = 0
    backend: str = "dshow"
    fps: int = 15
    alert_volume: float = 0.5
    scene: SceneConfig = field(default_factory=SceneConfig)

    def __post_init__(self) -> None:
        if type(self.camera_index) is not int or not 0 <= self.camera_index <= 20:
            raise ValueError("camera index must be an integer from 0 to 20")
        if self.backend not in {"dshow", "msmf"}:
            raise ValueError("backend must be dshow or msmf")
        if type(self.fps) is not int or self.fps not in {15, 30}:
            raise ValueError("FPS must be 15 or 30")
        if isinstance(self.alert_volume, bool) or not isinstance(self.alert_volume, (int, float)):
            raise ValueError("alert volume must be a number")
        if not math.isfinite(self.alert_volume) or not 0 <= self.alert_volume <= 1:
            raise ValueError("alert volume must be between zero and one")
        if not isinstance(self.scene, SceneConfig):
            raise ValueError("scene settings are invalid")

    def to_dict(self) -> dict:
        return {"schema_version": 1, "camera_index": self.camera_index,
                "backend": self.backend, "fps": self.fps,
                "alert_volume": self.alert_volume, "scene": self.scene.to_dict()}

    @classmethod
    def from_dict(cls, data: dict) -> AppSettings:
        if not isinstance(data, dict) or data.get("schema_version") != 1:
            raise ValueError("unsupported settings schema")
        allowed = {"schema_version", "camera_index", "backend", "fps", "alert_volume", "scene"}
        if set(data) - allowed:
            raise ValueError("unknown settings fields")
        fields = {k: v for k, v in data.items() if k != "schema_version"}
        fields["scene"] = SceneConfig.from_dict(fields.get("scene", {}))
        return cls(**fields)


def save_settings(settings: AppSettings, directory: Path | None = None) -> Path:
    """Create one new revision; never replace or remove earlier settings."""
    directory = directory if directory is not None else data_directory() / "config"
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = directory / f"settings-{stamp}-{uuid4().hex}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(settings.to_dict(), stream, indent=2, allow_nan=False)
        stream.write("\n")
    return path


def load_settings(directory: Path | None = None) -> tuple[AppSettings, str]:
    directory = directory if directory is not None else data_directory() / "config"
    if not directory.exists():
        return AppSettings(), "Default settings; scene has not been calibrated"
    revisions = sorted(directory.glob("settings-*.json"), reverse=True)
    if not revisions:
        return AppSettings(), "Default settings; scene has not been calibrated"
    # Reject a corrupt newest revision visibly instead of silently using old geometry.
    path = revisions[0]
    try:
        if path.stat().st_size > 128 * 1024:
            raise ValueError("settings file is too large")
        settings = AppSettings.from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, TypeError) as error:
        return AppSettings(), f"Settings fault: {error}. Review ROI and exclusions before use."
    return settings, "Local settings loaded; observation only"
