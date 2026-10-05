# Next-chat handoff — Milestone 2: simulated detection state machine

Updated: October 5, 2026.

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
> Actual personalized collection was not performed in Milestone 1. Its implementation approval covered synthetic verification only. Explain capture sequence before any movement and obtain separate collection/readiness approval. The first step is ordinary safe posture, without head lowering. Optional already-safe head-down/recovery follows only when ready. Feature-only collection and saving have separate visible confirmations; saved coordinates/confidence are still private data. Imagery saving requires explicit destination/scope approval; no camera-imagery writer currently exists.
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
- Actual live capture, real clip inference, physical accessibility testing, personal zone/margin review, and actual caregiver participation were not performed in Milestone 1. No personal feature/profile files or camera imagery were saved during implementation. The 24-hour stability gate remains pending.
- At initial inspection no detector was running, while Streamlabs OBS was running. C920 ownership was not established. No camera was opened during implementation; recheck ownership before hardware access. The app was not left running by this milestone.
- At inspection private runtime contained Full/Lite/Heavy models and plotting cache, with no saved settings/calibration/replay data. Verify current contents rather than assuming they remain unchanged. Reflection masking is not preconfigured from old photos and needs user review.
- Native live pose inference remains threaded; unfinished/hung workers are retained and block replacement. Preserve this guard. Feature replay itself does not create an inference worker. Watchdog recovery is later work.
- Root website HTML/CSS and public URLs were preserved. Existing local files/global packages, Windows audio/mute, startup entries and camera properties were not changed.

## Launch and first safe action

Normal launch: **Tyler Safety Monitor** Desktop shortcut or `fall_detector/Start Monitor.cmd`, starting minimized. One tray click restores the dashboard. Only one application/camera owner should run.

For a movement-free demo, from the repository root in PowerShell:

```powershell
& .\fall_detector\.venv\Scripts\pythonw.exe -B -m tyler_safety_monitor --no-camera --show
```

Open **Calibration / Replay**, then **Synthetic Replay Demo**, then **Play / Pause Replay**. Replay pauses the camera. **Live View — Camera Stays Paused** does not reopen it automatically.

First real collection, after separate approval/readiness: verify ownership, fixed camera and reflection masks; choose a visible unambiguous candidate; use ordinary-safe-posture capture first. Its visible five-second delay precedes up to 15 seconds of derived features. Always-visible Stop/Review ends early. Hiding/minimizing/fault/pause ends collection. No head lowering is required for this first step.

Optional already-safe head-down/recovery is a later agreed step. Assisted boundary/caregiver scenarios remain pending. Save confirmation creates new files under local calibration/profiles and calibration/replays; unsaved data is only in memory and is lost on exit. New Session asks before clearing in-memory data and retains saved files. The application never saves camera imagery.

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
