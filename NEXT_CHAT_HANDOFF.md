# Next-task handoff: begin building Tyler Safety Monitor

Use this as the opening message in the new Codex task:

> Continue Tyler Safety Monitor in this existing project. Before changing anything, discover and read every project-authored Markdown file that governs or informs the work, especially `README.md`, `PROJECT_ROADMAP.md`, `FALL_DETECTOR_BLUEPRINT.md`, and `fall_detector/README.md`, plus any `AGENTS.md` instructions. Treat `FALL_DETECTOR_BLUEPRINT.md` as the approved requirements baseline.
>
> Begin with **Milestone 0 — Foundation and camera feasibility** only. First inspect the repository and current environment, then give me a concise implementation plan and identify any remaining choices that truly block Milestone 0. Do not redesign already approved safety behavior without explaining concrete evidence for the conflict.
>
> The published compliance website at the repository root must remain working and its GitHub Pages URLs must not change. Put detector work under `fall_detector/`. Never commit room photographs, calibration captures, incident media, databases, logs, phone numbers, caregiver information, `.env` files, Twilio credentials, or generated secrets.
>
> I use one-finger controls because of a severe physical disability. Preserve the accessibility requirements in the blueprint, including the dashboard's manual alert-volume control. Ordinary alarms use the selected volume; a choking trigger temporarily unmutes and forces maximum output only when no caregiver is present. Caregiver arrival has higher priority: stop app audio and mute the active Windows output, then restore the prior audio state as soon as caregiver departure is reliably detected, regardless of monitoring or armed state. Ask me before repository source-code changes and ask what commit message to use before changing source, firmware, build, or binary artifacts. Documentation-only changes may use a sensible self-describing commit message. Commit and push finished work after verification.
>
> For the first milestone, prioritize a reliable C920 capture spike, ROI/exclusion-mask support, a minimized tray application that opens to a live tracking dashboard, and a benchmark of multiple-person pose tracking in the supplied lighting. Keep all caregiver messaging disabled or simulated. Do not ask me to recreate a dangerous airway-obstructing posture.
