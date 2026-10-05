"""Normalized scene geometry; masks are applied before model inference.

No frame is written to disk. Scene coordinates describe the original camera
frame, including when inference uses a cropped image.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, isfinite
from typing import Mapping, Sequence

import numpy as np


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class Rect:
    """A nonempty rectangle fully inside the normalized camera image."""

    x: float
    y: float
    width: float
    height: float

    def __post_init__(self) -> None:
        for name in ("x", "y", "width", "height"):
            object.__setattr__(self, name, _number(getattr(self, name), name))
        if not (0 <= self.x < 1 and 0 <= self.y < 1):
            raise ValueError("rectangle origin must lie inside [0, 1)")
        if not (0 < self.width <= 1 and 0 < self.height <= 1):
            raise ValueError("rectangle dimensions must lie inside (0, 1]")
        if self.x + self.width > 1 + 1e-12 or self.y + self.height > 1 + 1e-12:
            raise ValueError("rectangle must stay inside the camera image")

    @classmethod
    def from_corners(cls, x1: float, y1: float, x2: float, y2: float) -> Rect:
        x1, y1 = _number(x1, "x1"), _number(y1, "y1")
        x2, y2 = _number(x2, "x2"), _number(y2, "y2")
        return cls(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))

    def contains(self, x: float, y: float) -> bool:
        return (
            isfinite(x) and isfinite(y)
            and self.x <= x <= self.x + self.width
            and self.y <= y <= self.y + self.height
        )

    def to_pixels(self, width: int, height: int) -> tuple[int, int, int, int]:
        if isinstance(width, bool) or isinstance(height, bool):
            raise ValueError("image dimensions must be positive integers")
        if not isinstance(width, int) or not isinstance(height, int) or width < 1 or height < 1:
            raise ValueError("image dimensions must be positive integers")
        # Decimal corner taps can acquire binary floating-point noise at exact
        # pixel edges. Remove sub-billionth-pixel noise before outward rounding.
        x = min(width - 1, max(0, floor(round(self.x * width, 9))))
        y = min(height - 1, max(0, floor(round(self.y * height, 9))))
        right = min(width, max(x + 1, ceil(round((self.x + self.width) * width, 9))))
        bottom = min(height, max(y + 1, ceil(round((self.y + self.height) * height, 9))))
        return x, y, right - x, bottom - y

    def to_dict(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in ("x", "y", "width", "height")}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> Rect:
        if not isinstance(data, Mapping) or set(data) != {"x", "y", "width", "height"}:
            raise ValueError("rectangle requires x, y, width, height")
        return cls(**data)


@dataclass(frozen=True)
class SceneConfig:
    roi: Rect = Rect(0, 0, 1, 1)
    exclusions: tuple[Rect, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.roi, Rect):
            raise ValueError("roi must be a Rect")
        object.__setattr__(self, "exclusions", tuple(self.exclusions))
        if any(not isinstance(rect, Rect) for rect in self.exclusions):
            raise ValueError("exclusions must contain Rect values")

    def to_dict(self) -> dict[str, object]:
        return {"roi": self.roi.to_dict(), "exclusions": [r.to_dict() for r in self.exclusions]}

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> SceneConfig:
        if not isinstance(data, Mapping) or set(data) - {"roi", "exclusions"}:
            raise ValueError("scene accepts only roi and exclusions")
        exclusions = data.get("exclusions", [])
        if not isinstance(exclusions, (list, tuple)):
            raise ValueError("exclusions must be a list")
        return cls(
            Rect.from_dict(data["roi"]) if "roi" in data else Rect(0, 0, 1, 1),
            tuple(Rect.from_dict(rect) for rect in exclusions),
        )

    def accepts_point(self, x: float, y: float) -> bool:
        return self.roi.contains(x, y) and not any(r.contains(x, y) for r in self.exclusions)

    def prepare_frame(self, frame: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
        """Return a detached masked BGR crop and its original pixel rectangle."""
        if not isinstance(frame, np.ndarray) or frame.ndim != 3 or frame.shape[2] != 3:
            raise ValueError("frame must be an H by W by 3 BGR array")
        height, width = frame.shape[:2]
        roi_pixels = self.roi.to_pixels(width, height)
        masked = frame.copy()
        for exclusion in self.exclusions:
            x, y, w, h = exclusion.to_pixels(width, height)
            masked[y:y + h, x:x + w] = 0
        x, y, w, h = roi_pixels
        return np.ascontiguousarray(masked[y:y + h, x:x + w]), roi_pixels

    @staticmethod
    def map_point(
        point: Sequence[float], roi_pixels: tuple[int, int, int, int],
        frame_width: int, frame_height: int,
    ) -> tuple[float, float]:
        """Map model coordinates using the actual rounded crop bounds."""
        if frame_width <= 0 or frame_height <= 0 or len(point) < 2:
            raise ValueError("positive frame dimensions and a two-coordinate point required")
        x, y, w, h = roi_pixels
        if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > frame_width or y + h > frame_height:
            raise ValueError("crop must lie inside the original frame")
        px, py = _number(point[0], "point x"), _number(point[1], "point y")
        return (x + px * w) / frame_width, (y + py * h) / frame_height

    @staticmethod
    def map_landmarks(
        landmarks: Sequence[Sequence[float]], roi_pixels: tuple[int, int, int, int],
        frame_width: int, frame_height: int,
    ) -> tuple[tuple[float, float, float], ...]:
        """Map x/y and retain the third component unchanged.

        For model depth z, the caller must also rescale depth from cropped to
        full-frame width. This helper only remaps the image plane.
        """
        mapped = []
        for landmark in landmarks:
            if len(landmark) != 3:
                raise ValueError("landmark must contain x, y, z")
            x, y = SceneConfig.map_point(landmark, roi_pixels, frame_width, frame_height)
            mapped.append((x, y, _number(landmark[2], "landmark z")))
        return tuple(mapped)
