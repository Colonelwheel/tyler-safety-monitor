# Fall Detector — Observation, calibration and replay dashboard

The approved requirements are in [`../FALL_DETECTOR_BLUEPRINT.md`](../FALL_DETECTOR_BLUEPRINT.md).
Milestones 0 and 1 provide camera capture, person-candidate overlays, ROI/exclusion
editing, guided feature calibration, replay, and an accessible tray dashboard. **Emergency detection and caregiver
messaging are disabled. It is not an armed safety monitor.**

Milestone 2 adds a separate **Simulation** tab that practices warning, recovery,
caregiver, away, night and fault behavior using synthetic evidence. Select a
scenario and **Play / Pause Simulation**; **Cancel Simulated Alert** stays visible.
No camera/movement is required and no message, speech, automatic sound or Windows
audio change occurs. Pause freezes the simulation clock; Restart clears only
its in-memory scenario state. Opening an approved feature replay is read only
and keeps personal risk thresholds uncalibrated. See [Milestone 2](docs/MILESTONE_2.md).

Read all project Markdown and [`../AGENTS.md`](../AGENTS.md) before implementation.
The root compliance website and its GitHub Pages URLs remain unchanged.

## Open the installed dashboard

The preferred working copy on this PC is `C:\Codex Projects\Tyler Safety Monitor`,
with its existing Git history and GitHub remote preserved. The Desktop shortcut
launches this local copy. The earlier OneDrive copy is retained as a backup.
Saved models, settings and calibration files remain in their existing private
AppData location.

The launcher passes the existing Full model path explicitly and uses `-B` to
prevent bytecode writes. It does not download or replace a model.

Open **Start Monitor.cmd** in this folder. It launches the isolated application
minimized, with a tray icon. One click on that icon opens the live dashboard.
Closing the dashboard returns it to the tray and camera processing continues.
**Exit Application** stops the application. If Windows has no tray, a visible
window and taskbar minimize action provide a fallback.

The initial choices are camera 0, DirectShow, 1920 × 1080 MJPG, requested 15 FPS,
the Full pose model, and capacity for two poses. The measured capture rate was
approximately 14 FPS; requesting 30 FPS did not improve it in this scene.
See [the measurements and limitations](docs/MILESTONE_0.md).

Large **Decrease**, **Increase**, **Test Sound**, and **Stop Test Sound** controls
remain visible below the preview. Test Sound uses the selected application
volume; it never unmutes or changes Windows output volume. No automatic audio,
choking-volume override, or caregiver muting runs in this observation milestone.
The blueprint's audio priority and restoration rules remain requirements for
their later implementation.

## Calibration and replay

The **Calibration / Replay** tab provides **Synthetic Replay Demo** without
requiring movement, a recording, a model run, or camera access. To open the
dashboard with the camera paused, launch from PowerShell at the repository root:

```powershell
& .\fall_detector\.venv\Scripts\pythonw.exe -B -m tyler_safety_monitor --no-camera --show
```

Keep only one dashboard/camera owner running. Return from replay using **Live
View — Camera Stays Paused**, then start the camera explicitly when ready.

Actual calibration remains pending. Before moving, read the selected safe-step
explanation, review the fixed camera/reflection mask, choose your visible person
candidate, and approve the separate feature-only capture confirmation. The flow
uses a visible five-second delay and at most 15 seconds per step. **Stop / Review
Capture** stays visible outside the setup scroll area. Closing/hiding/minimizing
the dashboard or losing fresh observations ends collection; ordinary background
camera processing retains its existing behavior.

The first step is ordinary safe posture with no special movement. Routine small
adjustments and an optional already-safe head-down/recovery step follow only
when ready. Do not seek your deepest position, hold down for 30 seconds for
calibration, or recreate an airway-obstructing posture. Assisted and caregiver
steps stay pending until supervised validation. No caregiver samples are needed
to use the tooling now.

Capture retains derived pose coordinates and confidence in memory; **no camera
images, video or audio are saved**. **Save New Profile / Features** separately
asks before creating private files under `%LOCALAPPDATA%\TylerSafetyMonitor\calibration\profiles`
and `calibration\replays`. Earlier files are retained. **New Session — Keep Saved
Files** asks before clearing in-memory edits; it never deletes saved files. Use
a new session when changing camera, scene, or candidate. Unsaved samples are not
persisted on application exit.

Propose safe/intentional-lean envelopes from observed points or draw a proposed
zone with two separate preview taps. Review zones individually before saving.
The intentional-lean wiggle-room control starts at zero and offers large **Less**
and **More** actions in 0.1% original-frame steps up to 2%. This editor range is
not a safe-distance recommendation or a reviewed threshold; image distances are
not inches or anatomical depth. Margin changes invalidate the lean review and
never expand a hard danger boundary. No soft/hard zones are inferred from the
earlier photographs. The ordinary-lean 30-second rule remains Milestone 2 work.

