# Fall Detector — Milestone 0 observation dashboard

The approved requirements are in [`../FALL_DETECTOR_BLUEPRINT.md`](../FALL_DETECTOR_BLUEPRINT.md).
This milestone provides camera capture, person-candidate overlays, ROI/exclusion
editing, and an accessible tray dashboard. **Emergency detection and caregiver
messaging are disabled. It is not an armed safety monitor.**

Read all project Markdown and [`../AGENTS.md`](../AGENTS.md) before implementation.
The root compliance website and its GitHub Pages URLs remain unchanged.

## Open the installed dashboard

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
movement tracking, caregiver entry, or dangerous-event detection. Caregiver
entry samples are deferred at Tyler's request. No movement test is needed for
Milestone 0, and no airway-obstructing posture should ever be requested.

## Runtime data and scope

New settings revisions, explicitly downloaded models, and the plotting-library
cache live under `%LOCALAPPDATA%\TylerSafetyMonitor`. Capture and inference frames
stay in memory. There is no recording, event database, Twilio client, credential
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
