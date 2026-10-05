# Tyler Safety Monitor project instructions

Read every project-authored Markdown document before implementation changes. Treat
`FALL_DETECTOR_BLUEPRINT.md` as the approved requirements baseline.

## Authorization and commits

- Ask Tyler before repository source-code changes, unless he has already approved
  that scope in the current conversation.
- Tyler authorized Milestone 0 implementation on October 4, 2026, including an
  isolated dependency environment, camera access without saving imagery, and new
  local runtime files. This does not authorize later milestones.
- **Choose sensible, self-describing commit messages for this project. Do not ask
  Tyler for commit wording.** Tyler approved this ongoing preference on October 4,
  2026; it supersedes earlier instructions in the blueprint and handoff to agree
  on a source-code commit message.
- Verify finished work, review staged files for private data, then commit and push.

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
