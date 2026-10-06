from pathlib import Path
import importlib.util
from types import SimpleNamespace
import time

import numpy as np
import pytest

from tyler_safety_monitor.pose import PoseWorker, isolate_model_cache, observations_from_result
from tyler_safety_monitor.scene import Rect, SceneConfig


def result_at(x=.5, y=.5, confidence=.9):
    return SimpleNamespace(pose_landmarks=[[
        SimpleNamespace(x=x, y=y, z=.2, visibility=confidence, presence=confidence)
        for _ in range(33)]])


def test_crop_coordinates_and_head_only_survive_missing_shoulders():
    scene = SceneConfig(Rect(.2, .4, .6, .5))
    result = result_at()
    result.pose_landmarks[0][11].visibility = .1
    result.pose_landmarks[0][12].visibility = .1
    observations = observations_from_result(result, scene, (200, 400, 600, 500), 1000, 1000)
    assert observations[0].head == pytest.approx((.5, .65))
    assert observations[0].shoulders is None
    assert observations[0].landmarks[0] == pytest.approx((.5, .65, .12))
    assert observations[0].confidence == pytest.approx(.9)
    assert len(observations[0].landmark_scores) == 33
    assert observations[0].landmark_scores[11] == (.1, .9)
    assert observations[0].landmark_scores[12] == (.1, .9)
    assert observations[0].landmark_scores[0] == (.9, .9)


def test_unavailable_scores_are_retained_as_zero_without_changing_visible_head():
    result = result_at()
    result.pose_landmarks[0][0].visibility = None
    result.pose_landmarks[0][0].presence = float("nan")
    result.pose_landmarks[0][11].visibility = float("inf")
    result.pose_landmarks[0][12].presence = None
    observation = observations_from_result(result, SceneConfig(), (0, 0, 100, 100), 100, 100)[0]
    assert observation.head == (.5, .5)
    assert observation.confidence == pytest.approx(.9)
    assert observation.shoulders is None
    assert len(observation.landmarks) == 33
    assert observation.landmark_scores[0] == (0, 0)
    assert observation.landmark_scores[11] == (0, .9)
    assert observation.landmark_scores[12] == (.9, 0)


def test_visible_face_landmark_fallback():
    result = result_at()
    for index in (0, 2, 5, 7):
        result.pose_landmarks[0][index].presence = .1
    result.pose_landmarks[0][8].x = .6
    observation = observations_from_result(result, SceneConfig(), (0, 0, 100, 100), 100, 100)[0]
    assert observation.head == pytest.approx((.6, .5))


def test_low_confidence_excluded_and_nonfinite_heads_rejected():
    scene = SceneConfig(exclusions=(Rect(.4, .4, .2, .2),))
    assert not observations_from_result(result_at(), scene, (0, 0, 100, 100), 100, 100)
    assert not observations_from_result(result_at(confidence=.1), SceneConfig(), (0, 0, 100, 100), 100, 100)
    assert not observations_from_result(result_at(x=float("nan")), SceneConfig(), (0, 0, 100, 100), 100, 100)


def test_missing_model_is_visible_fault_without_implicit_download(monkeypatch):
    monkeypatch.setattr(Path, "is_file", lambda _path: False)
    worker = PoseWorker(Path("absent.task"), SceneConfig())
    worker.start()
    assert "model missing" in worker.error
    assert worker._thread is None
    assert not worker.submit(np.zeros((10, 10, 3), dtype=np.uint8))


def test_mailbox_keeps_latest_copy_and_counts_inference_skips():
    worker = PoseWorker(Path("unused.task"), SceneConfig())
    worker._thread = object()  # Submit behavior, without any native inference.
    first = np.full((10, 10, 3), 1, dtype=np.uint8)
    second = np.full((10, 10, 3), 2, dtype=np.uint8)
    assert worker.submit(first, 7)
    assert worker.submit(second, 7)
    second[:] = 0
    assert worker._pending[0].mean() == 2
    assert worker._pending[1] == 8  # MediaPipe requires increasing timestamps.
    assert worker.stats.submitted == 2
    assert worker.stats.dropped == 1
    assert worker.stats.completed == 0


def test_callback_maps_snapshot_and_rejects_old_scene_even_after_return():
    original = SceneConfig()
    worker = PoseWorker(Path("unused.task"), original)
    worker._active = (10, original, (0, 0, 100, 100), 100, 100, time.monotonic(), 0)
    worker.set_scene(SceneConfig(Rect(.1, .1, .8, .8)))
    worker.set_scene(original)
    worker._callback(result_at(), None, 10)
    assert worker.latest_result is None
    assert worker.stats.completed == 1
    worker._active = (11, original, (0, 0, 100, 100), 100, 100, time.monotonic(), 2)
    worker._callback(result_at(), None, 11)
    assert worker.latest_result.timestamp_ms == 11
    assert worker.latest_result.scene_generation == 2
    assert worker.latest_result.observations[0].head == (.5, .5)


def test_malformed_callback_becomes_visible_fault_and_releases_active_slot():
    scene = SceneConfig()
    worker = PoseWorker(Path("unused.task"), scene)
    worker._active = (1, scene, (0, 0, 100, 100), 100, 100, time.monotonic(), 0)
    worker._callback(SimpleNamespace(), None, 1)
    assert worker._active is None
    assert "Invalid pose result" in worker.error
    assert worker.latest_result is None


