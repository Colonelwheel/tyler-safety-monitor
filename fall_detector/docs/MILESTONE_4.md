# Milestone 4 proposal - simulated messaging

Status: proposal only, October 8, 2026. Source implementation is not approved.
Synthetic messaging work can proceed independently of the queued matching-light
head-position/trail investigation. Tracking-repair source needs separate approval.

## Proposed scope

Build a camera-independent, bounded in-memory fake messaging transport under
fall_detector/. No Twilio client, network request, credentials, real recipients,
new packages or normal AppData messaging storage is included. Synthetic test files
use fresh scratch only. Test Alerts and quiet Simulation retain separate sessions
and clocks; neither reads live candidate diagnostics as caregiver evidence.

| Part | Proposed behavior |
| --- | --- |
| Message content | Preview the blueprint's possible-fall and choking texts, marked SIMULATION ONLY. URGENT belongs only to choking. Use synthetic sender/recipient labels. |
| Timing | Keep Engine as the only scheduler: existing 30/10/8-second fall paths, immediate choking, 60-second repeats, maximum ten slots, and no overdue catch-up burst. |
| Identities | Give sessions, alert episodes and emitted effects stable identities. Dispatch each new message slot once; do not rescan timestamp/kind history as an outbox. |
| Delivery | Model submission, accepted, sent, delivered, rejected, failed, undelivered, delayed and unknown outcomes. Show intent/attempt/accepted/delivered separately; intent is never delivery proof. |
| Errors | Keep the incident active and show failure visually. With existing test-audio opt-in, use local speech to report simulated messaging unavailable at selected volume, through the same audio owner and caregiver/choking-silence priority. No overlapping outputs or blind immediate resend of an unknown outcome. |
| Replies | Accept only unseen synthetic reply IDs from the configured synthetic caregiver to the configured synthetic monitor, created after the current alert episode began. Any matching reply body acknowledges; invalid/old/duplicate replies do nothing. |
| Cancellation | Stop future dispatch after applicable recovery, qualified caregiver, valid reply or manual cancellation. An already submitted message cannot be retracted. Choking resolves only through manual Cancel/Resolve. |
| UI | Put message preview/status and fake outcome/reply controls inside existing scrollable details; keep Cancel, Choking, Stop Audio and simulated Contact 911 reachable. |
| Reset/pause | Pause freezes fake delivery time with the owning simulation clock. Reset/end rejects old-session callbacks and queued work. Quiet replay never activates Test Alerts or audio. |

Proposed source organization: a pure simulation_messaging.py plus focused engine
identity additions and small Test Alerts/Simulation integrations. Preserve engine
incident policy instead of adding another repeat timer. A simulated checkpoint
roundtrip can verify deduplication with in-memory copies; this does not establish
real process-restart durability. Production outbox persistence and credential
storage require a separate destination, side-effect and approval proposal.

## Confirmed choice and pending decision

Tyler confirmed in this chat that upgrading an active fall alert to choking keeps
the current behavior: send an immediate choking intent and begin a new ten-message
budget. Identify the choking episode separately: replies created before it began
and prior-session callbacks cannot acknowledge it. Any unseen matching caregiver
reply created afterward acknowledges regardless of body or which message prompted
the reply. Delivery results never acknowledge or resolve an incident.

Pending Tyler's answer: does the ten-slot cap count every scheduled submission
attempt, including rejected/unknown outcomes, or only accepted messages with a
separately bounded retry policy? Recommended proposal: count each scheduled
attempt, keep accepted/delivered totals separate, and consume uncertain outcomes
conservatively without immediate duplicate sends. Do not implement this choice
until resolved. A new choking budget does not authorize restarting repeats by
repeatedly pressing Choking during the same unresolved choking incident.

## Feature conflicts and preserved behavior

