# Tyler Safety Monitor — Project Roadmap

## How to use this document

This file is the durable project context for future work. A new Codex task should read this file and the repository before making changes. It should not assume that it can see earlier conversation history.

Nothing under **Candidate features** or **Open decisions** is approved merely because it appears here. Ask Tyler whenever a requirement, safety choice, privacy choice, or implementation detail is uncertain.

## Project purpose

Tyler Safety Monitor is a personal, non-commercial Windows safety-monitoring project. Its intended purpose is to use a local camera and other accessible controls to recognize a possible fall, slip, unsafe change in position, or manual request for help; warn Tyler locally; allow an easy cancellation period; and then alert a trusted caregiver when appropriate.

The system should be designed around Tyler's actual normal chair/bed position and movement patterns. It should not assume that the user normally stands or walks.

This project is an assistive backup, not a medical device, professional monitoring service, guaranteed fall detector, or replacement for emergency services and other safety arrangements.

## Current project status

Status recorded: September 9, 2026.

- The public informational and SMS-consent website is complete and published through GitHub Pages.
- Homepage: <https://colonelwheel.github.io/tyler-safety-monitor/>
- Privacy Policy: <https://colonelwheel.github.io/tyler-safety-monitor/privacy.html>
- Terms & Conditions: <https://colonelwheel.github.io/tyler-safety-monitor/terms.html>
- SMS consent information: <https://colonelwheel.github.io/tyler-safety-monitor/consent.html>
- Public project contact: <tyguy9510@hotmail.com>
- The real caregiver completed the Google SMS consent form.
- The existing Twilio A2P campaign was corrected and resubmitted rather than creating a duplicate campaign.
- The Twilio campaign is currently under review.
- The local Windows camera-monitoring program has not yet been implemented.

Never commit caregiver details, phone numbers, consent-form responses, Twilio credentials, Pushover credentials, or other secrets to this repository.

## Core design principles

1. **Local first.** Analyze camera video on Tyler's Windows computer whenever practical. Do not upload or record video by default.
2. **Personalized detection.** Calibrate an expected safe zone and normal posture for Tyler instead of relying only on generic standing-person fall detection.
3. **Multiple signals.** Combine several observations because any single webcam signal can be wrong.
4. **Easy cancellation.** Provide a loud spoken/local warning, a large visible cancel control, and one or more accessible cancellation methods before alerting a caregiver.
5. **Manual help must remain available.** A manual panic trigger should work without waiting for the camera model to identify a fall.
6. **Fail visibly.** Clearly warn Tyler if the camera, pose detection, alert connection, or other critical component stops working.
7. **Minimize false confidence.** Camera angle, lighting, blankets, occlusion, network failure, and limited landmark visibility can all cause missed events or false alarms.
8. **Ask before sensitive behavior.** Recording, uploading images, placing calls, changing recipients, or contacting emergency services requires Tyler's explicit approval.

## Intended system flow

```text
Webcam and manual controls
          ↓
Local body/position observations
          ↓
Personalized risk logic using multiple signals
          ↓
Loud local warning + accessible cancel countdown
          ↓
Alert consented caregiver if not canceled
          ↓
Optional later escalation if explicitly configured
```

## Recommended first version

The first useful version should stay small enough to test safely and understand. Its proposed scope is:

- Run locally on Windows in Python.
- Use OpenCV for webcam capture.
- Start with MediaPipe Pose or another suitable, maintained local pose/landmark library after verifying current compatibility.
- Let Tyler select the camera and see a clear preview/status display.
- Provide a guided calibration step for Tyler's expected head/torso position and safe area.
- Observe more than one possible danger signal, such as:
  - a rapid head or torso movement downward or sideways;
  - the head or torso moving outside the calibrated safe zone;
  - Tyler unexpectedly disappearing from the expected chair/bed area;
  - unusually little movement after a suspicious movement.
- Combine signals over time rather than sending an alert from a single imperfect frame.
- Show a full-screen or very large alarm interface and speak a warning such as, “Possible fall detected. Say cancel or press cancel.”
- Provide an adjustable countdown, initially proposed as 30 seconds.
- Offer at least one extremely easy cancel method; the exact methods must be chosen with Tyler.
- Provide a manual panic trigger that bypasses fall-detection logic.
- Send an SMS through Twilio to the consented caregiver if a warning is not canceled.
- Keep a small local event log containing timestamps, system status, detected reason, cancellation, and alert outcome—but no camera image or video by default.
- Include a test mode that never sends a real alert.

Illustrative logic only—not final thresholds:

```text
IF multiple observations suggest that Tyler left the safe position
   OR a manual panic trigger is activated
THEN show and speak a local warning

IF the warning is not canceled before the configured countdown ends
THEN send an alert to the configured, consented caregiver
```