def test_model_download_refuses_existing_file_before_any_network_or_write(monkeypatch):
    script = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_pose.py"
    spec = importlib.util.spec_from_file_location("benchmark_pose_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("LOCALAPPDATA", "C:/detector-runtime-test")
    monkeypatch.setattr(Path, "exists", lambda _path: True)

    def forbidden(*args, **kwargs):
        raise AssertionError("existing destination must not access network or write")

    monkeypatch.setattr(module.urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(Path, "open", forbidden)
    with pytest.raises(FileExistsError):
        module.download_model("lite")


def test_model_cache_uses_only_dedicated_runtime_location(monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", "C:/detector-runtime-test")
    monkeypatch.setenv("MPLCONFIGDIR", "C:/shared-user-cache")
    created = []
    monkeypatch.setattr(Path, "mkdir", lambda path, **kwargs: created.append(path))
    isolate_model_cache()
    assert created == [Path("C:/detector-runtime-test/TylerSafetyMonitor/cache/matplotlib")]
    import os
    assert Path(os.environ["MPLCONFIGDIR"]) == created[0]


class FakeThread:
    def __init__(self, alive):
        self.alive = alive
        self.joins = []

    def is_alive(self):
        return self.alive

    def join(self, timeout):
        self.joins.append(timeout)


def test_native_startup_timeout_is_visible_without_waiting_for_native_return():
    worker = PoseWorker(Path("unused.task"), SceneConfig())
    worker._thread = FakeThread(True)
    worker._initializing_at = time.monotonic() - 16
    assert worker.is_alive
    assert not worker.ready
    assert "initialization timed out" in worker.error
    assert not worker.submit(np.zeros((10, 10, 3), dtype=np.uint8))


def test_close_reports_unfinished_native_worker_and_rejects_reuse():
    worker = PoseWorker(Path("unused.task"), SceneConfig())
    thread = FakeThread(True)
    worker._thread = thread
    worker._ready = True
    assert not worker.close()
    assert thread.joins == [1]
    assert worker.is_alive
    assert not worker.ready
    assert "did not stop" in worker.error
    assert not worker.submit(np.zeros((10, 10, 3), dtype=np.uint8))
    worker.start()
    assert worker._thread is thread
    thread.alive = False
    assert worker.close()
    assert not worker.is_alive


def test_close_without_started_worker_succeeds():
    worker = PoseWorker(Path("unused.task"), SceneConfig())
    assert worker.close()
    assert not worker.is_alive


@pytest.mark.parametrize("flags, expected", [
    ([], {"full"}),
    (["--exclude", "0.1", "0.1", "0.2", "0.2"], {"full_masked"}),
    (["--exclude", "0.1", "0.1", "0.2", "0.2",
      "--compare-roi", "0.2", "0.2", "0.5", "0.5"], {"full_masked", "roi_masked"}),
])
def test_benchmark_scenes_come_only_from_explicit_cli(monkeypatch, capsys, flags, expected):
    script = Path(__file__).resolve().parents[2] / "scripts" / "benchmark_pose.py"
    spec = importlib.util.spec_from_file_location("benchmark_pose_cli_test", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import sys
    monkeypatch.setattr(sys, "argv", ["benchmark_pose", "--models", "unused.task",
                                      "--images", "unused.png", *flags])
    captured = {}

    def capture(models, images, repeats, warmup, pose_counts, scenes):
        captured.update(scenes)
        return {"mock": True}

    monkeypatch.setattr(module, "benchmark", capture)
    assert module.main() == 0
    assert set(captured) == expected
    if not flags:
        assert captured["full"] == SceneConfig()
    capsys.readouterr()


def test_recent_loss_counts_distinguish_native_miss_from_head_rejection_and_expire():
    scene = SceneConfig()
    worker = PoseWorker(Path("unused.task"), scene)
    def deliver(result, timestamp):
        worker._active = (timestamp, scene, (0, 0, 100, 100), 100, 100, time.monotonic(), 0)
        worker._callback(result, None, timestamp)
    deliver(SimpleNamespace(pose_landmarks=[]), 100)
    deliver(result_at(confidence=.1), 200)
    deliver(result_at(), 300)
    assert worker.stats.diagnostic_frames == 3
    assert worker.stats.no_pose_frames == 1
    assert worker.stats.rejected_head_frames == 1
    assert worker.stats.accepted_heads == 1
    deliver(result_at(), 10250)
    assert worker.stats.diagnostic_frames == 2
    assert worker.stats.no_pose_frames == worker.stats.rejected_head_frames == 0
    assert worker.stats.completed == 4


def test_scene_reset_and_late_callback_do_not_restore_old_loss_diagnostics():
    scene = SceneConfig()
    worker = PoseWorker(Path("unused.task"), scene)
    worker._active = (100, scene, (0, 0, 100, 100), 100, 100, time.monotonic(), 0)
    worker._callback(SimpleNamespace(pose_landmarks=[]), None, 100)
    assert worker.stats.no_pose_frames == 1
    worker.set_scene(scene)
    assert worker.stats.diagnostic_frames == worker.stats.no_pose_frames == 0
    worker._active = (200, scene, (0, 0, 100, 100), 100, 100, time.monotonic(), 0)
    worker._callback(result_at(), None, 200)
    assert worker.latest_result is None
    assert worker.stats.diagnostic_frames == worker.stats.raw_poses == worker.stats.accepted_heads == 0
    assert worker.stats.completed == 2
