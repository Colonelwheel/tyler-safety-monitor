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


## Exploratory head-focused comparison — October 5, 2026

The live Full pose detector intermittently lost accepted heads even while Tyler
was still at his tolerable nighttime lighting. Association/UI repairs do not
establish native head-detection stability. Before changing the model or rejecting
thresholds, use the in-memory last-ten-second counts to distinguish a native
no-pose result from a pose whose head fails validation. Neither can be hidden by
holding an old head position as current.

An isolated read-only trial examined Google's [Face Detector guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_detector),
[Python API](https://developers.google.com/edge/mediapipe/solutions/vision/face_detector/python)
and [BlazeFace Full Range model card](https://storage.googleapis.com/mediapipe-assets/MediaPipe%20BlazeFace%20Model%20Card%20%28Full%20Range%29.pdf).
The official full-range artifact was downloaded only to fresh private scratch;
no artifact is included in Git, no existing model was overwritten, and no Python
package changed. Artifact SHA256:
`3698b18f063835bc609069ef052228fbe86d9c9a6dc8dcb7c7c2d69aed2b181b`.
This digest records tested bytes, not a publisher signature. The model card lists
Apache 2.0 and limitations involving face orientation/size, low light and jitter.

Three previously supplied dashboard screenshot previews were read without
modification. Full and lower views returned zero faces in 10 repeated IMAGE
inferences per view/sample. Exploratory closer crops with rotation returned a
face in the night sample only at one tested orientation. That single transformed
still result is not temporal validation or proof of a correctly associated
person. All transforms were in memory; no imagery or coordinates were written.
The source imagery remains outside Git. The app still uses Full pose only.

A future live head-focused comparison should keep experimental observations
separate from pose tracks, profile eligibility and danger decisions, map current
coordinates back to the original frame, and record actual model/pipeline
provenance for any subsequently approved collection. Do not relabel face
confidence as pose visibility or safety confidence. Do not adopt a smaller ROI
without reviewing coverage of separate people and usual head movements.


The optional live comparison is now implemented, off by default, using the above
verified artifact. **Start Experimental Head Comparison** explicitly prepares
one separate local model if missing and starts the diagnostic worker; normal
startup downloads nothing. Each sample scans the masked ROI plus nine generic
overlapping half-size tiles at 0/+30/-30 degrees. Scan/submission rate is capped
at two per second; current estimates are spatially suppressed and bounded to 16.
The worker uses the nose keypoint (or unavailable-keypoint box centre), reverses
rotation/crop, and rejects original-scene exclusions and rotation padding. Face
confidence remains a different measurement from pose landmark visibility.

A native smoke test of this implemented worker on the three supplied screenshot
previews returned one estimate per sample with 141–156 ms scans. The night sample's
estimate fell outside the expected head region. Do not treat the count of one as
successful recognition of Tyler. The separate magenta overlay allows an ordinary
Desktop live comparison of location, gaps, false estimates and CPU/cadence cost.
No experimental detections are used by pose association, profile/feature saving
or danger decisions. Feature capture is disabled while comparison is preparing,
running or still stopping; Stop Head Comparison restores the ordinary workflow
once the worker has stopped. Existing calibration provenance is unchanged.

The experimental score selector offers 50% (baseline), 80%, and 90%. Scores are
not probabilities of matching a person. Changing the session-only cutoff clears
old estimates and counters; Full pose tracking and saved calibration remain
unchanged. The status distinguishes score-only rejection from other missing
estimates. Inspect the magenta estimate locations: a false pillow estimate can
keep a no-face counter at zero. Higher cutoffs also risk dropping genuine heads.