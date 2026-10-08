# Next-chat handoff — Milestone 3: accessible warnings and controls

Updated: October 7, 2026.

## Latest follow-up: scroll protection and individual mask removal

Tyler requested and approved fixing right-panel wheel input changing options,
then separately approved individual exclusion removal. The live inspection saw
requested FPS switch from 15 to 30 during scrolling; Tyler chose to keep 30.
No setting save, camera retry, capture or real mask removal was performed by the
agent. The previous camera-layout repair is now observed in the ordinary Desktop
launch: the picture is unobstructed and counter/control placement is visible.
This does not establish continuous tracking accuracy.

New PanelWheelGuard protects all closed combos/spin fields and numeric editors
in Camera, Calibration and Simulation. Wheel and pixel-only input scroll the
panel while deliberate popup selection, typing and arrows remain available.
Camera number 0 is visibly labeled as the first camera. Numbered masks support
Remove Selected Mask -> tap -> default-No confirmation with 60-pixel buttons.
Only one index is removed; other masks/ROI and saved revisions remain intact.
Overlapping taps are rejected rather than guessing; fully overlapping masks
cannot be selected by this tap tool. Capture/replay and changed-scene confirmation
guards prevent stale deletion. Save Settings remains separately explicit.

All **457 synthetic tests passed** in fresh isolated scratch. Computer Use was
reset after active inspection, before coding/testing. New source still needs a
user-convenient restart/live scroll check; preserve unsaved settings/features.
Independent review found no concrete defect; the seven-file staged privacy and
whitespace checks passed. Public website and dependency pins are unchanged.
Milestone 3 and new personal capture remain unapproved. All real texts, including
test messages, stay deferred to Milestone 6 unless separately approved earlier.

## Current handoff: Milestone 2 complete within its simulated scope

Tyler approved the simulated Milestone 2 source, interface, replay, tests and
documentation on October 7. The final full suite passed 430 synthetic tests,
the dependency check passed, and independent review found no remaining concrete
source defect after fixes and regression coverage. The 19-file staged privacy
review and staged whitespace check passed. No physical validation or
safety-readiness claim is implied.
Read `fall_detector/docs/MILESTONE_2.md` for scope and limitations. The earlier
Milestone 2 opening prompt below is historical, not a request to reimplement it.

Milestone 2 shows what would happen, without messaging or automatic audio. It
tests fixed warning deadlines through recognition gaps, positive recovery,
strict two-second caregiver confirmation, retained caregiver silence during
uncertainty, supported paired exit, independent simulated audio restoration,
30-second safe rearm, Night/manual commands and faults. It does not validate
recognition or approve personal thresholds. Existing approved features remain
read-only, uncalibrated and unknown; saved schemas/bytes are preserved.

Tyler additionally requested live second-person diagnostics. The main dashboard
now displays a candidate, observed 0.0-2.0 seconds, reset count and restart reason.
Use Calibration / Replay to designate Tyler first. This diagnostic is independent
of simulated/real caregiver suppression and saves nothing. Current evidence loss
resets the counter even after qualification; a retained simulated caregiver audio
latch is separately shown as uncertain when fresh evidence is absent. Actual
ordinary Desktop/caregiver validation remains pending.

Tyler separately approved: automatic posture recovery must never cancel a
manual choking incident. Explicit Cancel/Resolve, a valid caregiver reply, or
confirmed caregiver presence stops repeats. An immediate manual choking intent
remains possible in every mode. Existing caregiver suppression must not resume
repeats or choking maximum-volume intent merely because the caregiver departs.

Tyler reports that brighter conditions currently track reliably and dim light
causes flicker. Simulated development is independent of lighting. Physical
dim-light validation is deferred until those conditions return. No new capture,
movement request, caregiver session, model fusion or confidence-policy acceptance
is implied. Experimental face comparison remains separate from Full calibration.

## October 7 follow-up: live-view layout repair and text deferral

Tyler approved fixing controls/status text obstructing the live camera view.
The ordinary Desktop screenshot showed overlap on the short/scaled window.
Detailed camera statistics, candidate notes and landmark legend now live in
Camera / Masks; compact camera status and pose faults stay visible. The live
two-second counter stays above the side tabs. Volume controls use one row when
captions fit and two rows on narrower/scaled layouts. Simulation explanations
and effect details scroll while current state/countdown and Cancel/Play stay
visible. No tracking, capture, saved settings or alert behavior changed.

