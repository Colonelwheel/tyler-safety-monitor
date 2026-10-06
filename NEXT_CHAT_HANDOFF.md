# Next-chat handoff — Milestone 2: simulated detection state machine

Updated: October 5, 2026.

Preferred working copy: `C:\Codex Projects\Tyler Safety Monitor`. Tyler approved
relocation outside OneDrive and updating the existing Desktop shortcut. The
original project and environment remain intact as a backup; continue development
in the local copy. Full Git history and the existing origin were copied. Saved
private AppData files remain at their original locations.

## Ready-to-use opening prompt

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
them. The latest model-count and incremental-selector changes require a fresh
ordinary Desktop launch for live verification. All 227 synthetic tests passed;
independent review found no concrete regression in association or selection.

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
