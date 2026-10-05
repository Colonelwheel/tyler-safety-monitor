"""Read-only image benchmark. Outputs aggregates, never imagery/landmarks/paths."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import statistics
import sys
import time
import urllib.request
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def model_url(variant: str) -> str:
    if variant not in ("lite", "full", "heavy"):
        raise ValueError("unsupported model variant")
    return ("https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
            f"pose_landmarker_{variant}/float16/1/pose_landmarker_{variant}.task")


def download_model(variant: str) -> dict:
    """Explicit local download with fixed source and exclusive new-file creation.

    Existing files are read only and never replaced. Download completes in
    memory before exclusive creation, avoiding truncated files on HTTP errors.
    SHA256 is provenance evidence, not publisher-signature verification.
    """
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is required")
    target = Path(local_app_data) / "TylerSafetyMonitor" / "models" / f"pose_landmarker_{variant}.task"
    if target.exists():
        raise FileExistsError("Model destination already exists; existing data preserved.")
    with urllib.request.urlopen(model_url(variant), timeout=60) as response:
        payload = response.read(64 * 1024 * 1024 + 1)
    if len(payload) > 64 * 1024 * 1024 or not zipfile.is_zipfile(io.BytesIO(payload)):
        raise ValueError("Unexpected model bundle size or format")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as output:
        output.write(payload)
    return {"variant": variant, "version": 1, "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload), "local_model_path": str(target)}


def benchmark(models: list[Path], images: list[Path], repeats: int,
              warmup: int, pose_counts: list[int], scenes: dict) -> dict:
    import cv2
    from tyler_safety_monitor.pose import isolate_model_cache, observations_from_result
    isolate_model_cache()
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    frames = []
    for path in images:
        frame = cv2.imread(str(path))
        if frame is None:
            raise ValueError("An input image could not be read")
        frames.append(frame)
    rows = []
    for model in models:
        if not model.is_file():
            raise FileNotFoundError("A local model is missing")
        digest = hashlib.sha256(model.read_bytes()).hexdigest()
        # Never print an arbitrary user-provided filename; variant comes from
        # known model identifiers or an anonymous label.
        variant = next((v for v in ("lite", "full", "heavy")
                        if model.name == f"pose_landmarker_{v}.task"), "custom")
        for count in pose_counts:
            options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.IMAGE, num_poses=count,
                min_pose_detection_confidence=0.5,
                min_pose_presence_confidence=0.5,
                min_tracking_confidence=0.5)
            with vision.PoseLandmarker.create_from_options(options) as detector:
                for scene_label, scene in scenes.items():
                    for index, frame in enumerate(frames, start=1):
                        cropped, roi = scene.prepare_frame(frame)
                        rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                        for _ in range(warmup):
                            detector.detect(image)
                        durations, heads, raw_counts, confidences, shoulder_counts = [], [], [], [], []
                        for _ in range(repeats):
                            started = time.perf_counter()
                            result = detector.detect(image)
                            observations = observations_from_result(
                                result, scene, roi, frame.shape[1], frame.shape[0])
                            durations.append((time.perf_counter() - started) * 1000)
                            heads.append(len(observations))
                            raw_counts.append(len(result.pose_landmarks))
                            shoulder_counts.append(sum(p.shoulders is not None for p in observations))
                            confidences.extend(p.confidence for p in observations)
                        ordered = sorted(durations)
                        rows.append({
                            "model": variant, "model_sha256": digest, "num_poses": count,
                            "scene": scene_label, "sample": index,
                            "repeats": repeats, "warmup": warmup,
                            "latency_median_ms": round(statistics.median(durations), 2),
                            "latency_p95_ms": round(ordered[min(len(ordered)-1, int(.95*len(ordered)))], 2),
                            "raw_pose_count_range": [min(raw_counts), max(raw_counts)],
                            "accepted_head_count_range": [min(heads), max(heads)],
                            "head_detection_fraction": sum(h > 0 for h in heads) / repeats,
                            "shoulder_count_range": [min(shoulder_counts), max(shoulder_counts)],
                            "head_landmark_confidence_mean": round(statistics.mean(confidences), 4) if confidences else None,
                        })
    return {"method": "IMAGE; repeated still-image inference; CPU default delegate",
            "limitations": ["No temporal tracking or identity-swap validation",
                            "num_poses is capacity, not evidence of two real people",
                            "Model confidence is not calibrated detection accuracy",
                            "No image, coordinate, path, or overlay written"],
            "sample_count": len(frames), "results": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download-model", choices=("lite", "full", "heavy"))
    parser.add_argument("--models", nargs="+", type=Path)
    parser.add_argument("--images", nargs="+", type=Path)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--num-poses", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--exclude", nargs=4, type=float, action="append", default=[],
                        metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="Local normalized exclusion rectangle; repeat for multiple masks")
    parser.add_argument("--compare-roi", nargs=4, type=float,
                        metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="Optional local normalized inference crop to compare with full frame")
    arguments = parser.parse_args()
    try:
        if arguments.download_model:
            result = download_model(arguments.download_model)
        else:
            if not arguments.models or not arguments.images:
                parser.error("--models and --images are required for benchmarking")
            if arguments.repeats < 1 or arguments.warmup < 0 or any(n < 1 for n in arguments.num_poses):
                parser.error("repeats/num-poses must be positive and warmup nonnegative")
            from tyler_safety_monitor.scene import Rect, SceneConfig
            exclusions = tuple(Rect(*values) for values in arguments.exclude)
            scenes = {"full_masked" if exclusions else "full": SceneConfig(exclusions=exclusions)}
            if arguments.compare_roi is not None:
                scenes["roi_masked" if exclusions else "roi"] = SceneConfig(
                    Rect(*arguments.compare_roi), exclusions)
            result = benchmark(arguments.models, arguments.images, arguments.repeats,
                               arguments.warmup, arguments.num_poses, scenes)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        # Native framework diagnostics may go to stderr, but our errors never
        # echo private image paths or arbitrary model contents.
        print(json.dumps({"error_type": type(error).__name__,
                          "error": "Operation failed; existing input files preserved."}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
