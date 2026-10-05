# Milestone 1 — Calibration and recorded-data harness

Implemented October 5, 2026 after Tyler approved the source/documentation plan.
The separate implementation approval did not authorize real collection. No live
camera session, personalized feature capture, imagery recording, or real clip
analysis was performed during this milestone. No caregiver participation was
requested. This remains observation tooling with all emergency actions disabled.

## Usable tooling

- Calibration/Replay tab beside the existing Camera/Masks tab; existing tray,
  large manual app-volume controls, test/stop sound and fault behavior retained.
- Guided ordinary safe posture, routine adjustments, optional already-safe
  head-down/recovery, and darkest-light ordinary-posture steps. Assisted and
  caregiver scenarios explicitly remain pending.
- Separate visible user approval before feature collection, a five-second
  delay, a 15-second per-step maximum, and always-visible Stop/Review. Hiding,
  minimizing, camera pause, scene changes, and stale/faulted observations stop
  collection and retain collected in-memory data for review.
- Features contain original capture-read-completion time, camera frame index,
  separate inference timestamp, safe-step label, normalized landmarks,
  visibility/presence and head confidence. No camera images/audio are written.
- New, exclusive local profile/feature files only after save confirmation,
  beneath `%LOCALAPPDATA%\TylerSafetyMonitor\calibration\profiles` and `replays`.
  Earlier saved files and unrelated files are preserved; unsaved data remains
  in memory and is lost on application exit. New Session asks before clearing
  in-memory edits and never removes saved files.
- Strict versioned profiles retain scene/model hashes, camera source/dimensions,
  dependency versions, capture-step coverage, normalized zones, and proposed /
  reviewed status. No danger zones or timing classifications are synthesized.
  Loaded overlays require matching available camera/model/dimensions/scene
  metadata, and cannot verify physical camera placement by themselves.
- Observed safe/intentional-lean envelopes, two-tap zone editing, and explicit
  per-zone visual review. Flat or empty point sets require manual geometry
  review rather than an invented envelope. Person candidates remain unconfirmed;
  a session cannot change its candidate or camera source and mix samples.
- An intentional-lean variation control starts at zero, in 0.1% original-frame
  steps up to 2%. The UI editor range is not an anatomical distance or an
  accepted safety threshold. Changes invalidate lean review; hard danger zones
  remain unchanged. Final boundaries require Tyler's review and physical
  validation. The approved 30-second ordinary-lean grace belongs to Milestone 2
  and cannot compensate for incorrectly recognized severe positions.
- Synthetic demo plus approved-local-feature replay with its own clock,
  Play/Pause, rewind, original aspect ratio, landmark confidence and candidate
  paths broken across gaps, missing observations and ambiguous association.
- Explicit local clip-to-feature CLI using ordered MediaPipe VIDEO inference
  in an owned child process with a bounded total deadline. Original source
  clip/model remain read-only. Optional sidecar source times preserve irregular
  camera cadence; nominal clip FPS is labeled when actual times are unavailable.
  Output is a new private feature JSON, never video/overlay media.

## Verification

- 208 automated synthetic component/integration tests passed with isolated
  fresh scratch directories and bytecode/cache writes disabled. Tests include
  the original foundation suite and new profile preservation/validation,
  malformed/deeply nested files, score metadata, replay timing/coordinates,
  missing/uncertain tracks, countdown/delay, separate consent, candidate/source
  changes, minimized capture stop, and large one-pointer controls.
- Mocked clip inference verifies ordered frame processing, actual source times,
  crop/full-scene mapping and unchanged source inputs. No real clips/models are
  used by these tests.
- Offscreen Qt visual rendering with a synthetic two-candidate replay checked
  the accessible tab layout, always-visible Stop/Review and volume row, and
  absence of horizontal scrolling. Windows' existing Segoe UI font was loaded
  read-only for the sandbox render. Synthetic screenshots remain ignored scratch
  artifacts; no room imagery was rendered or saved.
- Existing isolated Python 3.12.8 dependency pins were unchanged; `pip check`
  passed. No installations, global package changes, environment recreation,
  camera settings changes, startup entries, or Windows audio changes occurred.
- The staged privacy gate and manual final diff review exclude private media,
  models, runtime JSON/JSONL, scratch files, logs and credentials. Root website
  HTML/CSS was not changed; no hosting/URL change is part of this milestone.

