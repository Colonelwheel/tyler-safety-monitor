# Tyler Safety Monitor project instructions

Read every project-authored Markdown document before implementation changes. Treat
`FALL_DETECTOR_BLUEPRINT.md` as the approved requirements baseline.

## Authorization and commits

- Ask Tyler before repository source-code changes, unless he has already approved
  that scope in the current conversation.
- Tyler authorized Milestone 0 implementation on October 4, 2026, including an
  isolated dependency environment, camera access without saving imagery, and new
  local runtime files. This does not authorize later milestones.
- Tyler approved Milestone 1 tooling/source/documentation on October 5, 2026,
  with synthetic verification. Actual personalized collection and saving imagery
  were not authorized by that implementation approval. Feature capture and saves
  require the visible, separate user confirmations; this milestone never saves
  camera imagery. Milestone 2 still needs approval.
- **Choose sensible, self-describing commit messages for this project. Do not ask
  Tyler for commit wording.** Tyler approved this ongoing preference on October 4,
  2026; it supersedes earlier instructions in the blueprint and handoff to agree
  on a source-code commit message.
- Verify finished work, review staged files for private data, then commit and push.
- **Whenever a milestone is complete, create or update `NEXT_CHAT_HANDOFF.md`
  for the next milestone before finishing.** Include the completed milestone's
  implementation and verification, known limitations, deferred validation,
  current launch instructions, and a ready-to-use next-chat prompt. Keep the
  next milestone's approval boundaries explicit; a handoff does not authorize
  its source changes or recording. Verify, commit, and push the handoff with
  the finished project work. Tyler requested this standing rule on October 5,
  2026.

## Caregiver participation schedule

- Tyler requested on October 5, 2026 that actual caregiver involvement be deferred
  until the latest practical development point, normally consolidated with
  Milestone 6 supervised validation. Build tooling and simulated caregiver tests
  first; do not repeatedly request caregiver samples during earlier milestones.
- Keep caregiver behavior in its approved implementation milestones. If a concrete
  dependency or safety requirement needs earlier participation, explain why and
  agree on the smallest necessary session with Tyler. Assisted calibration steps
  remain pending when assistance is unavailable; never substitute unsafe solo
  movements. Complete required real caregiver validation before enabling live alerts.

## Preservation and scope

- Leave the existing Python installations and their installed packages unchanged.
  Install detector dependencies only in an isolated virtual environment.
- Keep application work under `fall_detector/`. Keep the static compliance site
  at the root and preserve its published GitHub Pages URLs.
- Never commit room photographs, calibration captures, incident media, databases,
  logs, phone numbers, caregiver information, `.env` files, credentials, or secrets.
- Use `%LOCALAPPDATA%\\TylerSafetyMonitor` for new runtime data; never overwrite or
  remove existing unrelated files. Camera imagery is not saved in Milestone 0.
- Preserve all approved one-finger controls and safety behavior. Caregiver silence
  overrides choking audio; departure restores prior audio independently of armed
  or monitoring state. Milestone 0 keeps emergency actions simulated.
- Do not ask Tyler to recreate an airway-obstructing posture.
- Use parallel subagents when they materially improve implementation or verification.