Profiles preserve camera/model/scene provenance and proposed/reviewed status.
Loaded overlays are hidden when available camera/model/dimensions/scene metadata
differs or cannot be verified. A matching metadata record cannot prove that the
physical camera or room did not move; review the actual scene before reuse.

Feature replay uses original source timestamps, its own playback clock, and
original normalized coordinates/aspect ratio. Paths break at gaps, missing
observations and association uncertainty. Per-landmark scores are visibility/
presence estimates: green at least 80%, amber 50–80%, invisible below 50%. They
are not calibrated accuracy or danger probability. All people remain candidates.

For an already-approved local clip, an explicit offline command analyzes frames
in order in a bounded child process and creates a **new feature file only**:

```powershell
& .\fall_detector\.venv\Scripts\python.exe -B .\fall_detector\scripts\replay_clip.py --clip <approved-local-clip> --model <local-task-model> --output "$env:LOCALAPPDATA\TylerSafetyMonitor\calibration\replays\new-unique-name.json" --scene <local-scene-json> --timestamps <local-timestamp-sidecar>
```

`--scene` accepts the `roi`/`exclusions` object; `--timestamps` accepts
`{"schema_version":1,"timestamps":[0.0,0.071,0.143]}` with exactly one source time
per decoded frame. Both are optional, but omission means full-frame/unmasked
analysis or nominal clip-FPS timing, respectively. Nominal FPS cannot recover
the original camera cadence. Output must remain beneath the private local replay
directory and must not already exist. No source clip/model is changed or
downloaded. A stalled analysis is terminated after `--timeout` seconds (600 by
default); any partial new output remains for inspection. See
[Milestone 1 verification and limits](docs/MILESTONE_1.md).

## Region editing

1. Select **Set ROI** or **Add Exclusion Mask**.
2. Tap one corner in the preview, then tap the opposite corner. No dragging,
   modifiers, simultaneous input, or multi-touch is required.
3. Review the result. **Cancel Region Edit**, **Undo Last Mask**, and **Full Frame
   ROI** provide separate one-action corrections.
4. Select **Save Settings** to create a new local revision. Earlier revisions
   are retained; the newest valid revision is loaded on restart. A corrupt newest
   revision produces a visible fault and default uncalibrated settings.

Mask the reflective picture before relying on observations. The default scene
uses the full frame with no personalized masks: private room geometry is not
baked into source. The tested lower crop reduced detection on one supplied
photo, so do not assume a tighter crop is better. Include genuine caregiver
approach areas when later calibrating the scene. Person IDs are observational
candidates, not confirmed Tyler/caregiver identities.

## Isolated setup on another checkout

Python 3.12 x64 must already be installed. The tested interpreter is 3.12.8.
Run the following from the repository root using PowerShell:

```powershell
& .\fall_detector\scripts\setup.ps1
```

The script creates a new `.venv` and installs pinned dependencies only there.
It refuses to alter an existing environment. No global packages, Python version,
PATH, system settings, or Windows startup entries are changed. A partial setup
is preserved for inspection rather than automatically deleted.

Download a model explicitly once:

```powershell
& .\fall_detector\.venv\Scripts\python.exe .\fall_detector\scripts\benchmark_pose.py --download-model full
```

It creates a new local model file and refuses to overwrite an existing one.
Starting the dashboard never downloads a model. Other variants and licensing
details are in [the model review](docs/MODELS.md). To select an existing local
model explicitly, use `--model <local-task-path>` on the application command.

## Verification and benchmarks

```powershell
& .\fall_detector\.venv\Scripts\python.exe -m pip check
& .\fall_detector\.venv\Scripts\python.exe -m pytest .\fall_detector\tests -q -p no:cacheprovider --basetemp (Join-Path $env:TEMP ('tsm-test-' + [guid]::NewGuid().ToString('N')))
& .\fall_detector\.venv\Scripts\python.exe .\fall_detector\scripts\benchmark_camera.py --backend dshow --seconds 20 --warmup 5
& .\fall_detector\.venv\Scripts\python.exe .\fall_detector\scripts\check_staged.py
```

Always use a **new** scratch directory for `--basetemp`; pytest may remove a
previously existing directory at that path. Tests use synthetic data and fake
devices, including camera-process failure simulations. They do not test real
caregiver behavior or change Windows audio settings.

Run hardware benchmarks while the dashboard is exited so only one process owns
the C920. Camera output is aggregate JSON to stdout; no camera images are saved.
The pose benchmark reads external photographs without modifying/copying them:

```powershell
& .\fall_detector\.venv\Scripts\python.exe .\fall_detector\scripts\benchmark_pose.py --models <local-task-paths> --images <external-image-paths> --num-poses 1 2
```

