# Milestone 2 — Simulated detection state machine

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

Approved October 7, 2026. This is a practice version of the decision rules: it
shows when the future monitor would warn, cancel, stay quiet for a caregiver, or
report uncertainty. It never sends a message or changes audio. Simulation does
not need the camera or reproduced lighting conditions.

## Implementation

- A pure state engine separates operating mode, incident state, uncertainty,
  fault status, caregiver presence and simulated audio priority.
- Ordinary lean has 30 seconds of grace followed by a 10-second warning.
  Severe evidence/manual possible fall has an eight-second warning; manual
  choking produces an immediate simulated intent. Repeats are spaced by 60
  seconds and limited to ten total, with no overdue catch-up burst.
- One incident retains its original deadline through missing, uncertain or
  faulted observations. Severe escalation cannot lengthen a deadline. A fault
  alone does not create an emergency incident. Night prevents new automatic
  incidents while preserving an existing incident and manual commands.
- Positive recovery is a separate supplied scenario fact, not a consequence of
  a head being visible. Slow movement into a safe range does not cancel before
  recovery confirmation. Missing evidence cannot count as recovery.
- Tyler explicitly approved that automatic posture recovery never cancels a
  manual choking alert. Explicit cancellation/resolution, a simulated valid
  caregiver reply, or confirmed caregiver presence stops repeats. Choking is
  not inferred from camera observations.
- Caregiver confirmation requires the same separate synthetic candidate with
  fresh continuous supporting observations for two seconds. Missing/ambiguous
  results, candidate changes or excessive observation gaps reset confirmation.
  A confirmed caregiver remains present through occlusion until affirmative
  departure evidence is supplied. Empty frames cannot establish safe departure.
- A paired exit requires a previously qualified caregiver plus explicit joint
  exit evidence. Reliable departure restores the simulated saved audio state
  independently of Night, Fault, Away or arming. Rearming then requires 30
  continuous seconds of confirmed safe evidence. Caregiver silence outranks
  choking maximum-volume intent.
- Playback evaluates every event at its source timestamp, even when one UI
  refresh consumes many events. Pause freezes simulation time; restarting clears
  all simulation state/effects. End of a replay freezes, rather than fabricating
  additional time or observations. Exact-deadline positive recovery/cancellation
  can precede expiry; evidence received after expiry cannot undo an earlier intent.
- The independent Simulation tab has large single-action controls and persistent
  Cancel/Play controls. It does not control the camera or calibration and is
  paused by default. Existing tray, volume and feature-capture controls remain.
- At Tyler's request, the live dashboard separately shows current second-person
  candidate evidence, observed confirmation progress from 0.0 to 2.0 seconds,
  the reset count and why it restarted. It requires a freshly eligible explicit
  Tyler selection and one separate clear Full-pose candidate. Empty/ambiguous
  results, candidate changes, unsupported association or stale observations
  restart it. Refresh ticks never manufacture observed time. Confirmation is
  labeled **Caregiver candidate confirmed — diagnostic only**; it makes no
  identity decision and never suppresses alerts or changes audio.

## Inputs and policy boundaries

Synthetic scenario facts exercise the reducer, not person recognition or medical
classification. `safe_confirmed`, `recovery_confirmed`, reliable departure and
paired exit are explicit test facts; production criteria remain to be validated.
The 0.4-second synthetic freshness parameter is configurable and is not an
approved operational tolerance. Continuous caregiver evidence does not mean
summing disconnected detections or counting unobserved gaps as proof.

The live diagnostic counter uses 0.4-second freshness and 0.15 original-frame
normalized separation/motion allowances drawn from existing association policy.
These are provisional diagnostics, not accepted caregiver thresholds. Actual
mask coverage, proximity, occlusion and identity errors still require validation.
The live evidence counter resets when current evidence disappears, even after
two seconds; it is separate from the simulated caregiver audio latch, which
retains silence until affirmative departure. The simulation distinguishes
retained caregiver silence from currently available caregiver evidence.

Existing approved feature replays can be opened read-only. Their source intervals,
coordinates and provenance are retained; their saved format is unchanged. They
remain uncalibrated/unknown and cannot supply recovery, caregiver, severe-event
or safe-exit claims. An optional explicitly designated replay candidate in the
runner supports availability diagnostics only; saved positions do not identify
Tyler. Visualization-reviewed zones do not approve operational safety thresholds.

The experimental face comparison remains separate from Full-pose calibration,
selection and detection simulation. A later fusion candidate could require two
models to agree on the same spatially separate person over time, but a high
detector score is not an identity guarantee. False detections may have high
scores and models may share errors. No fusion, new model acquisition or relaxed
caregiver-continuity rule is implemented by this milestone.

## Verification

- All **430 synthetic tests passed** in the final full suite (323 prior plus
  107 new cases). New coverage includes exact timing boundaries, late/missing
  evidence, severe escalation, positive recovery, manual choking cancellation,
  caregiver flicker/departure/paired exit, independent audio priority, source-time
  batching/pause/rewind/stepping, and live diagnostic counter resets.
- The existing isolated environment's `pip check` passed; no dependencies changed.
- Independent review reproduced caregiver-handled choking resuming after departure;
  the durable stop and regression prevent that. Review also identified manual-fall
  warnings with an already confirmed caregiver; those requests are now handled
  without a pending warning or simulated fall message. Severe escalation during
  lean grace uses the previous alert deadline, not the grace transition time.
- Offscreen synthetic previews were checked with the existing Windows font loaded
  read-only. Tests preserve 60-pixel controls, persistent Cancel/Play, zero horizontal
  scrolling in the simulation panel, and visible essential controls at reduced
  height. The requested live diagnostic uses fake observations in tests; actual
  ordinary Desktop/caregiver behavior has not yet been checked live.
- The full suite used fresh isolated AppData and pytest scratch, with bytecode and
  pytest caches disabled. No hardware, personal collection, imagery sharing or
  real adapters were exercised. The 19-file staged privacy review and staged
  whitespace check passed. Public website files and dependency pins are unchanged.

## Current data and limitations

Read-only inspection found valid saved profiles with no zones/reviews and zero
margin, plus the two approved feature replays. Ordinary host AppData and Codex's
retained cache were inspected separately; their settings/model counts differ.
Matching logical environment paths must not substitute for physical-path checks.
No runtime file is merged, replaced, moved or deleted. The isolated Python 3.12.8
environment and dependency pins are reused; global Python remains untouched.

Tyler reports reliable tracking in brighter conditions and flicker in dim light.
This supports a lighting dependency but does not establish accepted worst-light
recognition. Persistent new-ID reattachment remains synthetically verified;
the previous ordinary Desktop check observed selection through missing/visible
states but no new P number. Caregiver recognition, physical recovery criteria,
longest recognition gaps, real audio restoration and all later live-alert gates
remain pending. No caregiver participation is needed now; supervised work stays
deferred to Milestone 6 unless an earlier concrete dependency is agreed upon.

## Moving to Milestone 3

Milestone 2 is complete when the simulated decisions, timing/gap safeguards,
one-action panel and preservation checks pass. This does not require perfect
per-frame camera recognition and does not authorize live use. Milestone 3 adds
the actual accessible warning screen and controls, with speech/sounds in test
mode after a separate proposal and approval. Windows audio switching must be
explicitly scoped before implementation. Messaging, recording and watchdog
behavior remain outside this milestone.

Launch the normal Desktop shortcut to retain the established user runtime view.
For a movement-free test, use the existing `--no-camera --show` command in the
detector README and open **Simulation**. Select a scenario and **Play / Pause
Simulation**. The panel never enables real alerts.
