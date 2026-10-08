# Tyler Safety Monitor — Fall Detector Blueprint

Status: requirements baseline for implementation  
Blueprint date: October 4, 2026  
Target platform: Tyler's Windows 11 PC

## 1. Purpose

Build a local, accessibility-first monitoring application that watches Tyler's fixed bed position with a Logitech C920 webcam, detects a possible dangerous forward collapse, gives Tyler an appropriate opportunity to recover or cancel, and sends SMS alerts to one consented caregiver through Twilio.

The key danger is not a generic standing fall. Tyler normally sits on his bed and may intentionally lean forward with his head down for approximately 30 seconds. The serious event is a substantially deeper forward collapse that may obstruct his airway and may leave him unable to speak, reach his phone, or operate another control.

The application is an assistive backup. It is not a medical device, professional monitoring service, breathing monitor, or guarantee that a fall or emergency will be detected.

## 2. Scope decisions

### Version-one requirements

- Operate locally on Windows 11.
- Use the fixed Logitech HD Pro Webcam C920.
- Monitor only while Tyler is in active/day mode.
- Remain minimized during ordinary operation.
- Open to a dashboard with the live camera view, tracking overlays, status, and all relevant controls.
- Provide a manually selected local alert volume with an accessible test control.
- Detect ordinary forward leaning separately from a severe forward collapse.
- Favor false-positive alerts over missed severe events.
- Detect a caregiver as a second, independently tracked person.
- Automatically handle caregiver assistance and safe departures.
- Provide mouse, phone, voice, and automatic recovery cancellation paths where applicable.
- Provide separate manual possible-fall and choking triggers.
- Send SMS through the already-approved Twilio campaign.
- Repeat unanswered emergency SMS messages at most ten times total.
- Save incident-only local recordings for diagnostics and delete them after 30 days.
- Start with Windows and use an independent watchdog.
- Keep all secrets, phone numbers, photographs, and incident recordings out of Git.

### Explicitly outside version one

- Automatic calls to 911 or other emergency services.
- Automatic Twilio voice calls.
- Pushover notifications.
- Remote live viewing.
- Images or video attached to caregiver messages.
- The Android USB/cellular SMS fallback. This is planned after the core camera/Twilio system.
- Detection of breathing, choking sounds, mouth position, or medical condition from video.
- Support for multiple rooms or moving cameras.

## 3. Confirmed operating environment

### Computer

- Acer Predator PO5-640
- Windows 11 Home 64-bit
- Intel Core i7-12700F, 12 cores / 20 logical processors
- NVIDIA GeForce RTX 3080
- 32 GB RAM
- Connected to a UPS
- Expected to remain powered on and awake during active monitoring

### Camera and scene

- Logitech HD Pro Webcam C920
- Fixed position and framing
- Tyler occupies the lower center of a wide 1920 × 1080 view
- The bed and caregiver approach/exit area are visible
- Low-light frames have a strong blue cast but retain a visible head/face/shoulder outline
- A framed picture can reflect content from a television opposite it
- The reflected-picture region and other irrelevant fixed regions must be excluded from person detection
- Camera access is not normally shared with OBS, Zoom, or other applications

### Daily routine

- Tyler normally sits in the same bed position throughout the day.
- Repositioning, intentional forward leaning, sleeping, caregiver assistance, and safe departures must not produce caregiver alerts.
- A caregiver sets Tyler up for the day and lays him down at night.
- Tyler and the caregiver leave the frame together for the tub or when leaving the house.
- Night mode is selected deliberately.

## 4. Accessibility requirements

