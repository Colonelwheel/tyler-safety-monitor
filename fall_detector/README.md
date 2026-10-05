# Fall Detector application

This directory is reserved for the local Windows monitoring application described in [`../FALL_DETECTOR_BLUEPRINT.md`](../FALL_DETECTOR_BLUEPRINT.md).

No implementation code exists yet. The first implementation task is **Milestone 0 — Foundation and camera feasibility**.

## Repository boundaries

- Keep the existing GitHub Pages website at the repository root working.
- Put detector source, tests, watchdog, scripts, and detector-specific documentation beneath this directory.
- Never commit camera photographs, calibration captures, event recordings, logs, databases, caregiver details, phone numbers, credentials, or local configuration.
- Store runtime data beneath `%LOCALAPPDATA%\TylerSafetyMonitor`, not inside the repository.

## Required reading

Before making implementation changes, read:

- `../README.md`
- `../PROJECT_ROADMAP.md`
- `../FALL_DETECTOR_BLUEPRINT.md`
- `../NEXT_CHAT_HANDOFF.md`
- any applicable `AGENTS.md`