Supply optional `--exclude X Y WIDTH HEIGHT` and `--compare-roi X Y WIDTH HEIGHT`
with normalized full-frame coordinates. Room geometry remains local input.
Do not redirect private media or operational logs into this public repository.
Still images test landmark visibility and inference time; they do not establish
movement tracking, caregiver entry, or dangerous-event detection. Actual caregiver
involvement is deferred until the latest practical development point, normally
Milestone 6 supervised validation; see `AGENTS.md` and blueprint section 8 for
earlier-dependency exceptions and required validation before live alerts. Assisted
captures stay pending when assistance is unavailable. No movement test is needed
for Milestone 0, and no airway-obstructing posture should ever be requested.

## Runtime data and scope

New settings/profile/feature revisions, explicitly downloaded models, and the plotting-library
cache live under `%LOCALAPPDATA%\TylerSafetyMonitor`. Capture and inference frames
stay in memory. Approved derived features can be saved, but there is no imagery recording, event database, Twilio client, credential
store, watchdog, startup registration, or LAN control server in this milestone.

`.gitignore` excludes private media and generated outputs. The staged-file gate
blocks common media/database/model files and credential/phone-number patterns;
it supplements manual diff review and does not guarantee secret detection.
Never commit photographs, calibration captures, incident media, databases,
logs, phone numbers, caregiver information, `.env` files, or credentials.

Camera open/read hangs are contained in an owned child process and retried with
bounded backoff. Inference initialization/results report faults. Native pose
calls run on a background thread; a stuck native thread prevents replacement
workers and requires exiting/restarting the application. Independent watchdog
recovery and Windows startup remain Milestone 5 work.

## Startup file diagnostics

Use `--diagnostics` on an explicitly requested troubleshooting launch to save one
new private startup report under `%LOCALAPPDATA%\TylerSafetyMonitor\diagnostics`.
It records paths, source-module locations, file readability, selected LOCALAPPDATA
values and Windows handle final paths/errors. It saves no imagery, feature values,
settings contents or broad environment dump. Normal Desktop launches do not enable
this option; do not commit diagnostic files.

Codex's packaged Windows runtime can redirect logical AppData access into its own
LocalCache even when LOCALAPPDATA contains the ordinary host path. On October 5,
this caused agent-launched checks to find the models/settings while Tyler's Desktop
launch could not. With explicit approval, the eight existing runtime files were
copied into ordinary host AppData without replacing anything, and the user-launched
dashboard then loaded saved settings and completed live pose inference. Retained
cached originals remain untouched. Verify physical handle paths in the actual user
launch before diagnosing another apparent missing file or collecting real features;
a successful agent-spawned check alone is insufficient. See the handoff for details.


### Experimental head comparison

Camera / Masks has **Start Experimental Head Comparison** and **Stop Head
Comparison**. Comparison is off by default. Start explicitly downloads a reviewed
~1.1 MB Google face model into a separate local models file if missing; existing
files are never replaced, and normal startup never downloads anything. The
background comparison uses the current masks, runs at at most 2 samples/second,
and shows magenta current face estimates independently of Full pose IDs. It
writes no imagery/features and makes no identity or safety decisions. Calibration
capture is blocked until comparison is stopped. This experiment is not a proven
nighttime detection fix; inspect estimate locations and cadence, not just counts.

The experimental score selector offers 50% (baseline), 80%, and 90%. Scores are
not probabilities of matching a person. Changing the session-only cutoff clears
old estimates and counters; Full pose tracking and saved calibration remain
unchanged. The status distinguishes score-only rejection from other missing
estimates. Inspect the magenta estimate locations: a false pillow estimate can
keep a no-face counter at zero. Higher cutoffs also risk dropping genuine heads.

### Select Tyler independently of temporary P IDs

The main dashboard also shows **LIVE SECOND-PERSON DIAGNOSTIC**. After selecting
Tyler as described below, it shows the separate candidate, observed progress up
to **2.0 seconds**, the reset count and why the counter restarted. Flicker,
missing/ambiguous Tyler, changed candidates and stale observations reset it.
**Caregiver candidate confirmed — diagnostic only** does not verify identity,
enable alert suppression, mute audio or save any data. It uses Full pose only;
experimental face estimates cannot advance this counter.

In Calibration / Replay, choose your current visible P candidate and press
**Use Selected Candidate as Tyler**. The Tyler row stays selected through
supported short-gap P-ID changes. Its status shows visible, missing, checking a
returning candidate, or requiring reselection. Missing or uncertain detections
cannot supply calibration points; a longer gap or competing person requires a
fresh explicit selection. No features are collected by selecting Tyler.

This designation is for the current camera/scene session. Pause/restart, scene
changes, replay and New Session clear it. Saved profiles remain intact; opening
a profile does not automatically identify the person in view. Existing unsaved
features require New Session before changing designation. Stop the experimental
comparison before an independently approved feature capture. This association
is based on observed position continuity and does not prove personal identity.