The current Engine effects contain timestamp/kind only and use a bounded history.
That cannot safely serve as an exactly-once dispatch cursor across resets or
history eviction. Stable identities and consumption at each engine transition
must prevent loss/duplicates without replaying old history.

The current message_count counts intents before transport acceptance. UI must keep
that meaning explicit rather than relabeling the count as delivered messages.
Engine remains the single source of deadlines/caps/stopping conditions. Evaluate
valid replies at the current owning clock before an equal-time repeat deadline;
a late reply cannot undo a submission whose deadline already elapsed.

Caregiver arrival stops choking repeats and sets warning silence. A reply stops
repeats without proving caregiver presence or setting that silence latch. Neither
resolves choking or hides its popup. Reliable departure restores saved simulated
computer audio independently of armed state; this unresolved choking warning
stays silent until manual Cancel/Resolve. Delivery/error changes, volume changes,
audio re-enable, Night, tracking gaps and Contact 911 cannot bypass these rules.

Preserve strict two-second caregiver confirmation, affirmative departure,
30-second continuous safe rearm, fixed incident deadlines through uncertainty,
independent live candidate-only counter, all six configurable VoiceAttack hotkeys
and saved-binding restoration. VoiceAttack owns speech INPUT; opted-in local
speech/sounds provide OUTPUT. No microphone listener. Test session/audio remain
disabled per launch, and development startup remains foreground.

## Synthetic verification plan

- Exact initial/repeat deadlines, ten-slot cap, large time jumps without a burst,
  repeated rendering/commands, history eviction, unique session/episode IDs and
  fall-to-choking's new budget.
- Accepted versus delivered state, delayed/duplicate/stale status events, explicit
  rejection/failure/undelivered/unknown outcomes and bounded memory.
- Reply sender/recipient/creation-time/ID filters, equal-deadline ordering,
  rejection of replies created before choking escalation, acceptance of any
  matching reply afterward, and prior-session callbacks after reset.
- Choking arrival/reply retains popup, reliable departure never resumes stopped
  repeats or warning output, manual-only resolution, and visual-only Contact 911.
- Quiet replay, pause/end/restart, disabled commands, selected-volume output,
  persistent essential controls, existing capture guards and candidate isolation.
- Fake-only adapter boundary; no credential/runtime writes or network dispatch.

After approved implementation: independent source review, full isolated synthetic
suite, offscreen layout verification, staged privacy/diff review, updated handoff
and tracking checkpoint, sensible commit and push. Report concrete behaviors,
separating synthetic evidence from hardware/accessibility acceptance.

## Current baseline and deferred gates

Read all twelve project-authored Markdown documents, inspected Git/source/tests,
and obtained an independent read-only integration review. Baseline main at 4cf3ac3
was clean; all 554 synthetic tests passed in 19.77 seconds using the existing
.venv, fresh unique scratch, redirected AppData/temp/caches, offscreen Qt, -B and
pytest without its cache provider. pip check found no broken requirements.

Verified examples include deadlines through missing evidence, strict caregiver
continuity, replies keeping choking active, persistent choking silence after
reliable departure/volume changes, visual-only Contact 911 and separate hotkey
restore versus test/audio opt-in. This is baseline evidence, not Milestone 4 tests.
No source or personal runtime data was changed; no physical device/audio session
was performed. No active Computer Use session was opened.

All real SMS, including test texts, and caregiver participation normally remain
Milestone 6 work. No recording, new personal collection, Windows audio switching,
watchdog/startup, model/profile/settings migration or public website change is
proposed. Retain the OneDrive backup, global Python, dependency pins and separate
ordinary Desktop/Codex AppData namespaces. Matching-light head/trail inspection
remains queued with Tyler. Current code breaks paths across absence/ambiguity,
but bounded historical paths may remain visible during loss. Head circles show
current candidate detections, including uncertain IDs; the Tyler designation needs
fresh subject-accepted evidence. Distinguish these during live inspection. The
reported jump's cause is unverified.