Synthetic geometry checks cover window bounds, picture/control separation,
usable preview size, large buttons, persistent counter on all tabs and simulation
Cancel/Play at 1260x640, 1100x600 and enlarged text. Actual post-restart Desktop
layout remains to be verified. Preserve current unsaved edits/features and do
not automatically restart the running monitor just to load this repair.
The final isolated suite passed **433 tests**, the dependency check passed and
independent review found no remaining concrete layout regression. Synthetic
preview QA used the existing Windows UI font; actual camera imagery was not saved.
The eight-file staged privacy review and whitespace check passed; public website
files and dependency pins are unchanged.

Tyler explicitly requested durable rules: end/reset Computer Use before coding
or waiting unless an active UI action needs it. Defer **all real texts, including
test texts, to Milestone 6** unless separately approved earlier. Milestone 4
builds simulated messaging first; real recipient/message checks and supervised
delivery/reply tests precede separately approved automatic live arming.

## Ready-to-use next-chat prompt

> Continue Tyler Safety Monitor in C:\Codex Projects\Tyler Safety Monitor. Read
> fall_detector/docs/TRACKING_REPAIR_CHECKPOINT.md first, then every project-authored
> Markdown document, including AGENTS.md, FALL_DETECTOR_BLUEPRINT.md,
> NEXT_CHAT_HANDOFF.md and fall_detector/docs/MILESTONE_2.md. The blueprint plus
> Tyler's October 7 choking clarification are the approved baseline.
>
> Inspect current Git/source/tests and propose Milestone 3: actual accessible
> warning screen, speech/sounds and one-action controls in test mode. Ask before
> source changes. This handoff does not approve Milestone 3, actual Windows audio
> switching, real messaging, recording, startup/watchdog or new personal collection.
>
> Preserve the separate simulated engine, fixed timers through uncertainty,
> caregiver-confirmation/departure rules and choking cancellation clarification.
> Preserve the requested live diagnostic two-second counter and explicit
> candidate-only labels; it must not become operational caregiver recognition.
> Caregiver silence overrides choking; reliable departure restores saved audio
> independently of armed state. Keep essential one-pointer controls visible.
> Propose any actual audio work explicitly before implementation. No caregiver
> session is required now; actual involvement stays deferred to Milestone 6 unless
> a concrete earlier dependency is explained and agreed upon.
> Keep all real SMS, including test texts, deferred to Milestone 6 unless Tyler
> separately approves an earlier test. Use simulated messaging in Milestone 4.
> Use Computer Use only for active inspection/actions; end/reset it before
> coding, testing or waiting unless a current UI action needs it.
>
> Keep personal boundaries unapproved and existing profiles/features/settings/models
> unchanged. Reuse the isolated .venv, preserve the OneDrive backup/global Python
> and root public website. Account for Codex AppData redirection; do not merge
> runtime copies. Use fresh synthetic scratch, verify, review staged privacy,
> update the next handoff/checkpoint, then commit and push with sensible wording.

Current launch: the normal **Tyler Safety Monitor** Desktop shortcut, or the
existing `--no-camera --show` command in `fall_detector/README.md`. Open
**Simulation**, select a scenario, then **Play / Pause Simulation**. Cancel and
Play controls stay outside scrolling. The simulation starts paused and is
independent of live camera/calibration. **Advance 10 Seconds — Simulation** tests
timers without real waiting. No physical movement is needed.

Preferred working copy: `C:\Codex Projects\Tyler Safety Monitor`. Tyler approved
relocation outside OneDrive and updating the existing Desktop shortcut. The
original project and environment remain intact as a backup; continue development
in the local copy. Full Git history and the existing origin were copied. Saved
private AppData files remain at their original locations.

## Historical Milestone 2 opening prompt and earlier evidence

