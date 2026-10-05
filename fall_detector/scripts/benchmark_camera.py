"""Benchmark a camera sequentially; emit aggregate numbers, never camera media.

Run using the isolated environment after installing the detector package:
    python scripts/benchmark_camera.py --seconds 20 --warmup 5
The optional JSON output is created exclusively and never overwrites a file.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import statistics
import time

from tyler_safety_monitor.camera import CameraCapture, CameraSettings


def benchmark(settings: CameraSettings, seconds: float, warmup: float,
              startup_timeout: float = 25.0) -> dict:
    camera = CameraCapture(settings)
    samples = []
    started = time.monotonic()
    result = {"request": asdict(settings), "scope": "memory-only capture; no saved images"}
    camera.start()
    try:
        while time.monotonic() - started < startup_timeout:
            if camera.snapshot().state == "LIVE":
                break
            time.sleep(0.1)
        else:
            result.update({"success": False, "failure": "No live frame before startup timeout",
                           "final": asdict(camera.snapshot())})
            return result
        until = time.monotonic() + warmup
        while time.monotonic() < until:
            time.sleep(0.1)
        baseline = camera.snapshot()
        benchmark_started = time.monotonic()
        until = benchmark_started + seconds
        faults = 0
        while time.monotonic() < until:
            metrics = camera.snapshot()
            samples.append(metrics)
            if metrics.state != "LIVE":
                faults += 1
            time.sleep(0.1)
        final = camera.snapshot()
        elapsed = time.monotonic() - benchmark_started

        def summarize(name: str) -> dict:
            values = [getattr(sample, name) for sample in samples
                      if getattr(sample, name) is not None]
            return ({"mean": statistics.fmean(values), "minimum": min(values), "maximum": max(values)}
                    if values else {})

        result.update({
            "success": faults == 0,
            "duration_seconds": elapsed,
            "non_live_samples": faults,
            "sample_count": len(samples),
            "captured_frames": final.captured_frames - baseline.captured_frames,
            "received_frames": final.received_frames - baseline.received_frames,
            "capture_window_fps": (final.captured_frames - baseline.captured_frames) / elapsed,
            "receive_window_fps": (final.received_frames - baseline.received_frames) / elapsed,
            "read_failures": final.read_failures - baseline.read_failures,
            "reconnect_events": final.reconnect_events - baseline.reconnect_events,
            "transfer_drops": final.transfer_drops - baseline.transfer_drops,
            "cadence_gap_estimate": final.cadence_gap_estimate - baseline.cadence_gap_estimate,
            "diagnostics": {name: summarize(name) for name in
                            ("delivered_fps", "received_fps", "frame_age", "brightness", "blur", "exposure")},
            "final": asdict(final),
            "limits": ["Timestamp follows read completion; sensor-to-display latency is unmeasured",
                       "Cadence gaps are estimates, not confirmed camera/driver frame drops",
                       "Brightness and blur are diagnostics, not validated lighting safety thresholds"],
        })
        return result
    finally:
        camera.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--backend", choices=("dshow", "msmf", "all"), default="all")
    parser.add_argument("--fps", type=int, choices=(15, 30), help="Default: benchmark both 15 and 30")
    parser.add_argument("--seconds", type=float, default=20.0)
    parser.add_argument("--warmup", type=float, default=5.0)
    parser.add_argument("--output", type=Path, help="Explicit NEW aggregate JSON file; no imagery")
    args = parser.parse_args()
    if args.seconds <= 0 or args.warmup < 0:
        parser.error("Seconds must be positive and warmup nonnegative")
    if args.output and (args.output.suffix.lower() != ".json" or args.output.exists()):
        parser.error("Output must be a new .json file; existing files are never overwritten")
    backends = ("dshow", "msmf") if args.backend == "all" else (args.backend,)
    rates = (15, 30) if args.fps is None else (args.fps,)
    results = [benchmark(CameraSettings(index=args.index, backend=backend, fps=fps),
                         args.seconds, args.warmup) for backend in backends for fps in rates]
    payload = json.dumps({"benchmark": "C920 1920x1080 backend/FPS capture matrix", "results": results}, indent=2)
    print(payload)
    if args.output:
        # Exclusive mode still protects against a file created since the check.
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(payload + "\n")
    return 0 if all(result["success"] for result in results) else 1


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
