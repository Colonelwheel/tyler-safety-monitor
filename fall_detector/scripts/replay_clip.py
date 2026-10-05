"""Analyze an approved local clip in order, saving private feature data only.

No camera is opened, no model is downloaded, and the source clip is read only.
Native decoding/inference runs in an owned process with a bounded total timeout.
Optional timestamp sidecar: {"schema_version":1,"timestamps":[seconds,...]}.
Without a sidecar, timestamps derive from the clip's nominal FPS and cannot
recover the original camera cadence. No images, overlays or identity are saved.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import multiprocessing as mp
import platform
from pathlib import Path
import queue
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def file_digest(path: Path) -> str:
    """Stream a read-only source fingerprint without copying large clips."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_output(path: Path) -> Path:
    from tyler_safety_monitor.settings import data_directory
    root = (data_directory() / "calibration" / "replays").resolve()
    target = path.resolve()
    if target == root or not target.is_relative_to(root) or target.suffix.lower() != ".json":
        raise ValueError("output must be a new JSON file in the local calibration/replays directory")
    if target.exists():
        raise FileExistsError("output already exists")
    return target


def load_timestamps(path: Path | None):
    if path is None:
        return None
    from tyler_safety_monitor.replay import MAX_SAMPLES, MAX_DURATION, _unique_keys, _time
    with path.open("rb") as stream:
        payload = stream.read(1024 * 1024 + 1)
    if len(payload) > 1024 * 1024:
        raise ValueError("timestamp sidecar exceeds size limit")
    data = json.loads(payload, object_pairs_hook=_unique_keys)
    if (not isinstance(data, dict) or set(data) != {"schema_version", "timestamps"}
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or not isinstance(data["timestamps"], list) or not 1 <= len(data["timestamps"]) <= MAX_SAMPLES):
        raise ValueError("invalid timestamp sidecar")
    times = tuple(_time(t) for t in data["timestamps"])
    if any(a >= b for a, b in zip(times, times[1:])) or times[-1] - times[0] > MAX_DURATION:
        raise ValueError("invalid timestamp ordering or duration")
    return times