> Continue Tyler Safety Monitor in this existing project. Before changes, discover and read every project-authored Markdown file: AGENTS.md, README.md, PROJECT_ROADMAP.md, FALL_DETECTOR_BLUEPRINT.md, NEXT_CHAT_HANDOFF.md, fall_detector/README.md, and all fall_detector/docs documents. Treat FALL_DETECTOR_BLUEPRINT.md as the approved baseline.
>
> Milestones 0 and 1 tooling are complete. Begin Milestone 2 — Detection state machine only after inspecting current source, Git status, environment, camera ownership and private-data availability. Give a concise implementation plan and ask before its source changes. This handoff does not approve Milestone 2, new personal collection, saving imagery, or live alerts.
>
> Reuse the existing camera/pose/tracker/tray/audio/region foundation and Milestone 1 profile/feature/replay APIs. Keep DirectShow index 0, 1080p MJPG, requested 15 FPS, Full CPU model and capacity two unless new evidence justifies a change. Historical Milestone 0 delivered about 14 FPS; this is not a current hardware measurement. Do not equate visibility/presence scores with safety accuracy or synthetic tracks with validated caregiver recognition.
>
> Implement ordinary-lean, severe warning, slow recovery, caregiver, away, night and fault transitions with deterministic synthetic/approved-feature tests and strictly simulated alert adapters. Preserve the approved 30-second ordinary-lean grace, 10-second ordinary countdown, 8-second severe/manual-fall countdown, two-second separate caregiver persistence, and 30-second stable rearm. No unreviewed profile boundary may become an operational safety threshold. Missing calibration must stay explicit, rather than guessing from old photographs or synthetic test zones.
>
> Tyler clarified that his safe head-down distance can vary slightly day to day; do not anchor final thresholds to today's deepest position. Milestone 1 has a zero-default intentional-lean proposal margin editor (0.1% original-frame steps, maximum 2%). That editor limit is not a safe-distance recommendation or approved safety threshold. Review any actual margin and zones with Tyler. The 30-second ordinary-lean rule does not compensate for misclassifying severe depth. Do not request a 30-second calibration hold, maximum-depth movement, or airway-obstructing posture.
>
> Implementation approval covered synthetic verification only; Tyler later separately approved ordinary-posture and optional already-safe head-down/recovery feature captures. Those two short sessions and their profiles/replays are saved privately under actual host LOCALAPPDATA/TylerSafetyMonitor/calibration. Reuse them for initial envelope review instead of repeating movements. Saved zones are empty/unreviewed and lean margin remains zero; a small proposed allowance still needs review. No camera imagery was recorded. Any new collection requires fresh scope/readiness agreement. Session-limited dashboard screenshot approval from the earlier run does not authorize new-session imagery sharing or recording.
>
> Actual caregiver involvement remains deferred until the latest practical point, normally Milestone 6 supervised validation. Build synthetic tooling and tests first. Leave caregiver-assisted capture pending rather than substituting unsafe solo movement. Agree on the smallest necessary earlier session only if a concrete dependency demands it. Real caregiver and simultaneous two-person validation are required before live alerts. All people remain person candidates until validation.
>
> Preserve always-visible manual app-volume decrease/increase, Test Sound and Stop Sound, one-pointer controls, and the tray behavior. Do not implement Twilio messaging, startup registration or the independent watchdog in Milestone 2. Keep external alerts disabled/simulated. Follow the blueprint for simulated audio priority: caregiver silence outranks choking maximum volume, and reliable departure restores saved audio independently of armed/monitoring/rearm state. Any actual Windows audio-switching implementation must be explicitly included in the proposed scope and approved before changing it.
>
> Preserve the existing isolated fall_detector/.venv and all global Python installations/packages. Keep application work beneath fall_detector/ and root public HTML/CSS/URLs unchanged. Private real data belongs beneath actual host LOCALAPPDATA/TylerSafetyMonitor, outside Git and OneDrive. Never overwrite, remove or alter earlier private files incidentally. Use exclusive new files; obtain specific approval for any replacement/deletion. Use fresh unique synthetic scratch for pytest --basetemp; pytest can delete a reused directory. Sandboxed LOCALAPPDATA may be redirected, so verify the destination before a real capture/save.
>
> Choose sensible commit messages without asking for wording. Use parallel agents when helpful. Run appropriate synthetic tests, separate automated results from physical validation, review final/staged privacy, update this handoff for the next milestone, and commit/push finished work. Stop at the approved scope.

## Current implementation and verification