- Every essential action must be possible with one pointer/tap action.
- Do not require held modifier keys, simultaneous inputs, multi-finger gestures, or rapid movement between controls.
- Use very large controls with clear text and distinct colors/icons.
- Preserve keyboard, mouse, voice, and phone options, but never make voice the only path.
- Full-screen warning screens must contain one dominant **Cancel Alert** control.
- The ordinary dashboard may be minimized, but it must be recoverable from the system tray and Windows notifications.
- Notifications should include appropriate buttons such as **Restart**, **Start Monitoring**, **Night Mode**, and **Open Status**.
- Provide a large one-finger-friendly alert-volume control with direct decrease/increase actions and **Test Sound**.
- Ordinary fall warnings and status sounds must respect the manually selected alert volume and must not change Windows system volume automatically.
- A choking trigger normally overrides the selected volume: temporarily unmute the active Windows output and force both system and application alert volume to maximum, then restore the previous volume and mute state when the incident is resolved.
- Caregiver presence has higher priority than every alarm type: immediately stop application speech/sounds and mute the active Windows output, preserving its prior volume and mute state until caregiver departure is reliably detected.
- A manual choking trigger must remain available in every mode, including caregiver mode.
- Voice recognition is secondary: useful when Tyler can speak, but not part of the minimum automatic safety path.

## 5. Safety timing and alert rules

All times must be configuration values with the confirmed values below as defaults.

| Event | Default behavior |
| --- | --- |
| Ordinary forward lean | Allow 30 seconds |
| Ordinary lean persists | Start 10-second local countdown |
| Severe forward collapse | Start 8-second local countdown |
| Manual possible-fall trigger | Start 8-second local countdown |
| Manual choking trigger | Send SMS immediately; no countdown |
| Recovery during countdown | Cancel automatically |
| Separate caregiver detected | Cancel/suppress after 2 continuous seconds |
| Caregiver leaves Tyler safe and alone | Rearm after 30 stable seconds |
| SMS remains unacknowledged | Repeat every 60 seconds |
| Maximum SMS count | 10 total: initial plus nine repeats |
| Event media retention | 30 days |

### Proposed message text

Detected or manually triggered possible fall:

> Tyler Safety Monitor detected a possible dangerous forward fall. Tyler did not recover or cancel the alert. Please come check his position immediately.

Manual choking trigger:

> URGENT: Tyler activated the choking emergency alert and may be unable to breathe or respond. Come immediately.

The word **URGENT** is reserved for the choking message. The fall message must not use it.

### SMS stopping conditions

Stop future repeat messages when any of these occurs:

