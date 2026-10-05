# Local pose model review and benchmark

Milestone 0 provides observations and person candidates only. It does not
classify choking, falls, caregiver identity, or confirmed caregiver presence.
There are no real alerts. Caregiver-entry sample validation is deferred at
Tyler's request; the supplied still images each show one real person.

## Model selection and provenance

The [current Pose Landmarker guide](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)
provides lite, full, and heavy bundles and configurable pose capacity. The
[Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker/python)
describes asynchronous LIVE_STREAM inference and skipped busy inputs. The
application uses a worker with one active inference and one replaceable newest
frame; capture read failures and inference skips are separate metrics.

Models are explicit local inputs. Starting the application never downloads a
model. The benchmark helper can explicitly download Google's float16 version-1
bundles to new files beneath `%LOCALAPPDATA%\TylerSafetyMonitor\models`. It refuses
to replace existing files and prints a SHA256 digest. The digest records the
downloaded bytes; it is not a publisher-signed trust check. `.task` bundles are
excluded from Git and are not bundled or redistributed with this project.

The official [BlazePose GHUM 3D model card](https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf)
lists Apache License 2.0. It describes the original 2021 model, with fitness and
entertainment uses, single-person limitations, and sensitivity to face size,
orientation, low light, and occlusion. It excludes human life-critical
decisions. The current task supports multiple poses, but this is not proof of
reliable caregiver tracking in this room. Verify notices and attribution in
each downloaded artifact before any future redistribution; the website's
content license is not sufficient evidence for a model artifact's license.

The CPU delegate is used for this Windows feasibility spike. The presence of an
NVIDIA GPU alone does not establish support for a MediaPipe GPU delegate.
MediaPipe's transitive plotting-library cache is redirected to the detector's
dedicated local runtime cache before import, preserving the shared Python/user
plotting cache and installed packages.

The initial supplied-image benchmark selected **Full with a masked full-frame
view** for the foundation default. It retained a visible head in both supplied
lighting samples at pose capacities one and two. The exploratory lower crop
missed sample 1; lite and heavy were less reliable on these images. These are
ordinary supplied photographs, not instructed leaning or collapse tests. No
movement testing was requested or performed for Milestone 0.
This supports the initial configuration, not a safety accuracy claim. Real
two-person caregiver validation remains deferred.

## Commands

Use the project's isolated environment; no system Python packages are changed.
From the repository root:

```powershell
fall_detector\.venv\Scripts\python.exe fall_detector\scripts\benchmark_pose.py --download-model lite
fall_detector\.venv\Scripts\python.exe fall_detector\scripts\benchmark_pose.py --download-model full
fall_detector\.venv\Scripts\python.exe fall_detector\scripts\benchmark_pose.py --download-model heavy
```

Benchmark external samples with `--models <local-task-paths>` and
`--images <external-image-paths>`. Optional settings are `--repeats 10`,
`--warmup 2`, and `--num-poses 1 2`. Images are opened read-only, masked and
cropped in memory, and never copied into the checkout. Standard output contains
aggregate JSON only. Framework diagnostics may appear on standard error.

The default benchmark uses the full frame. Supply local normalized rectangles
with `--exclude <x> <y> <width> <height>` (repeatable) and optionally
`--compare-roi <x> <y> <width> <height>`. With exclusions, the aggregate scene
labels are `full_masked` and `roi_masked`; without them, `full` and `roi`.
Private room geometry is not baked into source or committed configuration.
The initial feasibility run compared a masked full view with a lower
bed/approach crop. Neither defines an approved calibration boundary. Review
caregiver-entry coverage in the live dashboard before adopting a crop.

## Meaning and limits of the measurements

- Median and p95 latency include model detection and observation conversion;
  initialization and warmup are excluded.
- Accepted head counts require visible/present face landmarks and reject the
  exclusion region. Shoulder visibility is measured separately; torso absence
  does not invalidate a visible head.
- Pose capacity 1 versus 2 compares computational cost and model output on the
  supplied scenes. It does not validate two actual people, entry/exit,
  occlusion, or confirmed caregiver presence.
- Repeating still-image inference measures repeatability, not temporal tracking
  continuity, identity swaps, or delivered camera FPS. Changing reflected TV
  content and live low-light motion require later safe observations.
- Landmark confidence is not a calibrated accuracy or medical-risk score.

If the samples fail usable head tracking, report that failure and evaluate an
alternative local head/person model before adopting safety thresholds. Camera
sample visibility alone is not proof of useful pose-model detection.

## Worker fault behavior

Missing model files, initialization failure, or missing callbacks become visible
detector faults. A scene edit increments a generation and discards old results.
The callback retains the original crop for coordinate mapping. The worker does
not block the Qt thread on model startup or inference. Startup that has not
completed after 15 seconds becomes a visible fault when status is read. `ready`
and `is_alive` distinguish model readiness from a still-running native thread.

Closing waits at most one second and returns whether the daemon worker actually
stopped. An unfinished worker remains referenced by the dashboard and prevents
replacement inference workers until it exits. It is not silently discarded or
reused; this avoids accumulating hung model instances after repeated retries.
If it does not stop, the visible fault directs the user to exit/restart the
application before retrying. A native library hang cannot be forcibly repaired
inside a Python thread. There is no native process isolation in Milestone 0;
separate process supervision belongs to the later watchdog milestone, and
long-running recovery still needs supervised testing.