- Branch/remote: main, https://github.com/Colonelwheel/tyler-safety-monitor.git.
- Foundation implementation: d63aed6; later pre-Milestone-1 documentation baseline: 9e0a3f8.
- Milestone 1: 208 automated synthetic tests passed, dependency check passed, offscreen synthetic dashboard rendering reviewed. See fall_detector/docs/MILESTONE_1.md for exact scope and deferred validation.
- Python 3.12.8 in the existing .venv; dependency pins/environment were not changed. Native models remain outside Git. No new dependencies or model downloads were needed.
- Profiles validate scene/model/camera/dimensions/dependency provenance and preserve proposed/reviewed zones. New revision filenames are exclusive. Features retain source seconds/frame index, separate inference milliseconds, capture-step labels, original normalized coordinates and per-landmark scores.
- Replay uses its own clock, original aspect ratio, candidate association and bounded segmented trajectories. Offline clip analysis is ordered VIDEO inference in an owned bounded process; source clips/models are read-only. Without a capture-time sidecar, clip time is explicitly nominal FPS.
- No personal data was collected during implementation. In a separately approved follow-up, ordinary posture and optional already-safe head-down/recovery features were saved in two separate private sessions. Profile and feature schemas validated with person observations throughout these short samples; this does not establish safety accuracy. No reviewed zones or nonzero margin were saved. Real clip inference, comprehensive physical accessibility testing, personal zone/margin review, caregiver participation and the 24-hour stability gate remain pending.
- Initial implementation inspection found no detector running and did not establish C920 ownership. The later authorized session restored live Full-model head tracking after restarting a dashboard that falsely reported the model missing. A normal default-model launch then worked. The original missing-file cause remains unconfirmed; no reinstall/download or model-path source patch was needed. The normal app was left running, with no active capture, at Tyler's request to continue later. Recheck current ownership/health rather than starting a competing process.
- Private runtime now has saved scene settings with a reflection mask plus separately saved ordinary/intentional-lean profiles and feature sequences. Earlier files were retained. Recheck physical camera placement and mask coverage before reuse; do not publish personalized filenames, geometry or features.
- Tyler approved a narrow save-status layout fix after long Windows paths widened the controls. Compact visible confirmation retains exact paths in tooltip/accessibility description, and its label can shrink without forcing panel growth. All 209 synthetic tests passed. Restart is needed to load this source change; the updated label has not been checked live yet. Preserve the saved sessions before any exit/restart.
- Native live pose inference remains threaded; unfinished/hung workers are retained and block replacement. Preserve this guard. Feature replay itself does not create an inference worker. Watchdog recovery is later work.
- Root website HTML/CSS and public URLs were preserved. Existing local files/global packages, Windows audio/mute, startup entries and camera properties were not changed.

## Launch and first safe action

Normal launch: **Tyler Safety Monitor** Desktop shortcut or `fall_detector/Start Monitor.cmd`, starting minimized. One tray click restores the dashboard. Only one application/camera owner should run.

For a movement-free demo, from the repository root in PowerShell:

```powershell
& .\fall_detector\.venv\Scripts\pythonw.exe -B -m tyler_safety_monitor --no-camera --show
```

Open **Calibration / Replay**, then **Synthetic Replay Demo**, then **Play / Pause Replay**. Replay pauses the camera. **Live View — Camera Stays Paused** does not reopen it automatically.

Next action: inspect current application ownership and private saved profiles/features, then review ordinary/intentional-lean envelopes and the small day-to-day allowance with Tyler. Both initial captures are already saved; do not ask him to repeat them merely because the app restarted. They are separate sessions with matching scene configuration, not a combined reviewed operational profile. Preserve provenance and leave safety-critical boundaries unapproved.

Tyler confirmed that varying sideways head tilts are safe variation by themselves.
An accompanying downward position must still be evaluated independently; lateral
tilt must not itself become a danger trigger or cancel downward evidence. This is
a requirement for later reviewed detection work, not implemented classification.

The observed head-position ranges overlap, and the intentional-lean sequence includes return to ordinary posture. Measurable movement is present, but reliable discrimination has not been demonstrated. Compare head tilt as well as position in saved-feature replay before choosing detection features or accepting a personal allowance.

For any separately agreed new collection: verify ownership, fixed camera and reflection masks; choose a visible unambiguous candidate and explain the safe step first. Its visible five-second delay precedes up to 15 seconds of derived features. Always-visible Stop/Review ends early. Hiding/minimizing/fault/pause ends collection.

Additional head-down/recovery collection requires another agreed session. Assisted boundary/caregiver scenarios remain pending. Save confirmation creates new files under local calibration/profiles and calibration/replays; unsaved data is only in memory and is lost on exit. New Session asks before clearing in-memory data and retains saved files. The application never saves camera imagery.

