# Tyler Safety Monitor project instructions

Read every project-authored Markdown document before implementation changes. Treat
`FALL_DETECTOR_BLUEPRINT.md` as the approved requirements baseline.

## Feature conflict audit and clarification

- Tyler requested on October 8, 2026 that every feature be audited for conflicts
  with existing features, controls, workflows and approved safety/privacy behavior.
  Check interactions and regressions, not only isolated feature correctness.
  Explain concrete conflicts and resolve them before calling the work complete.
- Tyler explicitly prefers questions whenever the agent is even slightly unsure.
  Ask concise clarifying questions rather than silently choosing an uncertain
  interpretation, requirement or consequential implementation behavior. This
  latest preference supersedes assumptions that he prefers avoiding questions.

- Tyler requested on October 8 that every test-run report include concrete
  examples of behaviors checked, with synthetic evidence distinguished from real
  camera/audio/VoiceAttack validation. Do this consistently, not just totals.

## Latest choking requirements

October 8 choking correction supersedes earlier caregiver-resolution wording:
manual choking remains unresolved until explicit manual Cancel/Resolve. Neither
upright recovery, caregiver entry, caregiver reply nor paired exit resolves it.
Caregiver arrival or a valid caregiver reply stops message repeats durably, while
the choking warning stays open. Caregiver presence still silences app audio.
After reliable caregiver departure, this unresolved choking warning stays silent
until manual Cancel/Resolve; saved computer audio restoration remains independent
of armed state. Re-enabling test audio or changing volume cannot clear that latch.
The choking popup requests foreground activation above ordinary windows, including
fullscreen programs. Contact 911 has its own user-configurable global hotkey for
VoiceAttack, initially unassigned, and works only during enabled test choking.
Real exclusive-fullscreen focus and VoiceAttack delivery require desktop validation.
Contact 911 in Milestone 3 is SIMULATION ONLY: visual feedback, no call, no network
or dialer action, no automatic resolution. Any actual emergency-service contact
requires a separately reviewed implementation and explicit approval.

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
  camera imagery. This earlier approval did not authorize Milestone 2.
- Tyler approved Milestone 2 simulated source, replay, interface, tests and
  documentation on October 7, 2026. Use synthetic evidence and read-only existing
  approved feature replays; personal boundaries remain uncalibrated. No real
  messaging, automatic audio/Windows switching, recording, startup or watchdog.
  This approval does not authorize Milestone 3 or new personal collection.
- Tyler also requested a live diagnostic second-person status and two-second
  confirmation counter, including visible restarts due to flicker. This uses
  existing Full-pose candidates and the explicit Tyler designation, saves nothing,
  and must not enable caregiver identity claims, alert suppression or audio changes.
- Tyler approved on October 7 that automatic posture recovery must not cancel a
  manual choking alert. Explicit Cancel/Resolve, a valid caregiver reply, or
  confirmed caregiver presence stops repeats. Upright posture is not proof that
  choking has resolved; the immediate manual alert remains available in every mode.
- Tyler approved Milestone 3 on October 8, 2026: test-only accessible warning
  screens, one-pointer controls, explicitly enabled app-local speech/sounds and
  configurable global hotkeys for VoiceAttack speech input. No predetermined
  mappings or microphone listener. Hotkeys are editable anytime; an explicit save
  creates new separate hotkey revisions and saved bindings restore on launch.
  Test session and audible output still require separate enable actions per launch.
  Windows volume/mute switching, real SMS, recording, startup/watchdog and new
  personal collection remain outside this approval.
- Tyler approved Milestone 4 simulated messaging source/tests/documentation on
  October 8, 2026. Use synthetic labels, in-memory bounded delivery/reply histories
  and Engine-owned deadlines/repeats. Every scheduled attempt counts toward ten,
  including failed/unknown; fall-to-choking immediately starts a new budget.
  No real SMS, credentials, durable messaging files, dependency additions or new
  normal AppData messaging scope. Milestone 5 and tracking-repair source still
  require approval. Keep real texts and caregiver sessions normally at Milestone 6.
- Tyler requested foreground dashboard startup during development on October 8.
  Keep the default visible until he approves restoring tray-first behavior near
  the end of the project. `--start-minimized` is an explicit optional override.
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

- Tyler requested on October 7, 2026 that all real SMS, including test texts,
  stay deferred until Milestone 6 supervised validation unless he separately
  approves an earlier test. Milestone 4 uses simulated messaging first. Verify
  recipient/text before approved real tests; automatic live arming still needs
  completed acceptance gates and explicit approval.

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

- Use Computer Use only during active UI inspection or actions. End/reset the
  automation session before coding, tests, research or waiting unless a current
  UI action needs it. Do not leave the computer skill active in the background
  during development. Keep the user's monitor session/data intact.

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