## Current environment and limits

At initial inspection, no detector process was running and Streamlabs OBS was
running. Windows camera-use metadata did not establish current C920 ownership;
do not launch a competing hardware test without checking the actual owner.
The private runtime directory had local Full/Lite/Heavy models and the plotting
cache, but no saved settings/calibration/replay files. Its default reflection
mask therefore still needs actual review. No existing runtime data was changed.

The earlier 1080p MJPG DirectShow / requested 15 FPS and Full/two-pose choices
are retained. Their approximately 14 delivered FPS result is historical Milestone
0 evidence, not a new hardware measurement. No sustained 24-hour gate, live
feature-capture test, physical one-finger trial, darkest-light motion test, true
two-person validation, or personalized margin/boundary review passed here.

Feature replay has no camera image background. Approved clip analysis produces
features for replay, rather than an imagery playback/recording UI. This avoids
needing new imagery-saving approval. No real-time capture-export video writer
was added. Strict sample/byte/duration limits make overly long sessions visible
errors rather than silently truncating their contents; use a new session after
saving. Live inference still skips busy frames, while offline clip inference
processes all decoded frames in order. Capture timestamps are read completion,
not sensor exposure timestamps.

Native live inference remains threaded. The existing unfinished-worker guard
blocks replacement until it exits; a hung worker requires application restart.
The offline CLI owns only its analysis process and can stop that process at its
deadline. The independent service watchdog remains Milestone 5 work.

## Next safe action

First use the no-camera launch in the detector README and **Synthetic Replay
Demo**. No head movement is needed. Then check camera ownership and actual mask
coverage before a separately approved ordinary-safe-posture feature session.
Explain and agree on each capture step before Tyler moves. Optional already-safe
head-down/recovery comes later when he is ready; do not request a 30-second hold,
maximum-depth position, or airway-obstructing posture. Saving camera imagery
still needs separate destination-and-scope approval. Caregiver/assisted data
remains deferred to supervised validation, normally Milestone 6.

Milestone 2 source implementation needs new approval. Its deterministic simulated
state machine may start with synthetic sequences and uncalibrated status; no
unreviewed personal boundaries may become operational thresholds, and no live
caregiver alerts may be enabled.

## Separately approved live follow-up — October 5, 2026

After implementation, Tyler separately approved feature-only collection and
new private profile/replay files, then session-limited dashboard screenshot
inspection. Ordinary posture and optional already-safe head-down/recovery
captures completed through the visible guided controls. Both saved profile and
feature schemas validated; person observations were present throughout these
short samples. The two steps remain separate saved sessions after application
restart. All actual geometry, features, filenames and imagery stay outside Git.
No camera images or audio were recorded by the monitor. A new local reflection-mask
settings revision was saved, preserving earlier files.

A running dashboard reported the Full model missing even though its file was
readable and a camera-free initialization succeeded. Application restart
restored live tracking; a subsequent normal launch with the default model also
worked and loaded the saved mask. The original failure's cause was not confirmed;
no model download, reinstall or model-path source change was needed. The normal
application was left running with no active capture. Recheck ownership and health
before resuming.

Saving exposed a status-label layout defect: long Windows filenames widened the
calibration panel and hid controls. Tyler approved a targeted follow-up fix. The
label now permits horizontal shrinking and displays a compact save confirmation;
exact paths remain in its tooltip and accessible description. Those details clear
on later status updates. All 209 synthetic tests passed, including a regression
that long save paths do not increase the panel width or horizontal scroll range.
The revised label has not yet been checked in the live application after restart.

Tyler requested continuation later. Saved profiles have no reviewed zones and
retain zero lean margin. A possible small allowance was discussed but not applied
or approved as a threshold. Review proposed envelopes and day-to-day allowance
from the existing private features next; do not require repeated movements just
to recover these samples. Routine-adjustment/darkest-light collection, assisted
boundaries, real caregiver/two-person validation and sustained stability remain
pending. These short captures establish no safety accuracy or live-alert approval.
The tracked head-position ranges overlap; the optional step includes recovery.
There is measurable movement, but reliable posture discrimination is not yet
demonstrated. Evaluate tilt as well as position using replay before treating a
personal zone or allowance as suitable for detection.
