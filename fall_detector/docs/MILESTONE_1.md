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

## Separately approved desktop-launch and relocation follow-up

Tyler reported the missing-model warning again from the Desktop launch and a
partially visible bottom replay control. He approved moving the working copy to
`C:\Codex Projects\Tyler Safety Monitor` and updating the existing shortcut while
retaining the OneDrive original. The full Git repository and isolated environment
were copied and verified; only copied environment path references and associated
metadata were updated. No global Python packages were changed or reinstalled.
Saved models/settings/calibration remain in AppData.

The launcher now passes the existing Full model explicitly and prevents bytecode
writes. Its camera-free integration regression executes the actual command file
with spaced synthetic paths. No startup download or model replacement was added.
The earlier desktop dashboard showed both missing-model and default-settings
status despite the expected files existing; the underlying cause and OneDrive
involvement remain unconfirmed.

Screen-fit changes preserve 60-pixel buttons while allowing the preview to shrink,
wrapping passive notes, putting the volume label above its buttons and limiting
initial size to the available display area. The bottom replay button's vertical
bounds and essential controls are tested at reduced usable height. All 211
synthetic tests and dependency checks passed in the relocated copy. An agent-launched check of the
updated Desktop shortcut passed a short live check: pose inference and a
head-candidate overlay were present, saved settings/reflection mask loaded, and
the final replay control was fully visible after scrolling. The monitor was left
minimized with capture idle and ordinary processing continuing. No new feature
capture or imagery recording was performed for this repair. Sustained stability
and safety-recognition accuracy remain unvalidated.

## Desktop launch runtime-data correction — October 5, 2026