def analyze_clip(clip: Path, model: Path, output: Path, scene, sidecar: Path | None = None):
    import cv2
    from tyler_safety_monitor.pose import isolate_model_cache, observations_from_result
    from tyler_safety_monitor.replay import FeatureSample, FeatureSequence, MAX_SAMPLES, MAX_DURATION, save_sequence
    isolate_model_cache()
    import mediapipe as mediapipe
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    if not clip.is_file() or not model.is_file():
        raise FileNotFoundError("local clip/model is missing")
    output = validate_output(output)
    times = load_timestamps(sidecar)
    with model.open("rb") as stream:
        bundle = stream.read(64 * 1024 * 1024 + 1)
    if len(bundle) > 64 * 1024 * 1024:
        raise ValueError("model exceeds size limit")
    digest = hashlib.sha256(bundle).hexdigest()
    del bundle
    clip_digest = file_digest(clip)
    capture = cv2.VideoCapture(str(clip))
    if not capture.isOpened():
        capture.release()
        raise ValueError("clip cannot be decoded")
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        declared_frames = float(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        if times is None and (not math.isfinite(fps) or fps <= 0):
            raise ValueError("clip has no usable timebase; supply a timestamp sidecar")
        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model)),
            running_mode=vision.RunningMode.VIDEO, num_poses=2,
            min_pose_detection_confidence=.5, min_pose_presence_confidence=.5,
            min_tracking_confidence=.5)
        samples = []
        inference_timestamp = -1
        dimensions = None
        with vision.PoseLandmarker.create_from_options(options) as detector:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                index = len(samples)
                if index >= MAX_SAMPLES or times is not None and index >= len(times):
                    raise ValueError("clip exceeds sample count or sidecar length")
                if frame is None or frame.ndim != 3 or frame.shape[2] != 3 or not frame.size:
                    raise ValueError("invalid decoded clip frame")
                width, height = frame.shape[1], frame.shape[0]
                if width > 4096 or height > 2160:
                    raise ValueError("clip dimensions exceed supported bounds")
                if dimensions is not None and dimensions != (width, height):
                    raise ValueError("clip dimensions changed")
                dimensions = (width, height)
                timestamp = times[index] if times is not None else index / fps
                origin = samples[0].timestamp if samples else timestamp
                if timestamp - origin > MAX_DURATION:
                    raise ValueError("clip exceeds duration limit")
                # Model millisecond rounding is separate from untouched source time.
                inference_timestamp = max(inference_timestamp + 1, int((timestamp - origin) * 1000))
                crop, roi = scene.prepare_frame(frame)
                image = mediapipe.Image(image_format=mediapipe.ImageFormat.SRGB,
                                        data=cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                result = detector.detect_for_video(image, inference_timestamp)
                observations = observations_from_result(result, scene, roi, width, height)
                samples.append(FeatureSample(timestamp, index, observations, inference_timestamp))
        if not samples or times is not None and len(samples) != len(times):
            raise ValueError("empty clip or timestamp sidecar length mismatch")
        if (math.isfinite(declared_frames) and declared_frames > 0
                and abs(len(samples) - declared_frames) > .5):
            raise ValueError("decoded clip length differs from declared frame count")
        sequence = FeatureSequence(scene, {
            "source_kind": "approved_local_clip", "model_sha256": digest,
            "model_name": next((variant for variant in ("lite", "full", "heavy")
                                if model.name == f"pose_landmarker_{variant}.task"), "custom"),
            "clip_sha256": clip_digest,
            "dependencies": {"python": platform.python_version(),
                             "mediapipe": importlib.metadata.version("mediapipe"),
                             "opencv": importlib.metadata.version("opencv-contrib-python"),
                             "numpy": importlib.metadata.version("numpy")},
            "frame_width": dimensions[0], "frame_height": dimensions[1], "num_poses": 2,
            "timestamp_basis": "source_capture_sidecar" if times else "nominal_clip_fps",
        }, tuple(samples))
        save_sequence(sequence, path=output)
        return len(samples)
    finally:
        capture.release()


def _worker(arguments, scene_data, status):
    try:
        from tyler_safety_monitor.scene import SceneConfig
        count = analyze_clip(arguments.clip, arguments.model, arguments.output,
                             SceneConfig.from_dict(scene_data), arguments.timestamps)
        status.put({"saved": True, "samples": count})
    except Exception as error:
        status.put({"saved": False, "error_type": type(error).__name__})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--scene", type=Path, help="Local JSON scene containing roi and exclusions")
    parser.add_argument("--timestamps", type=Path)
    parser.add_argument("--timeout", type=float, default=600, help="Total worker deadline in seconds, 1–3600")
    args = parser.parse_args()
    process = status = None
    try:
        from tyler_safety_monitor.scene import SceneConfig
        from tyler_safety_monitor.replay import _unique_keys
        if not math.isfinite(args.timeout) or not 1 <= args.timeout <= 3600:
            raise ValueError("invalid worker deadline")
        args.output = validate_output(args.output)
        scene = SceneConfig()
        if args.scene:
            with args.scene.open("rb") as stream:
                payload = stream.read(128 * 1024 + 1)
            if len(payload) > 128 * 1024:
                raise ValueError("scene exceeds size limit")
            scene = SceneConfig.from_dict(json.loads(payload, object_pairs_hook=_unique_keys))
        context = mp.get_context("spawn")
        status = context.Queue(maxsize=1)
        process = context.Process(target=_worker, args=(args, scene.to_dict(), status), name="approved-clip-replay")
        process.start()
        process.join(args.timeout)
        if process.is_alive():
            raise TimeoutError("clip analysis deadline exceeded")
        try:
            result = status.get(timeout=1)
        except queue.Empty:
            result = {"saved": False, "error_type": "WorkerFailure"}
        print(json.dumps(result))
        return 0 if result["saved"] else 1
    except (Exception, KeyboardInterrupt) as error:
        print(json.dumps({"saved": False, "error_type": type(error).__name__,
                          "error": "Clip analysis stopped; source files preserved. Any partial new output is retained."}), file=sys.stderr)
        return 1
    finally:
        if process is not None and process.pid is not None:
            if process.is_alive():
                process.terminate()
                process.join(timeout=2)
            if not process.is_alive():
                process.close()
        if status is not None:
            status.cancel_join_thread()
            status.close()


if __name__ == "__main__":
    raise SystemExit(main())
