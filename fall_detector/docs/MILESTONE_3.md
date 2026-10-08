# Milestone 3 — Accessible warning tests and configurable VoiceAttack input

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

Approved October 8, 2026. Tyler separately clarified that speech INPUT belongs to
VoiceAttack and hotkeys must be user-settable anytime. Speech OUTPUT remains in
the monitor. The approval covers local test playback at selected app volume;
Windows volume/mute switching and real emergency adapters remain simulated.

## Implementation

- A separate manual test session owns a pure Engine and monotonic clock without
  finite replay limits. Session defaults disabled and audio off on every launch.
  Commands cannot enable either implicitly. Quiet Simulation replay is preserved.
- The topmost full-screen warning displays test-only status, incident reason,
  original countdown and uncertainty. Cancel is dominant; Choking, simulated
  Contact 911 and Stop Test Audio remain reachable with one pointer during a warning. Escape/close explicitly
  cancel the test incident. Manual triggers remain usable in every test mode.
- Actual speech/tones are created lazily after explicit audio opt-in. Output uses
  current selected app volume, including choking demonstrations. Speech uses the
  already installed local Windows SAPI engine, with no dependency or voice download.
  Latest-state keys deduplicate refreshes; cancel, pause, caregiver silence, End
  and shutdown stop pending speech/tone output. No backlog of effects is replayed.
- Synthetic scenario facts are selected explicitly. Missing/faulted data cannot
  extend incident timers or imply recovery/departure. Two continuous seconds of
  the same caregiver candidate are required; uncertainty after qualification
  retains caregiver silence. Reliable synthetic departure restores saved audio independently of
  Night/Fault/Away/arming, with safe rearm separate. Choking survives posture
  recovery, caregiver entry/reply and paired exit. Those caregiver events stop
  repeats without resolving; departure cannot resume stopped repeats. Only explicit
  manual Cancel/Resolve ends the incident.
- Six configurable global actions use owned Windows WM_HOTKEY registrations,
  MOD_NOREPEAT and queued GUI delivery. No keyboard hook or microphone listener.
  Key and modifier widgets accept separate taps, with no chord-holding requirement.
  Apply/Remove works anytime, conflicts preserve the previous valid binding,
  stale queued registrations cannot activate new bindings, and shutdown releases
  only owned shortcuts. No mappings are predetermined; OS-reserved keys are rejected.
- Explicit hotkey Save creates new exclusive revisions in a separate hotkeys
  directory, preserving prior revisions and the existing AppSettings schema.
  Startup loads the newest revision read-only; corrupt revisions and registration
  conflicts fail visibly. Saved hotkeys restore automatically, but Test Session
  and audible output still need separate enable actions after reopening.
- Dashboard startup now opens foreground during development at Tyler's request.
  `--start-minimized` retains the final tray-first workflow explicitly. Restore
  tray-first by default near project completion only after Tyler approves it.
- Mutual feature-capture/test-session guards are checked again after capture
  confirmation. Existing samples remain intact; no camera/scene/selection mutation
  occurs when enabling a test. The live second-person diagnostic stays candidate-only
  and cannot control the test engine or audio.

## Verification and conflict audit

All **554 synthetic tests passed** in 12.10 seconds using the existing isolated
Python environment, fresh unique scratch, redirected AppData, offscreen Qt,
`-B` and pytest without its cache provider. `pip check` found no broken requirements.
Tests use fake cameras, native registrations/foreground APIs, speech and audio.

Concrete examples verified:
- fixed warning deadlines continue through missing/uncertain evidence;
- caregiver arrival/reply stops choking repeats without resolving the incident;
- reliable departure restores saved simulated audio independently of armed state,
  while unresolved choking warning audio remains silent through opt-in/volume changes;
- only manual Cancel/Resolve clears choking; a subsequent new incident can sound;
- Contact 911 button/hotkey requires active test choking and produces only visual
  feedback, never a call, process launch, network action or incident resolution;
