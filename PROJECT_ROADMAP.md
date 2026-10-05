# Tyler Safety Monitor — Project Roadmap

## How to use this document

This file is the durable project context for future work. A new Codex task should read this file and the repository before making changes. It should not assume that it can see earlier conversation history.

Nothing under **Candidate features** or **Open decisions** is approved merely because it appears here. Ask Tyler whenever a requirement, safety choice, privacy choice, or implementation detail is uncertain.

## Project purpose

Tyler Safety Monitor is a personal, non-commercial Windows safety-monitoring project. Its intended purpose is to use a local camera and other accessible controls to recognize a possible fall, slip, unsafe change in position, or manual request for help; warn Tyler locally; allow an easy cancellation period; and then alert a trusted caregiver when appropriate.

The system should be designed around Tyler's actual normal chair/bed position and movement patterns. It should not assume that the user normally stands or walks.

This project is an assistive backup, not a medical device, professional monitoring service, guaranteed fall detector, or replacement for emergency services and other safety arrangements.

## Current project status

Status updated: October 4, 2026.

- The public informational and SMS-consent website is complete and published through GitHub Pages.
- Homepage: <https://colonelwheel.github.io/tyler-safety-monitor/>
- Privacy Policy: <https://colonelwheel.github.io/tyler-safety-monitor/privacy.html>
- Terms & Conditions: <https://colonelwheel.github.io/tyler-safety-monitor/terms.html>
- SMS consent information: <https://colonelwheel.github.io/tyler-safety-monitor/consent.html>
- Public project contact: <tyguy9510@hotmail.com>
- The real caregiver completed the Google SMS consent form.
- The existing Twilio A2P campaign was corrected and resubmitted rather than creating a duplicate campaign.
- Twilio approved the A2P campaign on September 10, 2026.
- A Twilio number is assigned to the approved campaign; real test messaging is not yet complete.
- Milestone 0 now provides an isolated Python 3.12 Windows tray/dashboard, memory-only C920 capture, ROI/exclusion editing, observational pose candidates, manual app-volume controls, and local benchmark tools. Emergency detection and caregiver messaging remain disabled. See `fall_detector/docs/MILESTONE_0.md` for measurements and deferred validation.
- The implementation requirements are now defined in `FALL_DETECTOR_BLUEPRINT.md`.

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

## Confirmed first version

The first useful version should stay small enough to test safely and understand. The detailed requirements and implementation stages are in `FALL_DETECTOR_BLUEPRINT.md`. Its confirmed scope includes:

- Run locally on Windows in Python.
- Use OpenCV for webcam capture.
- Start by validating MediaPipe Pose or another suitable, maintained local pose/landmark library against the actual camera and darkest lighting.
- Let Tyler select the camera and see a clear preview/status display.
- Provide a guided calibration step for Tyler's expected head/torso position and safe area.
- Observe more than one possible danger signal, such as:
  - a rapid head or torso movement downward or sideways;
  - the head or torso moving outside the calibrated safe zone;
  - Tyler unexpectedly disappearing from the expected chair/bed area;
  - unusually little movement after a suspicious movement.
- Combine signals over time rather than sending an alert from a single imperfect frame.
- Show a full-screen or very large alarm interface and speak a warning such as, “Possible fall detected. Say cancel or press cancel.”
- Allow an ordinary forward lean for 30 seconds and then provide a 10-second countdown.
- Use an 8-second countdown for a confidently detected severe collapse or manual possible-fall trigger.
- Send the manual choking alert immediately without a countdown.
- Offer at least one extremely easy cancel method; the exact methods must be chosen with Tyler.
- Provide a manual panic trigger that bypasses fall-detection logic.
- Send an SMS through Twilio to the consented caregiver if a warning is not canceled.
- Repeat an unacknowledged alert every minute, up to ten messages total, stopping on recovery, caregiver presence, resolution, or any caregiver reply.
- Keep a local event log and incident-only video beginning approximately 20 seconds before detection, limited to two minutes per incident and deleted after 30 days.
- Include a test mode that never sends a real alert.
- Start minimized, open to a live camera/tracking dashboard, and use an independent watchdog with actionable Windows notifications.
- Provide a manually selected alert-volume control and **Test Sound**. Ordinary alerts respect that selection; only the choking trigger temporarily unmutes and forces maximum system/application volume before restoring prior settings.
- On caregiver arrival, immediately stop Fall Detector audio and mute the active Windows output so all computer audio is silent. Preserve the prior audio state and restore it as soon as caregiver departure is reliably detected, regardless of monitoring or armed state. Caregiver-mode silence overrides choking maximum-volume behavior.

Illustrative logic only—not final thresholds:

```text
IF an ordinary lean lasts 30 seconds
THEN show and speak a 10-second warning

IF a severe collapse is detected
   OR the manual possible-fall trigger is activated
THEN show and speak an 8-second warning

IF the warning is not canceled before the configured countdown ends
THEN send an alert to the configured, consented caregiver

IF the manual choking trigger is activated
THEN send the choking alert immediately
```

## Candidate features for later evaluation

These ideas came from the original project discussion but are not yet approved requirements:

- Additional voice cancellation phrases beyond the initial secondary voice control.
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
- Multiple camera support.
- Additional offline alert channels beyond the planned Android USB/cellular fallback.

Mouth-open or yelling detection should not be assumed reliable and should not be a first-version requirement without testing.

## Privacy and security requirements

- Process live video locally by default.
- Save only approved incident media locally; do not continuously record.
- Do not provide remote viewing by default.
- Do not upload snapshots, recordings, or live video in version one.
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

### Stage 1 — Requirements and physical setup (complete)

- Requirements, camera, scene, accessibility controls, alert timing, caregiver flow, storage, and failure behavior are documented in `FALL_DETECTOR_BLUEPRINT.md`.

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

## Decisions deferred until implementation or later phases

These must not be guessed when their implementation stage arrives:

1. Exact calibrated soft and hard position boundaries after safe supervised capture.
2. Final pose/head model after benchmarking the actual C920 footage.
3. Exact voice phrases and recognition implementation.
4. Whether seven days is the appropriate shadow-mode validation period.
5. Detailed Android USB/cellular fallback design.
6. Later escalation beyond SMS, including voice calls, additional contacts, professional monitoring, or emergency services.

## First task for the camera-program phase

Read `FALL_DETECTOR_BLUEPRINT.md` and `NEXT_CHAT_HANDOFF.md`, then begin **Milestone 0 — Foundation and camera feasibility**. Do not silently change approved safety, accessibility, privacy, or alert-escalation behavior.

Milestone 0 implementation is now complete within the explicitly limited observation scope. Tyler deferred caregiver-entry samples; true simultaneous two-person tracking remains unvalidated. Do not proceed to Milestone 1 without approval for that new scope. The supplied lighting photographs were ordinary photographs, not instructed movement tests.

Tyler delegated this project's commit-message choices to the agent on October 4, 2026. Choose sensible messages without asking him for wording. Preserve his existing Python installations and packages; use only the detector's isolated environment. `AGENTS.md` records these ongoing project instructions.