- Tyler visibly recovers from a possible-fall incident. Automatic posture recovery
  does not cancel a manual choking alert (Tyler's clarification, October 7, 2026).
  Upright posture does not establish that choking has resolved; use explicit
  Cancel/Resolve, a valid caregiver reply, or confirmed caregiver presence.
- A second person is reliably detected for at least two seconds.
- Any inbound SMS reply arrives from the configured caregiver number after the incident began.
- Tyler or the caregiver explicitly resolves the incident in the application.

Do not send an automatic follow-up message merely because recovery or caregiver presence was detected.

## 6. Application state machine

The state machine must be explicit and independently testable. UI labels may be friendlier than the internal names.

### Primary modes

- `STARTING`: processes, camera, models, storage, and alert adapters are initializing.
- `NIGHT`: automatic fall detection is disabled; manual emergency triggers remain available.
- `READY`: application is running but has not yet confirmed a stable active posture.
- `ARMED`: Tyler is visible alone in the calibrated safe position and automatic detection is active.
- `CAREGIVER_PRESENT`: a separate person has been continuously and reliably tracked for at least two seconds; automatic fall warnings are suppressed.
- `AWAY`: Tyler and a previously detected caregiver left the frame together.
- `FAULT`: the detector, camera, storage, or another required local component is unavailable.

### Incident substates

- `LEAN_GRACE`: head crossed the ordinary forward boundary; 30-second tolerance is running.
- `NORMAL_WARNING`: ordinary lean persisted; 10-second cancellation countdown is running.
- `SEVERE_WARNING`: severe-collapse criteria were met; 8-second cancellation countdown is running.
- `ALERT_ACTIVE`: at least one caregiver SMS was submitted to Twilio; repeat/acknowledgement monitoring is active.
- `RESOLVED`: recovery, caregiver presence, inbound reply, or manual resolution ended the incident.

### Important transitions

1. **Morning activation**
   - The user or caregiver may press **Start Monitoring**.
   - The application should also attempt automatic activation after Tyler is visible upright and stable.
   - It must announce activation using a Windows notification, speech, and a distinct sound.

2. **Night mode**
   - Selected with one large action.
   - Stored durably so an overnight restart does not arm the detector unexpectedly.
   - Announced through notification, speech, and sound.

3. **Caregiver arrival**
   - Require two spatially separate, temporally stable human tracks for at least two seconds.
   - Cancel pending warnings and stop repeat SMS messages.
   - Enter `CAREGIVER_PRESENT`.
   - Immediately stop all Fall Detector speech and sounds and mute the active Windows output so audio from other applications is also silenced.
   - Preserve the previous Windows volume/mute state and application alert volume.
   - Keep caregiver mode completely silent; update visual state only and do not play a tone or spoken announcement.
   - Manual emergency controls remain active.

4. **Safe departure**
   - A caregiver track must exist before Tyler disappears.
   - If Tyler and that caregiver leave together, enter `AWAY` instead of creating an incident.
   - Do not classify an unexplained disappearance while Tyler is alone as a safe departure.

5. **Return**
   - Returning with a caregiver enters `CAREGIVER_PRESENT`.
   - Restore the preserved Windows volume/mute state and selected application alert volume as soon as caregiver departure is reliably detected, regardless of whether monitoring is armed, rearming, away, in night mode, or in another state.
   - After the caregiver leaves, require Tyler to be visible in a calibrated safe position for 30 continuous seconds before entering `ARMED`.

6. **Restart recovery**
   - Persist the last deliberate mode and active-incident metadata atomically.
   - If the last deliberate mode was `NIGHT`, restart into `NIGHT`.
   - Otherwise restore the service, camera, and scene classification, then resume the appropriate ready/armed/away state.
   - Never send an SMS solely because the application restarted.

## 7. Detection design

### Principle

Do not treat this as generic fall classification. Use personalized scene calibration and multiple observable signals over time.

### Camera preprocessing

- Capture monotonic timestamps for every accepted frame.
- Request the C920's native 1920 × 1080 stream and benchmark 15 and 30 FPS.
- Prefer the most stable Windows backend after testing Media Foundation and DirectShow.
- Crop inference to the bed, Tyler, and genuine caregiver-entry region.
- Apply a fixed exclusion mask over the reflective picture and other irrelevant regions.
- Record exposure, brightness, blur, dropped-frame rate, and camera reconnect events.
- Consider restrained low-light normalization only after comparing it with unmodified frames; avoid transformations that destabilize landmarks.

### Initial model strategy

Start with MediaPipe Pose Landmarker in live-stream mode because it supports asynchronous camera processing, tracking, confidence thresholds, and a configurable number of poses. Configure at least two poses for caregiver detection.

MediaPipe itself is open-source under the Apache License 2.0 and runs locally, so it does not have a per-frame or per-request API charge. Before distributing any downloaded model artifact, verify that artifact's own license and attribution requirements as part of dependency review.

The implementation must include an early model-validation spike. If MediaPipe cannot track Tyler's relatively small head/upper body reliably in the darkest scene, test an alternative local person/head detector rather than forcing unsuitable thresholds.

Do not select a fallback model without checking its license, Windows support, GPU/CPU behavior, and redistribution terms.

### Tracking outputs

For each real person track, retain:

- stable track identifier;
- normalized head center, preferring visible face landmarks and falling back to ears/eyes/nose combinations;
- shoulder midpoint and shoulder angle;
- upper-torso center and inclination when visible;
- landmark visibility/presence confidence;
- velocity and direction of head movement;
- duration inside each calibrated zone;
- recent occlusion and reacquisition history;
- association with Tyler versus a caregiver candidate.

### Calibrated regions

- **Safe zone:** ordinary upright/reclined range.
- **Intentional lean zone:** safe forward positions demonstrated by Tyler.
- **Soft boundary:** crossing begins `LEAN_GRACE`.
- **Hard danger boundary:** a substantially deeper head position that can begin `SEVERE_WARNING`.
- **Expected-person region:** where Tyler should be found while armed.
- **Caregiver entry/exit region:** valid path for a second real person.
- **Excluded reflection region:** the wall picture and any other locations that must never produce person tracks.

Use normalized coordinates and scene anchors so calculations do not depend on raw pixel dimensions alone.

### Evidence used for an ordinary lean

- Head crosses the soft forward/downward boundary.
- Head remains trackable and does not cross the hard boundary.
- Movement resembles a calibrated intentional lean.
- Tyler has not yet remained beyond the boundary for 30 seconds.

### Evidence used for a severe collapse

Use a weighted combination rather than one frame:

- head substantially exceeds the calibrated hard boundary;
- head continues downward after crossing the intentional-lean range;
- unusual downward/forward velocity or trajectory;
- final head location is much lower than safe calibration;
- head becomes occluded or unexpectedly leaves its expected region while Tyler was alone;
- lack of recovery movement;
- torso movement when available, but never require torso movement because it is not reliable for Tyler's event.

The severe path starts an 8-second cancellation countdown, not an immediate SMS.

### Recovery

Recovery must be recognized even if slow. Require evidence of movement back toward and then into the calibrated safe range; do not require one rapid motion. Once stable recovery is confirmed during a countdown, cancel it automatically.

### Second-person safety

False second-person detection is safety-critical because it can suppress a real alert. Therefore:

- Mask the reflective picture before inference.
- Require a second spatially distinct person, not a duplicated detection around Tyler.
- Require temporal persistence for at least two continuous seconds.
- Track entry from a plausible physical region when available.
- Reject implausible scale/location changes and detections contained inside the reflection mask.
- Test with changing television imagery, shadows, bedding, partial doorway appearances, and caregiver occlusion.

## 8. Calibration workflow

Calibration must never ask Tyler to recreate an airway-obstructing position.

Tyler clarified on October 5, 2026 that his safe intentional head-down position
can extend slightly farther on other days than during a particular session.
Allow a small, visually reviewed amount of day-to-day variation in the
intentional-lean proposal; do not automatically adopt today's deepest sample as
a final soft/hard threshold. The margin and safety-critical boundaries require
Tyler's review. The approved 30-second ordinary-lean grace period is unchanged;
it does not establish that an unrecognized severe position is safe. Milestone 1
implements review tooling only, with no danger classification or grace timer.

### Caregiver participation timing

Tyler requested on October 5, 2026 that actual caregiver involvement be deferred
until the latest practical development point, normally consolidated with
**Milestone 6 — Supervised validation**. Implement calibration tooling and
synthetic/simulated caregiver tests first. Keep caregiver behavior in its approved
implementation milestones; this scheduling change does not alter safety behavior.

The sequence below describes required capture coverage, not a demand to collect
every scenario in Milestone 1. Leave caregiver-assisted steps pending when
assistance is unavailable; never replace them with unsafe solo movements. Explain
any concrete dependency or safety requirement for earlier caregiver participation
and agree on the smallest necessary session with Tyler. Required real caregiver
calibration and validation must be complete before enabling live alerts.

### Guided capture sequence

1. Confirm the camera is fixed and show the masked/excluded regions.
2. Capture Tyler's ordinary safe positions and routine small movements.
3. Capture several intentional head-down-and-recover sequences, staying strictly within positions Tyler already considers safe.
4. With a caregiver assisting, capture safe approximations near—but not at—the maximum safe boundary.
5. Provide a visible capture delay so the caregiver can step out of frame before collecting a Tyler-only pose.
6. Capture caregiver entry, assistance, departure, Tyler-and-caregiver safe exit, and return sequences.
7. Capture the darkest realistic lighting and changing reflected-TV conditions.
8. Review proposed zone boundaries visually before saving them.

Calibration data remains local and must be easy to discard and recapture.

## 9. User interface

### Normal operation

- Main window starts minimized.
- System tray icon communicates status by color and accessible text.
- A single click opens the dashboard.
- The minimized state must not stop camera processing or alerts.

### Dashboard

The opened dashboard should contain:

- live camera preview;
- optional overlays for Tyler track, caregiver track, head path, safe zone, soft boundary, hard boundary, and exclusion masks;
- current mode and detection confidence;
- camera, detector, Twilio, watchdog, storage, and internet status;
- countdown and incident status when applicable;
- last event summary;
- large one-action buttons for:
  - **Start Monitoring**;
  - **Night Mode / Stop Automatic Monitoring**;
  - **Cancel Alert**;
  - **Possible Fall**;
  - **I'm Choking — Send Now**;
  - **Restart Detector**;
  - **Alert Volume** decrease/increase control and **Test Sound**;
  - **Test Alarm**;
  - **Test SMS**;
  - **Calibrate**;
  - **Settings**;
  - **View Events**.

The immediate choking control needs strong visual separation from test and configuration actions, while remaining usable with one finger.

### Warning overlay

- Appear above other ordinary windows.
- Show the reason and remaining seconds in very large type.
- Speak the warning and play a distinctive repeating sound.
- Use the manually selected volume for ordinary and severe-fall warnings.
- For a choking trigger, temporarily unmute and force the active Windows output and application alert to maximum volume when no caregiver is present; restore the previous settings after resolution.
- Provide one dominant **Cancel Alert** button.
- Accept configured mouse, phone, keyboard, and voice cancellation inputs.
- Allow automatic visual recovery and caregiver detection to cancel.
- When caregiver detection occurs, stop Fall Detector audio and mute the active Windows output immediately without playing an arrival or dismissal sound. Caregiver-mode silence overrides the choking maximum-volume behavior.

### Windows notifications

Use native Windows app notifications with action buttons. A separate watchdog owns failure and process-management notifications so it can act even when the Python detector is not running.

Potential actions by context:

- **Restart**
- **Start Monitoring**
- **Night Mode**
- **Open Status**
- **Retry Camera**

## 10. Proposed technical architecture

### Python monitoring application

Responsibilities:

- OpenCV camera capture and frame-health metrics.
- MediaPipe or validated replacement inference.
- temporal person tracking and calibrated feature extraction;
- state machine and countdowns;
- local PySide dashboard, tray icon, and full-screen warning;
- local speech/audio adapter;
- ring buffer and event media writer;
- SQLite event store and structured logs;
- Twilio sending, delivery-state tracking, and inbound-reply polling;
- configuration and calibration management;
- authenticated local IPC with the watchdog.

Select and pin the Python version only after verifying current compatibility among MediaPipe, OpenCV, PySide, and the packaging tool.

### .NET watchdog and notification helper

Use a small Windows-native .NET application because current Microsoft guidance recommends the Windows App SDK `AppNotificationManager` for new WPF, WinForms, and unpackaged desktop applications.

Responsibilities:

- start automatically at Windows sign-in;
- launch and supervise the Python application;
- monitor a frequent heartbeat;
- distinguish deliberate shutdown/night operation from a crash;
- restart the detector after failure;
- issue actionable Windows notifications even when the detector is down;
- forward notification button actions through a named pipe or process command;
- avoid sending caregiver SMS for detector/camera failures, per Tyler's decision.

### Local IPC

Use a Windows named pipe or equivalently local, authenticated mechanism. Commands must be explicit and idempotent, for example:

- `OPEN_STATUS`
- `START_MONITORING`
- `ENTER_NIGHT_MODE`
- `RESTART_DETECTOR`
- `RETRY_CAMERA`

Do not expose an unauthenticated LAN HTTP control interface.

### Twilio acknowledgement path

Version one should avoid requiring a publicly reachable local webhook. Poll Twilio's Message resource at a restrained interval during an active incident and look for an inbound message:

- from the configured caregiver number;
- to the configured Twilio number;
- created after the incident began;
- not previously processed.

Any matching reply acknowledges the incident and stops additional repeat messages. Store only the identifiers and minimal metadata needed for deduplication.

### Later Android companion

After the core system is validated, build a private Android companion that:

- accepts authenticated emergency commands over the always-connected USB link;
- sends cellular SMS with Android's SMS API when Twilio/home internet is unavailable;
- works while the phone is locked;
- reports sent/delivery results to the PC;
- exposes an accessible one-finger emergency control;
- explores a long-press Home or another dependable system-level gesture without breaking normal phone navigation.

USB debugging/ADB may be useful for development and transport experiments, but the final safety path should not assume an interactive ADB confirmation at incident time.

## 11. Storage, secrets, and retention

### Local data location

Use a dedicated directory such as:

```text
%LOCALAPPDATA%\TylerSafetyMonitor\
  config\
  calibration\
  database\
  logs\
  events\
  models\
```

### Event recording

- Maintain an in-memory rolling buffer of approximately 20 seconds.
- On an incident, save the pre-event buffer, countdown, and up to 30 seconds after resolution.
- Limit one event clip to two minutes.
- Store timestamps and reason metadata beside the media.
- Delete event media automatically after 30 days.
- Run retention cleanup conservatively and only inside the verified event directory.
- Do not continuously record to disk.

### Secrets

- Never store Twilio credentials or phone numbers in Git.
- Prefer a restricted Twilio API key rather than the master Auth Token when feasible.
- Protect local credentials with Windows Credential Manager or DPAPI.
- Commit only redacted example configuration.
- Never log complete credentials or full phone numbers.

### Git exclusions

At minimum exclude:

- `.env` and local secrets;
- calibration captures;
- photographs and videos;
- event recordings and snapshots;
- databases and logs;
- generated models and caches when licensing or size makes them unsuitable;
- virtual environments and build output.

## 12. Failure handling

### Camera unavailable

- Enter `FAULT` while monitoring would otherwise be active.
- Issue local toast, speech, and sound immediately.
- Offer **Retry Camera**, **Restart**, and **Open Status**.
- Retry with bounded backoff and report recovery.
- Do not text the caregiver solely for a camera failure.

### Detector process crash or hang

- Watchdog identifies missed heartbeat.
- Preserve diagnostic logs without overwriting previous evidence.
- Restart the process automatically.
- Notify locally with actionable buttons.
- Restore the last deliberate mode safely.

### Internet or Twilio failure

- Preserve the active incident locally.
- Show and speak that caregiver messaging is unavailable.
- Retry within strict duplicate-prevention rules.
- Record whether Twilio accepted, delivered, failed, or could not receive the request.
- Version one has no independent remote path; the Android cellular fallback is a subsequent milestone.

### Storage failure

- Detection and alerting should continue when possible even if diagnostic media cannot be written.
- Report the storage problem locally.
- Never delete or rewrite unrelated files to recover space.

### Power failure

- The UPS reduces but does not eliminate risk.
- A fully powered-off PC cannot monitor or alert.
- Verify automatic recovery after UPS events during supervised testing.

## 13. Repository layout

The existing GitHub Pages site must remain at the repository root so its public compliance URLs do not change.

Proposed additions:

```text
FALL_DETECTOR_BLUEPRINT.md
NEXT_CHAT_HANDOFF.md
fall_detector/
  README.md
  pyproject.toml
  config.example.json
  src/
    tyler_safety_monitor/
      app/
      camera/
      detection/
      state/
      alerts/
      storage/
      accessibility/
  watchdog/
  tests/
    unit/
    integration/
    fixtures/
  scripts/
  docs/
```

The structure above is the target, not authorization to create source files without first following the repository instructions and obtaining approval for the implementation scope. Tyler authorized Milestone 0 on October 4, 2026 and delegated this project's commit-message choices to the implementing agent; do not ask him for commit wording.

## 14. Implementation milestones

### Milestone 0 — Foundation and camera feasibility

- Create the Python project and test structure.
- Pin a compatible toolchain.
- Open the C920 reliably at the chosen resolution/backend.
- Display a minimized tray app and openable live dashboard.
- Add ROI/exclusion-mask editing and frame-health metrics.
- Benchmark MediaPipe with one and two poses in all supplied lighting conditions.
- Produce no real alerts.

### Milestone 1 — Calibration and recorded-data harness

- Implement the guided safe capture workflow.
- Store local calibration profiles.
- Build a replay harness so recorded safe clips can be tested without requiring Tyler to repeat movements.
- Visualize head trajectory, zones, pose confidence, and second-person tracks.

### Milestone 2 — Detection state machine

- Implement ordinary lean, severe warning, slow recovery, caregiver, away, night, and fault transitions.
- Keep alert adapters in simulated mode.
- Add deterministic unit tests using recorded feature sequences.

### Milestone 3 — Accessible warning and controls

- Implement the dashboard, tray icon, full-screen warning, speech, sounds, and one-action controls.
- Add manual fall and immediate choking triggers in test mode.
- Verify one-finger use.

### Milestone 4 — Twilio messaging

- Store secrets securely.
- Build and verify against simulated messaging first. Tyler requested on
  October 7, 2026 that all real texts, including clearly labeled test messages,
  be deferred until Milestone 6 unless he separately approves an earlier test.
- Implement delivery/error status, message deduplication, one-minute repetition, ten-message maximum, and inbound-reply acknowledgement.
- Arm real messaging only after Tyler verifies the recipient and message text.

### Milestone 5 — Watchdog and startup

- Build the .NET watchdog/notification helper.
- Add Windows sign-in startup.
- Add process heartbeat, restart, actionable notifications, and durable mode restoration.

### Milestone 6 — Supervised validation

- Run the complete scenario matrix below.
- Begin with shadow mode that records what would have happened without sending SMS.
- Review every false positive and missed simulated event.
- After recipient and message review, perform separately approved, explicitly
  labeled real test messages and reply checks before automatic live arming.
- Enable live SMS only after Tyler accepts the observed behavior.

### Milestone 7 — Android cellular fallback

- Research and prototype the USB command channel.
- Build the private companion application.
- Test locked-phone cellular SMS independently of home internet.
- Keep Twilio as the primary channel unless testing supports another order.

### Milestone 8 — Later escalation research

- Consider Twilio voice, a second caregiver, nearby responder, professional monitoring, Pushover, mobile emergency features, and caregiver arrival acknowledgement.
- Design any emergency-service escalation separately.
- Never base an automatic 911 call solely on one computer-vision result or simple caregiver-absence timer.

## 15. Validation matrix

Every case must be tested in ordinary and darkest lighting where relevant.

### Normal behavior

- ordinary sitting and small posture adjustments;
- deliberate head-down lean under 30 seconds;
- deliberate head-down lean that approaches 30 seconds and recovers slowly;
- blankets, clothing colors, glasses glare, drinks, phones, and normal bedside objects;
- TV/reflection content with and without people visible in the reflection;
- intentional night mode and morning reactivation.

### Warning behavior

- ordinary lean exceeding 30 seconds enters the 10-second countdown;
- severe safe simulation enters the 8-second countdown;
- recovery at early, middle, and final countdown points;
- mouse, phone, voice, and visual recovery cancellation;
- manual fall trigger and cancellation;
- immediate choking trigger with no countdown;
- ordinary alarms respect the selected alert volume without changing Windows volume;
- choking temporarily unmutes and reaches maximum volume when no caregiver is present, then restores the previous Windows and application settings;
- the volume control and **Test Sound** are usable with one pointer/tap workflow.

### Caregiver and away behavior

- caregiver enters normally and partially;
- caregiver arrival stops application audio, mutes the active Windows output, and updates the visual state without producing any sound;
- the prior Windows and application volume state returns as soon as caregiver departure is reliably detected, independently of monitoring state or rearming;
- caregiver obstructs the camera;
- caregiver assists and remains in frame;
- caregiver leaves while Tyler remains safe;
- Tyler and caregiver leave together;
- Tyler and caregiver return together;
- Tyler disappears without a caregiver;
- false second-person candidates from reflection, furniture, shadows, and duplicate detections.

### Messaging

- initial fall and choking messages;
- one-minute repeat timing;
- ten-message maximum;
- any valid caregiver reply stops repeats;
- recovery or caregiver appearance stops repeats;
- Twilio rejected, failed, undelivered, and delayed statuses;
- internet lost before and during an incident;
- repeated restart never creates duplicate incidents.

### Reliability

- webcam unplug/replug;
- camera temporarily opened by another process;
- detector process killed;
- detector deliberately hung;
- watchdog restart;
- Windows sign-out/restart;
- UPS/power recovery test that does not endanger stored data;
- full or unavailable event-storage directory;
- clock change while timers use monotonic time.

## 16. Initial acceptance gates

Before enabling live caregiver alerts:

- Camera remains stable for at least 24 continuous hours.
- Watchdog successfully detects and recovers several supervised process failures.
- Each critical state transition passes automated tests.
- Each supervised physical scenario is repeated enough to show consistent behavior.
- Darkest-light tests retain usable Tyler tracking.
- Reflection tests produce no accepted false caregiver tracks.
- Test SMS delivery and caregiver replies work repeatedly.
- Shadow mode runs for an agreed observation period, initially proposed as seven days.
- Tyler reviews the false-positive and missed-event record and explicitly approves live arming.

Passing these gates does not guarantee safety; it establishes a documented minimum for beginning cautious use.

## 17. Known risks and mitigations

| Risk | Mitigation |
| --- | --- |
| Intentional lean resembles danger | Personalized soft/hard zones and two timed paths |
| Severe position prevents all manual input | Automatic severe detection and countdown |
| Person is small in wide frame | Software ROI crop; validate models on actual video |
| Low light reduces landmark quality | Health metrics, low-light validation, possible later lighting improvement |
| Reflection resembles caregiver | Permanent mask plus stable, separate-track requirements |
| Caregiver occludes Tyler | Caregiver mode and tracked arrival sequence |
| False second-person suppresses alert | Two-second persistence, spatial/trajectory validation, exhaustive reflection tests |
| Camera or app silently fails | Independent watchdog, local speech/sound/toasts, automatic restart |
| Internet/Twilio unavailable | Visible local fault now; Android cellular fallback later |
| Duplicate SMS flood | Persistent incident ID, idempotency guard, ten-message maximum |
| Secrets or recordings enter public Git | Strict ignore rules, local data directory, pre-commit checks |
| Automatic mode selects wrong state | Durable deliberate Night mode, visible announcements, accessible manual controls |

## 18. Primary technical references

- Google MediaPipe Pose Landmarker Python options, including live-stream mode and multiple poses: <https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/PoseLandmarkerOptions>
- Google MediaPipe asynchronous live-stream behavior: <https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/PoseLandmarker>
- OpenCV Windows video backends: <https://docs.opencv.org/4.12.0/db/d05/tutorial_config_reference.html>
- Microsoft Windows app notification guidance: <https://learn.microsoft.com/windows/apps/develop/notifications/>
- Microsoft .NET actionable app notifications: <https://learn.microsoft.com/windows/apps/develop/notifications/app-notifications/app-notifications-dotnet>
- Twilio Message resource, including inbound messages and filtered message lists: <https://www.twilio.com/docs/messaging/api/message-resource>
- Android `SmsManager`: <https://developer.android.com/reference/android/telephony/SmsManager>
- Android Debug Bridge and USB debugging: <https://developer.android.com/tools/adb>