- foreground requests occur on appearance/fall-to-choking and explicit actions,
  while ordinary refresh ticks do not steal focus;
- hotkey conflicts preserve the current registration and stale queued events are
  rejected; newest append-only saves load correctly even if timestamps tie/regress;
- previous five-action revisions load without rewriting them, with Contact 911
  initially unassigned;
- Test Sound stops warning audio but leaves the incident/popup active;
- capture guards retain existing samples and the live candidate counter cannot
  silence warning audio or turn into operational caregiver recognition.

Independent source review found no remaining concrete conflict in those paths.
Offscreen visual review with installed Segoe UI and enlarged text at 800x600
confirmed visible Choking, Stop Audio, simulated Contact 911 and dominant Cancel,
including post-contact confirmation. Essential actions stay outside the detail
scroll area. This is layout evidence, not physical accessibility acceptance.
`git diff --check` passed. Staged privacy review passed for all 26 source/test/document files; no private runtime data or binary artifacts are included.


Feature conflict review covered quiet replay/manual clocks, warning deadlines,
caregiver and choking priority, diagnostic isolation, manual/warning sound overlap,
capture visibility and stored samples, global-key conflicts/replacements, delayed
speech callbacks and crowded/scaled layouts. Full-screen warnings initially hid
Choking/Stop Audio; those controls are now directly available on the warning.
Fall countdown expiry is labeled active rather than immediate; only choking uses
the immediate label. One earlier assertion now explicitly permits labeled test
controls in Test Alerts as well as Simulation, while verifying silent/disabled
startup. Tracking, settings and feature schemas are unchanged; the pure engine now
exposes explicit choking identity and its durable warning-silence latch.

The existing Test Sound button explicitly stops warning speech/sounds and plays
its single selected-volume tone, while retaining the incident/popup. Simulated
caregiver silence still blocks that tone. This avoids competing app audio outputs.

## Deferred fullscreen/VoiceAttack acceptance

- Deferred by Tyler on October 8 until Milestone 6: test first warning appearance
  and fall-to-choking transition while an ordinary window, borderless fullscreen
  program and true exclusive-fullscreen program are active. Verify the popup comes
  forward and Cancel plus simulated Contact 911 work through independently chosen
  global hotkeys/VoiceAttack without using a mouse. Check display scaling/multiple
  monitors, registration conflicts, disabled-session guards and recovery of focus.
  Do not mark this accepted from offscreen tests; no real 911 call is part of it.

## Deferred validation and boundaries

Actual audible SAPI/output behavior, VoiceAttack key delivery, fullscreen game
compatibility, physical one-finger acceptance and live tracking accuracy remain
unverified. Automated tests use fake devices, registrations and speech. No caregiver
session or physical movement is required now. The ordinary monitor was not restarted
and unsaved user session data was not discarded.

Personal zones/margins remain unapproved. No new personal feature data, images, recordings,
models, runtime migrations, system-volume changes, SMS, microphone recognition,
startup registration or watchdog were exercised/implemented. Codex's packaged
AppData namespace may differ from the ordinary Desktop namespace; preserve both
copies and use the ordinary Desktop launch for later user validation. The OneDrive
backup, global Python, isolated dependency pins and root public website are retained.

Milestone 4 requires a separate proposal/approval and develops simulated messaging
first. All real texts, including test SMS, remain deferred to Milestone 6 unless
Tyler separately approves an earlier test. Required caregiver/supervised validation
and explicit live arming remain later gates.

## Launch

Use the normal Desktop shortcut or `fall_detector/Start Monitor.cmd`. It opens the
dashboard in the foreground during development. Preserve unsaved samples/settings
before any user-convenient exit/relaunch. For camera-free work use the existing
`pythonw.exe -B -m tyler_safety_monitor --no-camera --show` command. Open Test Alerts,
Enable Test Session, then test/cancel a manual fall. Audio stays off until separately
enabled. Open Hotkeys to choose/apply/save your own bindings; nothing is predetermined.