## Main source map beneath fall_detector/

| File | Responsibility |
| --- | --- |
| src/tyler_safety_monitor/dashboard.py | Tray/live UI, overlays, region taps, manual audio, bounded cleanup |
| src/tyler_safety_monitor/calibration_ui.py | Guided collection, separate consent, review/profile/replay controls |
| src/tyler_safety_monitor/calibration.py | Strict profile provenance, normalized proposal geometry, new revisions |
| src/tyler_safety_monitor/replay.py | Validated feature schema, source/playback clocks, bounded trajectories |
| scripts/replay_clip.py | Explicit approved-clip ordered analysis, private output, owned timeout process |
| src/tyler_safety_monitor/camera.py | Process-isolated latest-frame capture and health/reconnect |
| src/tyler_safety_monitor/pose.py | Async native pose, score conversion, scene generations, hung-worker guard |
| src/tyler_safety_monitor/tracking.py | Candidate IDs, duplicate rejection, gap/uncertainty markers |
| src/tyler_safety_monitor/settings.py | Validated append-only local settings |
| src/tyler_safety_monitor/audio.py | Manual app-volume test sound; no system audio switching |
| scripts/check_staged.py | Read-only staged privacy gate |
| tests/unit/ and tests/integration/ | Synthetic validation, mock devices and offscreen Qt checks |

## Milestone 2 decisions that remain genuinely pending

Source implementation approval is required. Exact personal zones, severe-risk signal weights, physical recognition behavior and calibration margin must not be guessed. Synthetic state-machine implementation can remain uncalibrated and simulated while real capture/assisted validation is deferred. Later live arming still requires every blueprint acceptance gate, supervised validation and explicit approval.

## Desktop launch and screen-fit follow-up

The Desktop shortcut now targets the local copy. `Start Monitor.cmd` passes the
existing Full model path explicitly and disables bytecode writes with `-B`. A
Windows integration test executes the actual launcher with a fake package, paths
containing spaces and no camera access, verifying the model argument and bytecode
write flag. The repeated earlier missing-model warning was observed alongside
default settings; the later in-process diagnosis below establishes the recurrence's cause.

The dashboard initial size now fits the available screen area, the preview can
shrink vertically, and passive notes wrap. The volume label sits above the four
large buttons. Every essential button keeps its 60-pixel minimum. A constrained
height regression checks the final replay button's vertical bounds after scrolling
and the always-visible Stop/volume controls' bounds. All 211 synthetic tests and
the dependency check passed in the relocated environment.

All 10,950 source-copy files were verified by SHA256 before relocation-specific
environment edits. Only the copied editable paths, command-wrapper paths,
activation reference and corresponding package metadata were adjusted; packages
were not reinstalled and global Python was unchanged. The original environment
and project remain intact. Shortcut/environment backups and verification reports
are outside Git. An agent-launched check of the updated Desktop shortcut passed a short live check:
pose inference and a head-candidate overlay were present, saved scene settings
and the reflection mask loaded, and the final replay control was fully visible
after scrolling to the bottom. No feature capture was active. The monitor was
left minimized with ordinary camera processing continuing. This does not establish
sustained stability or safety-recognition accuracy. Milestone 2 and new personalized
capture remain unapproved.

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

## Persistent Tyler selection — October 6, 2026

Tyler approved this tracking/calibration repair after discussing temporary P-ID
churn. It is not Milestone 2 or live caregiver detection. Calibration / Replay
now provides **Use Selected Candidate as Tyler**. Choose a current unambiguous
P candidate, then press that button. A stable Tyler selector row and status stay
separate from the current P number. The preview labels only a fresh qualified
head as Tyler / Pn. Selecting collects and saves no features.

SubjectSlot is session-local position association, not biometric recognition.
A missing head is never held forward. Short-gap attachment to a new P ID requires
a sole clear candidate within 0.075 original-frame normalized distance of the
last confirmed head, at least three fresh observations spanning 0.5 seconds,
and supporting-observation gaps no longer than 0.4 seconds. Confirmation must
finish within three seconds of the last confirmed observation. Empty batches
stay unavailable; short empty intervals do not manufacture observations or
prevent later supported confirmation. Same-ID motion remains bounded by 0.15;
capture freshness is at most 0.4 seconds. These are diagnostic association
policies, not accepted safety thresholds or accuracy guarantees.

