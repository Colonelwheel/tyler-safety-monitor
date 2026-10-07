# Tyler Safety Monitor website

This repository contains the public informational and SMS-consent website and the planned local Windows fall-detector application for **Tyler Safety Monitor**, a personal, non-commercial safety alert project.

The site uses plain HTML and CSS. It has no build step, analytics, trackers, cookies added by the project, database, or JavaScript.

## Fall Detector planning

- `PROJECT_ROADMAP.md` — durable project status and staged roadmap
- `FALL_DETECTOR_BLUEPRINT.md` — approved safety, accessibility, architecture, and validation requirements
- `NEXT_CHAT_HANDOFF.md` — ready-to-use prompt and current context for the next milestone
- `fall_detector/` — reserved home for the Windows application

Milestones 0 and 1 provide an observation-only Windows tray/dashboard, guided feature-only calibration, local versioned profiles, and a synthetic/approved-local-data replay harness. See [`fall_detector/README.md`](fall_detector/README.md) for launch instructions and validation limits. Personalized calibration remains pending. Emergency detection, caregiver audio switching, and real messaging are not implemented. Runtime photographs, recordings, personalized features, logs, databases, credentials, phone numbers, and caregiver information must never be committed.

Milestone 2 adds an isolated simulation panel for warning/recovery/caregiver/away/
night/fault decisions. It emits in-memory descriptions of what would happen;
actual messaging, automatic audio, recording and startup behavior remain disabled.

## Pages

- `index.html` — homepage
- `privacy.html` — Privacy Policy
- `terms.html` — Terms & Conditions
- `consent.html` — SMS disclosure and the real Google SMS Consent Form

## Before publishing or resubmitting to Twilio

1. Confirm the linked Google Form is public and contains an explicit, unchecked SMS-consent checkbox with disclosures matching `consent.html`.
2. Publish this repository through GitHub Pages from the `main` branch and root (`/`) folder.
3. Test every public page in a private/incognito window while logged out of both GitHub and Google.
4. Have the real caregiver complete the consent form. Never place the caregiver's response or private information in this repository.
5. Resubmit the existing rejected Twilio campaign; do not create a second campaign.

## Local preview

The files can be opened directly in a browser. A local web server is optional.