The missing-model warning recurred in Tyler's own Desktop launch after the earlier
agent-launched checks passed. In-process diagnostics established the cause: the
Desktop process returned Windows path-not-found errors for both the model and
settings directories, while the agent-launched process resolved those logical
AppData paths to Codex's packaged-app LocalCache. Matching LOCALAPPDATA environment
strings and explicit model arguments did not imply the same physical files.
Windows handle final paths exposed the redirection. OneDrive was not the cause of
this recurrence. See [Microsoft's packaged desktop app filesystem documentation](https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-behind-the-scenes).

Tyler explicitly approved copying the eight existing private runtime files (three
models, one settings revision, two profiles and two feature replays) into ordinary
host AppData. A one-time helper ran through Tyler's Desktop launch, preflighted all
source hashes and destinations, used exclusive creates, and checked every copied
file plus its original afterward. Existing destination files were never replaced;
all cached originals remain. Its temporary launcher step was removed after the
verified copy. No package reinstall, new download, feature collection or imagery
recording was needed.

The resulting user-launched dashboard read the Full model from ordinary AppData,
loaded saved settings and completed live pose inference (over 700 results at the
check), with camera live and calibration idle. This directly validates Tyler's
Desktop launch, rather than an agent-spawned process. It does not validate safety
classification, long-term stability or personalized thresholds. Milestone 2 remains
unapproved.

The application now has an optional `--diagnostics` switch. It creates one exclusive
JSON file beneath the effective AppData diagnostics directory with startup paths,
module locations, selected LOCALAPPDATA values and model/directory file checks,
including Windows errors and handle final paths/identities. It does not retain
model bytes, settings contents, features, camera images or other environment values.
Normal Desktop launches do not enable it. Diagnostic reports are private and must
never enter Git. All 213 synthetic tests passed after this follow-up.

For future real camera/calibration sessions, prefer Tyler's ordinary Desktop launch.
An agent's packaged-app filesystem view can still expose retained cached revisions;
do not treat matching environment strings, a shell `exists` check, or a successful
agent-spawned dashboard as proof of the user process's physical runtime location.
Inspect handle final paths using a user-launched `--diagnostics` session if another
file-visibility issue appears. Preserve both runtime copies; do not silently merge,
replace or delete revisions.


## Tracking stability follow-up — October 5, 2026

Tyler reported rapid changes between detected and uncertain head markers at his
current tolerable nighttime lighting, including while still. The temporary
smaller-ROI experiment did not establish stability; the original full-frame ROI
was restored without saving settings or collecting new features.

The approved repair adds bounded in-memory counts, replaces greedy association
with maximum-cardinality/minimum-distance one-to-one assignment, and keeps
conservative duplicate/crossing uncertainty and continuity resets. A synthetic
counterexample demonstrated that greedy matching created a new ID despite a
valid two-track assignment. Exhaustive small-graph tests verify the new objective.
No visibility thresholds, model parameters, calibration provenance or approved
personal files changed.

A currently detected head has a cyan ring independently of amber uncertain-ID
text. Missing heads are never held forward as current detections. Candidate
selection rows now update by ID instead of rebuilding each batch. A selected
missing candidate remains explicitly unavailable; it is never silently replaced
by another candidate. Capture still requires a current unambiguous observation.
Camera restart/pause, scene changes and New Session clear obsolete selections.

Two short user-launched checks demonstrated separate causes: an initial 10-second
window had 133 observation batches, no missing-head batch, 101 duplicate batches
and 33 ambiguous-match batches. A later 132-batch window after the association
repair had 33 missing-head batches, 7 duplicate batches and no ambiguous-match
batch. These are uncontrolled short samples, not comparable accuracy scores.
Tyler still reported marker churn. Genuine head-loss is unresolved; the ID/UI
repair must not be described as fixing native detection or establishing safety.

The Camera / Masks panel includes ten-second model counts distinguishing no
native pose from a native pose with all heads rejected by validation. Counts and
booleans are bounded in memory; no images, additional coordinates or logs are
saved. Scene edits clear these counts, and late old-scene callbacks cannot refill
them. A fresh ordinary Desktop launch on October 6 loaded the new counters.
Two ten-second windows had 52/129 and 81/132 native no-pose results respectively,
with zero pose-present/head-rejected results in both. Camera delivery stayed
13.8–14.0 FPS with no read failures or inference skips. Calibration was idle.
These short windows establish that the observed remaining gaps came from native
pose absence, not the application head filter. They are not accuracy estimates.
Tyler reported that the behavior seemed quite a lot better after the ID/display
repair; that subjective improvement does not establish stable head detection.
All 227 synthetic tests passed; independent review found no concrete regression
in association, selection or current-scene diagnostic counters.

A read-only exploratory Google BlazeFace Full Range trial used three previously
supplied dashboard screenshots, cropping/rotating only in memory. A new official
model was stored in isolated private scratch, outside Git; global packages and
ordinary AppData models were unchanged. Full and lower views returned no face in
10 repeated inferences per sample. A closer, rotated view returned one face in
the night sample in a single exploratory inference. This is a lead for a separate
live comparison, not evidence of sustained tracking, validated identity or a
replacement for Full. No alternative detector is enabled in the application.
Model/pipeline changes must preserve provenance and must not silently make old
profiles operational under a different measurement. See docs/MODELS.md for
source and limitations. Milestone 2 remains unapproved.


## Optional head-focused comparison — October 6, 2026

The tracking-repair approval included evaluating a head-focused detector if Full
kept losing the head. The new Camera / Masks actions **Start Experimental Head
Comparison** and **Stop Head Comparison** provide that separate diagnostic. It
is off on normal startup and never replaces Full pose tracks or assigns person
IDs. Magenta squares show current face estimates and face-model scores; they are
not pose visibility or safety confidence. Feature capture is blocked during
preparation/comparison. Existing profiles and feature files remain untouched.

The explicit Start action downloads the reviewed Google BlazeFace Full Range
artifact (~1.1 MB) only if its separate local model file is missing. SHA256 and
TFLite format are checked before an exclusive create. Existing bytes are validated
read-only; unexpected bytes or a changed remote digest fail visibly without
replacement. No download occurs during normal app startup. The ordinary Desktop
process performs acquisition in its own runtime namespace, avoiding inference
about file visibility from Codex's redirected AppData view.

A background worker scans the currently masked ROI and generic overlapping tiles
at zero and +/-30-degree rotations, with submissions and scans capped at two per
second. Coordinates are mapped back through inverse rotation and rounded ROI
bounds, then checked against the original scene/masks. Diagnostic proximity
suppression and a 16-estimate bound do not establish person count or identity.
There is one active scan and one replaceable copied pending frame; no imagery or
experimental coordinates are saved. Current-scene counts expire after ten
seconds. Scene edits discard old results. Pause/replay stop comparison, late
preparation cannot restart it, and a hung worker remains referenced and blocks
replacement. Missing, stale or faulted estimates disappear from the overlay.

All 256 synthetic tests passed, including acquisition preservation, inverse
mapping, masks, rate/queue bounds, old-scene results, native timeout/close,
separate overlays and blocked capture. Independent review found no concrete
privacy/thread/data regression. A native worker smoke test on the three previously
supplied screenshot previews produced one diagnostic estimate per sample in
approximately 141–156 ms per 30-view scan. The night estimate was outside the
expected head region; the trial therefore does not establish useful nighttime
head recognition. Its purpose is comparison, not a proven repair. Live CPU cost,
pose cadence, false detections and sustained detection must be checked separately.

Tyler's additional object masks temporarily appeared to reduce ID churn. Short
native no-pose counts fluctuated, including a zero-miss window followed by a
93/132-miss window, and Tyler reported that ID churn returned. The nightstand
hypothesis remains plausible but unconfirmed. At his explicit request he saved
the current masks as a new settings revision; earlier revisions and calibration
files were retained. Treat these masks as experimental. A masked caregiver head
cannot be detected in that area; review caregiver coverage and distinguish loss
of visibility from confirmed departure before operational use. Actual caregiver
participation remains deferred to supervised validation. No live safety logic or
Milestone 2 work is enabled by this comparison.

## Experimental score filtering — October 6, 2026

The separate face comparison now offers 50% (baseline), 80%, and 90% score
cutoffs. These are detector scores, not probabilities of matching Tyler or
being safe. The default remains 50%; this session-only control does not change
Full pose thresholds, settings revisions, identity association, or calibration.
Changing the cutoff clears current overlays, pending results and recent counts;
old in-flight results cannot appear under the new cutoff. A score-rejected-only
counter distinguishes batches that had mapped estimates but none above the
cutoff from other batches without a qualifying face.

An ordinary Desktop live view at 50% showed an estimate near Tyler's head and
an additional approximately 79% estimate over a pillow. Zero no-face samples
therefore did not establish continuous recognition of Tyler. Camera delivery
remained approximately 14 FPS without read failures; Full pose still had native
no-pose gaps. An 80% cutoff needs a fresh live location check: rejecting the
pillow estimate alone does not prove that genuine head estimates remain usable.

All 271 synthetic tests passed, including cutoff validation, 79% rejection and
94% retention at 80%, stale-result invalidation, counter expiration and UI
isolation. Independent review found no concrete regression. No new imagery,
personal calibration features, or safety decisions were recorded or enabled.
Milestone 2 remains unapproved. The ordinary Desktop cutoff check below is complete; sustained tracking remains unverified.
### Ordinary Desktop check at 80%

After the user restarted the usual Desktop shortcut, the new selector showed
80% and the comparison ran without a model warning. Two unobstructed live
previews showed a magenta estimate on the head, approximately 89% and 90%,
with no additional pillow estimate visible in either preview. Three recent
qualification counters read 3/19, 0/19, and 1/19 missing samples; the gaps were
score-only rejections. Full pose still reported 73/133, 54/129, and 77/130
native no-pose results. These are differently sampled diagnostic windows, not
identity accuracy measurements. Camera delivery remained approximately 14 FPS,
with zero read failures/reconnects and no comparison queue replacements.

The third screenshot was occluded by another window; only its accessibility
counters could be checked. No continuous visual correctness was established.
Leave 80% as the current experimental starting point; 90% could reject the
valid approximately 89% head estimate. The comparison remains separate from
Full association, so this check does not resolve cyan-ID churn, authorize a
new measurement for existing profiles, or enable safety classification. No
settings/profile save or feature capture was performed during this check.
Further work should assess ordinary-position variation, false estimates and
longer gaps before adopting any new tracking measurement.