import numpy as np
import pytest

from tyler_safety_monitor.scene import Rect, SceneConfig


@pytest.mark.parametrize("values", [
    (float("nan"), 0, 1, 1), (0, 0, float("inf"), 1),
    (0.8, 0, 0.3, 1), (0, 0, 0, 1), (-0.1, 0, 1, 1),
    (True, 0, 1, 1),
])
def test_invalid_rectangle_is_rejected(values):
    with pytest.raises(ValueError):
        Rect(*values)


def test_reverse_corner_taps_and_tiny_region_produce_valid_pixels():
    assert Rect.from_corners(0.8, 0.9, 0.2, 0.3).to_pixels(10, 10) == (2, 3, 6, 6)
    assert Rect(0.999, 0.999, 0.001, 0.001).to_pixels(2, 2) == (1, 1, 1, 1)
    with pytest.raises(ValueError):
        Rect.from_corners(0.2, 0.2, 0.2, 0.4)


def test_mask_is_applied_in_full_frame_coordinates_before_crop_without_mutating_input():
    frame = np.full((10, 20, 3), 255, dtype=np.uint8)
    scene = SceneConfig(Rect(0.25, 0.2, 0.5, 0.6), (Rect(0.2, 0.3, 0.2, 0.2),))
    crop, pixels = scene.prepare_frame(frame)
    assert pixels == (5, 2, 10, 6)
    assert crop.shape == (6, 10, 3)
    assert np.all(crop[1:3, 0:3] == 0)
    assert np.all(crop[0] == 255)
    assert np.all(crop[1:3, 3:] == 255)
    assert np.all(frame == 255)
    crop[0, 0] = 42
    assert np.all(frame == 255)


def test_landmark_mapping_uses_actual_pixel_crop_and_rejects_excluded_head():
    scene = SceneConfig(Rect(0.23, 0.1, 0.52, 0.8), (Rect(0.4, 0.3, 0.1, 0.1),))
    pixels = scene.roi.to_pixels(10, 10)
    assert pixels == (2, 1, 6, 8)
    assert scene.map_point((0.5, 0.5), pixels, 10, 10) == (0.5, 0.5)
    assert scene.map_landmarks(((0.5, 0.5, 0.8),), pixels, 10, 10) == ((0.5, 0.5, 0.8),)
    assert not scene.accepts_point(0.45, 0.35)
    assert not scene.accepts_point(0.1, 0.5)
    assert scene.accepts_point(0.5, 0.5)


def test_configuration_roundtrip_and_bad_config_fail_visibly():
    scene = SceneConfig(Rect(0.2, 0.3, 0.5, 0.4), (Rect(0.1, 0.1, 0.2, 0.2),))
    assert SceneConfig.from_dict(scene.to_dict()) == scene
    assert SceneConfig.from_dict({}) == SceneConfig()
    with pytest.raises(ValueError):
        SceneConfig.from_dict({"exclusions": "invalid"})
    with pytest.raises(ValueError):
        SceneConfig.from_dict({"unknown": 1})
    with pytest.raises(ValueError):
        scene.prepare_frame(np.zeros((10, 10)))