Uncertainty, nearby competition, unsupported movement, a longer absence or
recent second-person evidence during a gap requires explicit reselection. A
single timestamp keeps recent other-candidate evidence bounded. It prevents a
previously observed second person, including one with a new ID, from inheriting
Tyler's slot by moving to the last head position. Position continuity still
cannot exclude every undetected replacement or persistent false estimate;
this is not validated caregiver/person recognition.

Capture locks the designation epoch, camera generation, scene, dimensions and
unchanged Full-pose provenance. Missing/confirming frames can remain raw replay
gap evidence but contribute no subject proposal points. A reselection-required
state stops capture and retains previous data. Eligibility is rechecked after
the consent dialog, since observations continue while it is open. Manual
retargeting with existing features requires New Session; camera pause/restart,
scene edits, replay entry and New Session invalidate the live designation.
Loading a saved profile never establishes who is currently visible. Existing
profile/feature schemas and saved files are unchanged. Experimental face
comparison remains separate and must stop before feature capture.

All 323 synthetic tests passed. Coverage includes temporary-ID reattachment,
stale/invalid time, missing/uncertain states, long gaps, competing-person
replacement, epoch isolation, post-consent source/scene/comparison changes,
loaded-profile isolation and reset behavior. Independent review reproduced the
second-person replacement defect during development; the recent-other guard and
unit/integration regressions address it. The basic ordinary Desktop selection check below is complete;
new-ID reattachment was not observed live. Genuine native-pose gaps, alternate-model validation and
caregiver coverage remain unresolved; no safety timers, audio suppression or
alerts are enabled. The notation-first checkpoint is
fall_detector/docs/TRACKING_REPAIR_CHECKPOINT.md (initial commit 442b589).


### Ordinary Desktop selection check

The user restarted the usual Desktop shortcut and explicitly designated the
current P candidate as Tyler. The new controls and selected Tyler row were
visible. Three point-in-time checks retained the Tyler designation; the row
showed current P2/head visible on accessibility reads, and the unobstructed
preview also showed the explicit not-reliably-located/unavailable state during
a gap. Subsequent reads returned to current P2 without a new designation.
Camera delivery was approximately 13.4-14.2 FPS with zero read failures,
reconnects or pose submissions skipped. Calibration stayed idle with zero
samples. No capture, setting save, profile save, movement instruction or new
personal feature collection occurred.

No P-number change was observed in these checks. Supported new-ID reattachment
therefore remains verified by synthetic tests, not this live session. The final
screenshot was occluded, so its counters/selector text cannot independently
verify the head position. The basic live selection check confirms the new
interface and visible missing-data behavior; it does not establish continuous
correct head tracking, personal identity or caregiver recognition. Genuine pose
loss and alternative-model validation remain open before operational thresholds.


## Handoff decision and angle-dependent misses

The user reports that ordinary straight-ahead posture flickers more, while the
usual safely lowered posture flickers less. The latter is not perfect tracking;
this corrects the initial informal description. It is a user observation, not
a measured comparison or an isolated diagnosis of lighting/view angle. Do not
ask the user to remain head-down or repeat a movement to suit the detector.
Ordinary comfortable posture and tolerated lighting remain the required target.

Milestone 1 TOOLING is ready for handoff: guided capture, preservation/versioned
profiles, replay, visualization, persistent selection source and 323 synthetic
tests are complete within their approved scope. The basic Desktop selection
check retained the designation through missing/visible states. A live new-ID
reattachment was not observed, and native head-loss/angle sensitivity remains
unresolved. These limits must remain visible, not be smoothed into safe evidence.

It is appropriate to proceed to Milestone 2 SIMULATED state-machine development
after its separate source approval, with uncertainty/gap/fault behavior covered
by deterministic tests and existing measurement provenance preserved. Perfect
per-frame recognition is not a prerequisite to implementing that simulated
logic. This is not approval of operational thresholds, new personal capture,
caregiver audio changes, real messaging or live arming. Actual tracking quality,
longest gaps, caregiver coverage and supervised validation must satisfy the
blueprint's later live-alert acceptance gates. Caregiver participation remains
deferred to the agreed supervised stage. Do not declare safety readiness from
the current visual impression.
