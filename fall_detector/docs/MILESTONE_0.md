# Milestone 0 — Foundation and camera feasibility

Measured October 4, 2026 on the approved Windows 11 PC: i7-12700F, RTX 3080,
approximately 32 GB RAM, and connected Logitech C920. Inference used the CPU
delegate; the GPU was not used. Python 3.12.8, MediaPipe 1.0.1, PySide6 6.11.2,
OpenCV contrib 4.12.0.88, and NumPy 2.2.6 passed import and dependency checks in
the isolated `.venv`. Exact dependency pins are in `requirements.lock`.

## Implemented scope

- Tray start, single-click live dashboard restoration, continued processing
  while hidden, large one-pointer controls, and no-tray taskbar fallback.
- Latest-frame, memory-only capture in a supervised child process. Driver
  open/read hangs do not block the Qt event loop. Capture exposes negotiated
  format, delivered/received FPS, frame age, read failures, reconnects,
  brightness, exposure readback, blur, and estimated cadence gaps.
- Normalized two-tap ROI and exclusion rectangles, masks applied before
  inference, crop-to-full-frame coordinate mapping, and local settings revisions.
- Asynchronous Full pose observations, candidate association, duplicate
  rejection, explicit identity uncertainty, and stale-result rejection. No
  caregiver identity or danger classification is inferred.
- Always-visible selected app-volume decrease/increase and manual test/stop
  sound controls. Windows system volume/mute is not modified in this milestone.
- Privacy exclusions, read-only staged-file gate, and synthetic automated tests.

No emergency messages, recordings, calibration capture, incident database,
startup registration, real choking behavior, or caregiver audio switching are
implemented. The approved blueprint behavior is preserved for later milestones.

## Camera results

Each matrix window used five seconds of warmup and twenty seconds of measurement.
All successful tests used camera index 0 at 1920 × 1080. No imagery was saved.

The initial request order applied MJPG before resolution/FPS. DirectShow reverted
to YUY2 and delivered about 5 FPS at both requested rates. Requesting MJPG last
corrected the negotiated format without changing exposure, focus, brightness,
or other camera controls.

| Backend / requested rate | Negotiated format | Delivered FPS | Read failures / reconnects | Result |
| --- | --- | ---: | --- | --- |
| DirectShow / 15 FPS after fix | MJPG | 14.05 | 0 / 0 | Short capture window passed |
| DirectShow / 30 FPS after fix | MJPG | 13.84 | 0 / 0 | Short capture window passed; no rate benefit |
| Media Foundation / 15 FPS initial trial | No first frame | — | One bounded restart attempt | Startup timed out |
| Media Foundation / 30 FPS initial trial | No first frame | — | One bounded restart attempt | Startup timed out |

DirectShow/15 FPS is the provisional default. The advertised 30 FPS property
was not proof of delivered frame rate. The reason for the remaining rate
limitation is not established; exposure/lighting, driver, and USB behavior need
later observation. Mean frame age at parent receipt was about 44 ms in the
successful post-fix windows, with observed maxima around 203 ms. Timestamping
follows `read()` completion; sensor-to-display latency remains unmeasured.
Estimated cadence gaps are not verified camera/driver frame-drop counts.

This is short-run feasibility evidence, not a 24-hour stability pass. No physical
unplug, restart, UPS, or camera-contention experiment was required of Tyler.

## Supplied lighting photographs

Two ordinary supplied photographs were opened read-only outside the checkout.
These were **not instructed leaning tests**. No movement or airway-obstructing
posture was requested. There were ten repeated image-mode evaluations per
configuration after two warmup evaluations, using unchanged confidence
thresholds of 0.5. Repetitions are not independent physical scenarios.

The exploratory reflection mask and lower crop were local benchmark inputs,
not approved calibration boundaries or embedded public configuration.

| Model / scene | Sample 1 accepted head | Sample 2 accepted head | Median latency at capacity 1 / 2 |
| --- | --- | --- | --- |
| Lite / full masked | 0 of 10 | 10 of 10 | Sample 1: 18.13 / 18.07 ms; sample 2: 18.10 / 47.22 ms |
| Full / full masked | 10 of 10 | 10 of 10 | Sample 1: 55.68 / 55.74 ms; sample 2: 54.80 / 54.64 ms |
| Heavy / full masked | 0 of 10 | 0 of 10 | Sample 1: 144.88 / 135.05 ms; sample 2: 140.94 / 140.84 ms |
| Lite / lower crop masked | 0 of 10 | 10 of 10 | Sample 1: 9.38 / 26.25 ms; sample 2: 17.95 / 47.11 ms |
| Full / lower crop masked | 0 of 10 | 10 of 10 | Sample 1: 25.41 / 25.24 ms; sample 2: 55.99 / 55.20 ms |
| Heavy / lower crop masked | 0 of 10 | 0 of 10 | Sample 1: 26.04 / 26.22 ms; sample 2: 139.56 / 137.60 ms |

Full/full-frame is the initial model/view choice. Whenever Full accepted a head
in these photographs, it also produced accepted shoulder landmarks. The model
confidence scores are visibility/presence estimates, not calibrated accuracy.
The failed crop is concrete evidence against assuming cropping always improves
tracking; it does not change the approved requirement to support editable ROIs.

Pose capacity two was tested on **one real person**. Tyler explicitly deferred
caregiver-entry samples, so simultaneous two-person tracking, entry/exit,
occlusion recovery, and identity swaps remain unvalidated. Reflection suppression
was exercised on the supplied frames, not across changing TV content. There is
no claim of lean/collapse detection performance.

## Integrated Windows smoke check

A bounded sixteen-second ordinary live run started with the dashboard hidden
and the native Windows tray available. It reported 1920 × 1080 MJPG at 14.30 FPS,
zero read failures/reconnects, and a ready Full model. The inference mailbox
reported 111 submitted / 109 completed / 2 replaced pending inputs. The final
result had one accepted head, with approximately 47 ms inference/conversion
latency. Restoring the dashboard while processing succeeded. No frame or overlay
was saved. This one short run does not establish continuous tracking accuracy.

The actual Windows no-camera dashboard was visually checked at the machine's
display scaling. Automated offscreen tests cover tray restoration, continued
hidden processing, region taps/letterboxing, stale overlays, selected volume,
append-only settings, delayed results, hung workers, and responsive cleanup.

## Deferred work

- Caregiver-entry and real two-person sequence validation, as requested.
- Guided safe posture calibration and replay data: Milestone 1, after approval.
- Risk/state/audio priority behavior: later approved milestones; preserve
  caregiver silence above choking maximum volume and restore prior audio on
  departure independently of armed/monitoring state.
- Sustained capture, worst-light motion, changing reflections, physical device
  failure, and watchdog recovery validation before any live caregiver alerts.

No approved safety behavior was redesigned. The Full model is a feasibility
choice; its original model card excludes life-critical decisions and its
limitations remain documented in `MODELS.md`.