## Candidate features for later evaluation

These ideas came from the original project discussion but are not yet approved requirements:

- Voice cancellation such as “cancel” or “no, cancel.”
- A VoiceAttack phrase such as “emergency.”
- A single-key keyboard trigger.
- A large browser or phone button.
- Integration with Tyler's Simplecontroller-style app.
- Pushover emergency-priority notifications that repeat until acknowledged.
- Twilio voice calls if nobody acknowledges after a chosen delay.
- A caregiver acknowledgement workflow.
- An explicitly opted-in snapshot attached to an alert.
- An explicitly opted-in private live view.
- Detection of a repeated distress gesture or spoken “help” command.
- Automatic Windows startup and a watchdog that restarts failed components.
- Multiple camera support.
- Offline alarms and alternative alert behavior during an internet outage.

Mouth-open or yelling detection should not be assumed reliable and should not be a first-version requirement without testing.

## Privacy and security requirements

- Process live video locally by default.
- Do not save images, audio, or video by default.
- Do not provide remote viewing by default.
- Require Tyler's explicit approval before enabling snapshots, recordings, uploads, or live viewing.
- Store configuration and logs locally with minimal personal information.
- Keep secrets in a local environment/configuration mechanism excluded from Git.
- Never put a real caregiver's private information or consent record in this public repository.
- Make alert recipients and message behavior visible and testable before enabling live alerts.

## Safety requirements

- Do not automatically contact 911 or another emergency service in the initial version.
- Do not represent alerts as guaranteed delivery or detection as guaranteed accuracy.
- Provide a harmless simulation/test mode for calibration and demonstrations.
- Require an explicit arming step before live caregiver alerts are possible.
- Prevent repeated duplicate messages from one incident.
- Show whether the system is monitoring, paused, calibrating, in test mode, or unable to operate.
- Detect and display camera disconnection and loss of alert connectivity.
- Preserve a manual way to request help even if pose detection is uncertain.

## Implementation stages

### Stage 1 — Requirements and physical setup

- Confirm the camera model, location, angle, field of view, and lighting.
- Describe Tyler's normal safe position or positions.
- Choose accessible manual trigger and cancellation methods.
- Choose the initial countdown duration and caregiver response flow.
- Decide what should happen during camera or internet failure.

### Stage 2 — Offline observation prototype

- Create the Windows/Python application structure.
- Display the camera feed and system status.
- Add local pose/head/torso observations.
- Build calibration and safe-zone visualization.
- Log observations locally without sending alerts.
- Collect false-positive/false-negative test notes with Tyler.

### Stage 3 — Local warning and manual controls

- Add the alarm screen, spoken warning, countdown, and cancellation.
- Add the manual panic trigger.
- Add test/simulation mode.
- Verify that controls work with Tyler's actual accessibility needs.

### Stage 4 — Caregiver alerts

- Wait for the Twilio campaign to be approved before relying on production SMS.
- Add Twilio SMS using credentials stored outside Git.
- Confirm the recipient is the caregiver who provided consent.
- Add duplicate suppression, delivery/error status, and safe test messaging.

### Stage 5 — Reliability trial

- Run supervised tests across expected lighting, clothing, blankets, camera obstructions, and normal movements.
- Tune personalized thresholds conservatively.
- Test camera failure, application restart, Windows restart, and internet loss.
- Document known limitations before using the program as a safety aid.

### Stage 6 — Optional escalation

- Evaluate Pushover acknowledgement alerts.
- Evaluate Twilio voice calls.
- Evaluate phone/Simplecontroller integration.
- Consider snapshots or private live viewing only after a separate privacy decision.

## Open decisions for Tyler

These must be answered during the appropriate implementation stage, not guessed:

1. Which camera will be used, and where will it point?
2. Is the primary normal position a chair, bed, or more than one location?
3. What visible change most strongly indicates that Tyler may have slipped or fallen?
4. Which cancellation methods are physically easiest and most dependable?
5. Which manual panic methods should be included first?
6. Is 30 seconds an appropriate initial cancellation window?
7. Should inactivity be considered, and if so, after how long and in what circumstances?
8. Should caregiver alerts begin with Twilio SMS only?
9. Should Pushover or Twilio voice calling be added later?
10. Are snapshots ever acceptable, or should the system permanently avoid them?
11. What should the system do if the internet is unavailable?
12. Should the monitor start automatically with Windows?

## First task for the camera-program phase

Before writing detection code, inspect this roadmap and the existing repository, then ask Tyler the smallest set of concrete questions needed for **Stage 1 — Requirements and physical setup**. Do not silently choose safety, accessibility, privacy, or alert-escalation behavior.

