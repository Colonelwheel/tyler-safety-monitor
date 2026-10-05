# Next-chat handoff — Milestone 1: calibration and replay

Updated: October 5, 2026.

## Ready-to-use opening prompt

> Continue Tyler Safety Monitor in this existing project. Before changing anything, discover and read every project-authored Markdown file that governs or informs the work, including `AGENTS.md`, `README.md`, `PROJECT_ROADMAP.md`, `FALL_DETECTOR_BLUEPRINT.md`, `NEXT_CHAT_HANDOFF.md`, `fall_detector/README.md`, and all detector-specific documentation. Treat `FALL_DETECTOR_BLUEPRINT.md` as the approved requirements baseline.
>
> Milestone 0 is implemented and pushed in commit `d63aed6` (`Implement Milestone 0 camera feasibility dashboard`). Begin **Milestone 1 — Calibration and recorded-data harness** only. First inspect the actual source, Git status, isolated environment, current application/camera ownership, and available local data. Give me a concise implementation plan and identify only decisions that truly block this milestone. Ask before repository source-code changes; preparing this handoff does not authorize Milestone 1 implementation or recording.
>
> Build on the working tray/dashboard, camera capture, pose worker, ROI/exclusion editor, observational tracker, and settings revisions. Prefer small targeted additions. Milestone 0 delivered approximately 14 FPS at 1920 × 1080 MJPG through DirectShow with a requested rate of 15 FPS. MediaPipe Full with the masked full-frame view detected a head in both supplied lighting photographs; the tested lower crop missed one photograph. Preserve these provisional choices unless new evidence justifies a change. Do not treat model confidence or repeated still-image detections as validated safety accuracy.
>
> After implementation approval, prioritize a one-finger guided safe-calibration workflow, local calibration profiles, a replay harness for approved safe clips/feature sequences, and visualization of head trajectories, proposed zones, landmark confidence, and person-candidate tracks. Explain the capture sequence before asking me to perform movements. The earlier photos were ordinary photographs, not instructed leaning tests. Never ask me to recreate a dangerous airway-obstructing posture. Obtain explicit approval before saving camera imagery, including the destination and recording scope; use visible capture/start/stop controls and a delay where appropriate. Do not infer final soft/hard danger boundaries from the two photos or choose safety-critical thresholds without my review.
>
> Actual caregiver involvement, including entry samples and real simultaneous two-person validation, is **deferred at my request until the latest practical development point**, normally consolidated with Milestone 6 supervised validation. Build tooling and synthetic/simulated tests first; do not make caregiver participation a prerequisite for the calibration/replay foundation or ask for those samples now. Keep assisted calibration steps pending when assistance is unavailable; never substitute unsafe solo movements. Explain any concrete dependency or safety reason for an earlier caregiver session and agree on its minimum scope with me. This changes participation timing, not approved caregiver behavior or the requirement to complete real caregiver validation before live alerts. Label tracks as person candidates and identify pending validation. Keep all caregiver messaging disabled or simulated. Do not implement live fall alerts, choking behavior, caregiver audio switching, Twilio messaging, startup registration, or the independent watchdog in this milestone.
>
> Preserve one-finger access and the dashboard's always-visible manual alert-volume decrease/increase and Test Sound controls. The approved later audio behavior remains: ordinary alarms use the selected volume; a choking trigger temporarily unmutes and forces maximum system/application output only without caregiver presence. Caregiver arrival has higher priority: stop app audio and mute the active Windows output, preserving prior settings. Restore those settings as soon as caregiver departure is reliably detected, regardless of monitoring or armed state. Do not redesign these rules without explaining concrete evidence for a conflict.
>
> Keep my existing Python installations and global packages unchanged. Use the existing isolated `fall_detector/.venv`; inspect it before installing anything, and do not recreate or delete it. Keep application work under `fall_detector/`. Keep the published root compliance website working and preserve all GitHub Pages URLs. Never commit room photographs, calibration captures, personalized replay data, incident media, databases, logs, phone numbers, caregiver information, `.env` files, credentials, models, or generated secrets. Store approved private runtime data under `%LOCALAPPDATA%\TylerSafetyMonitor`, outside Git and OneDrive. Preserve existing PC/app data; use new files by default and obtain express permission for any overwrite, replacement, deletion, or unrelated side effects.
>
> Choose sensible commit messages for this project without asking me for wording; I delegated that decision permanently. Whenever a milestone is complete, create or update this handoff for the next milestone before finishing. Use parallel subagents when they materially improve implementation or verification. Run targeted synthetic tests, distinguish automated verification from physical/device validation, review the final diff and staged privacy gate, then commit and push finished work. Report what is usable, what remains unvalidated, and the next safe user action.

## Verified foundation to reuse

These are results from the completed Milestone 0 run, not claims that the live
environment or camera is still in the same state. Recheck current ownership and
health before another hardware run.

- Branch/remote: `main`, `https://github.com/Colonelwheel/tyler-safety-monitor.git`.
- Baseline commit: `d63aed6`; 80 automated tests and `pip check` passed.
- Existing Python 3.12 and 3.13 global package lists were unchanged after setup.
- Detector interpreter: isolated Python 3.12.8 x64 in `fall_detector/.venv`;
  dependency pins are in `requirements.lock` and `pyproject.toml`.
- Camera default: index 0, DirectShow, 1080p MJPG, requested 15 FPS. Delivered
  approximately 14 FPS in short windows. Media Foundation timed out in initial
  trials. The 24-hour stability gate has not been met.
- Model default: local Full `.task` bundle, CPU delegate, capacity for two poses.
  Bundles are outside Git; startup never downloads them.
- Live smoke check: hidden processing, native tray availability, dashboard
  restoration, camera capture, and asynchronous inference passed.
- Launch with the **Tyler Safety Monitor** Desktop shortcut or
  `fall_detector/Start Monitor.cmd`. The shortcut points to the existing launcher,
  preserving its relative isolated-environment path. One tray-icon click opens
  the dashboard; the program starts minimized and keeps messaging disabled.
- The app was left running minimized at the end of Milestone 0. This is historical
  state; do not assume it is still running or start a competing camera owner.
- Runtime settings are append-only local revisions. Default ROI is the full
  frame, with **no personalized exclusion mask saved by implementation**.
  Review the reflection mask in the dashboard before collecting calibration.
- Full detected a head in both ordinary supplied photographs in the masked
  full-frame benchmark. Lite missed sample 1, Heavy missed both, and the lower
  crop caused Full to miss sample 1. Two-pose capacity was measured on one person.
- Website HTML/CSS and URLs were unchanged; four existing public pages returned
  HTTP 200. No imagery, operational logs, databases, credentials, or models were
  committed. Detailed measurements are in `fall_detector/docs/MILESTONE_0.md`.

## Existing implementation map

| File beneath `fall_detector/` | Responsibility |
| --- | --- |
| `src/tyler_safety_monitor/dashboard.py` | Tray/dashboard, region taps, overlays, manual volume, responsive cleanup |
| `src/tyler_safety_monitor/camera.py` | Process-isolated capture, shared-memory latest frame, health, reconnect |
| `src/tyler_safety_monitor/pose.py` | Background LIVE_STREAM inference, confidence filtering, scene invalidation |
| `src/tyler_safety_monitor/scene.py` | Normalized rectangles, masks before crop, coordinate transforms |
| `src/tyler_safety_monitor/tracking.py` | Candidate IDs, duplicate rejection, continuity/ambiguity markers |
| `src/tyler_safety_monitor/settings.py` | Validated nonsecret settings and preserved local revisions |
| `src/tyler_safety_monitor/audio.py` | Manual app-volume test sound; no Windows volume/mute switching |
| `Start Monitor.cmd` | One-action isolated launch, starting minimized |
| `scripts/benchmark_camera.py` / `scripts/benchmark_pose.py` | Local aggregate-only feasibility tools |
| `scripts/check_staged.py` | Read-only staged privacy gate |
| `tests/unit/` / `tests/integration/` | Synthetic component and offscreen dashboard tests |

Native pose calls are threaded, not process-isolated. A hung pose thread remains
referenced and blocks replacement workers; exiting/restarting the application
is the current recovery path. Preserve that protection rather than accumulating
workers during calibration/replay. Identity through crossings, occlusion, and
true caregiver entry remains unvalidated. Model limitations are in
`fall_detector/docs/MODELS.md`.

## Milestone 1 acceptance targets for the implementation plan

1. A guided calibration flow explains each safe step, includes visible capture
   state/delay, supports one-pointer start/stop/review, and leaves uncertainty
   visible. Actual capture waits for recording approval and user readiness.
2. Local, versioned calibration profiles preserve scene/model provenance and
   reviewed normalized zones without overwriting existing profiles or treating
   unreviewed danger boundaries as approved.
3. Replay processes approved local clips or derived feature sequences without
   requiring repeated movements; preserve capture timestamps and map overlays
   into the original scene coordinates.
4. Visualize head trajectory, confidence, candidate tracks, and reviewed/proposed
   zones with clear labels. Existing tray, mask, volume, and fault behavior works.
5. Synthetic tests cover profile validation/preservation, replay timing and
   coordinates, missing/invalid inputs, tracking gaps, and accessible controls.
   Real clips and personalized features stay outside Git.
6. Documentation distinguishes implemented tooling from safe physical scenarios
   not yet collected or validated. Actual caregiver participation and assisted
   captures remain deferred as described above; no real messaging or safety-state
   logic is enabled.

Blueprint sections 7–9, 11, and Milestone 1 govern calibration, visualization,
and private-data handling. Stop at this milestone; later stages need approval.
