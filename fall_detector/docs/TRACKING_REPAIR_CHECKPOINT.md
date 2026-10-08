# Tracking repair checkpoint

## Next work: Milestone 4 can proceed independently of the lighting check

Tyler clarified October 8 that simulated messaging can be proposed and, after
separate source approval, implemented/tested with synthetic incidents while waiting
for the matching nighttime lighting. The low-light head-position/trail repair
remains queued for that session; it does not block simulated Milestone 4 work.

Prepare message content/status, delivery/error simulation, duplicate prevention,
one-minute repeats capped at ten messages, and simulated caregiver replies. Retain
manual-only choking resolution and caregiver silence/repeat rules. No actual
credentials or caregiver participation are needed for initial simulation. Propose
secure credential storage separately before introducing its runtime scope. All
real texts, including test texts, remain deferred to Milestone 6 unless Tyler
separately approves an earlier test. This scheduling update approves documentation
only, not Milestone 4 or tracking-repair source changes.


## Pending: low-light head-position jump — next matching nighttime session

Requested October 8, 2026. Tyler reported low-light flickering followed by a blue
head/trail line far from his actual head, as though a brief tracking dip teleported
it. Investigate when he returns to this same lighting level (requested tomorrow
night). This follow-up does not block simulated Milestone 4 work. The screenshot
supports an apparent
tracking/display error; its detection, identity, stale-position or trail cause is
not yet verified. Do not copy the private screenshot into the repository.

Inspect raw versus accepted head positions and loss/reacquisition/trail behavior.
Propose a small repair: explicitly uncertain position during loss, trail breaks
across unreliable observations, and credible reacquisition without rejecting real
fast movement/collapse. Preserve fixed incident timers; missing tracking is never
recovery, caregiver confirmation or departure. Verify synthetic dropout/outlier,
reacquisition and genuine-movement cases, then check the matching lighting with
Tyler. No movement challenge, recording or new personal collection is approved.
This entry authorizes notes only; ask before implementing the tracking repair.


## October 8, 2026: Milestone 3 completed in test mode

The separate manual Test Alerts session, actual accessible warning UI, opted-in
local speech/sounds and six configurable VoiceAttack hotkey actions are implemented.
Saved bindings restore read-only; test session/audio still default disabled each
launch. Dashboard opens foreground during development. Contact 911 remains clearly
SIMULATION ONLY, with a guarded configurable global shortcut and visual feedback.
Choking popup stays active during caregiver silence and paused test clock; only
manual Cancel/Resolve resolves it. Caregiver entry/reply stops repeats durably.
Reliable departure restores saved simulated computer audio, while this choking
warning remains silent until manual resolution. Test Sound explicitly stops warning
output and plays its one tone without resolving the incident.

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

Tyler deferred real fullscreen/VoiceAttack acceptance until Milestone 6. Test first
warning and fall-to-choking foreground behavior over ordinary, borderless and
exclusive fullscreen apps; verify independently chosen Cancel/Contact 911 hotkeys
via VoiceAttack without a mouse, scaling and multiple monitors, conflict/disabled
guards and focus recovery. Windows can deny activation; offscreen mocks do not
establish actual visibility. No live desktop, caregiver session or real output was
exercised. Actual Windows audio switching, real SMS (even test texts), recording,
new personal collection, startup/watchdog remain unapproved/deferred. Profiles,
features/settings/models, the OneDrive backup/global Python/dependency pins/public
HTML/CSS were preserved. Ordinary Desktop and Codex AppData copies remain separate.

Next: read NEXT_CHAT_HANDOFF.md and propose Milestone 4 simulated messaging;
obtain separate approval before implementation. Do not restart the user's existing
monitor or discard unsaved data. Read every project-authored Markdown first, audit
feature conflicts, ask whenever uncertain and report behavior examples with tests.


## Latest October 8 choking clarification

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

Implementation/tests now enforce this newer baseline. Earlier October 7
resolution statements below are retained as historical evidence and superseded.
Tyler confirmed persistent choking-warning silence after reliable departure.


## Historical October 8 approval and pre-implementation baseline

Tyler approved Milestone 3 implementation after reviewing the test-only warning,
local speech/sound output, one-pointer controls and simulated audio boundaries.
He clarified that VoiceAttack will own speech INPUT and send configurable global
hotkeys. Hotkeys must be user-settable at any time, with no predetermined bindings.
Implement this in Milestone 3, not a separate speech-recognition listener. No
microphone capture or VoiceAttack profile modification is authorized or required.

Use an explicitly enabled test session, independent of the quiet Simulation
replay and live camera. Defaults remain test session disabled, audio off and
unassigned hotkeys unless the user separately saved mappings. Actual app-local
speech/sounds use selected app volume after user opt-in. Windows system volume,
mute/choking maximum and computer-wide caregiver muting/restoration stay simulated.
The live diagnostic candidate counter cannot drive suppression or audio.

Preserve original warning deadlines through uncertainty, strict two-second
simulated caregiver confirmation, retained silence until reliable departure,
immediate restoration independent of armed mode, and thirty-second safe rearm.
Only manual Cancel/Resolve resolves choking. Caregiver entry/reply stops repeats
while the incident and popup remain active; departure leaves choking warning audio
silent. Saved audio for other computer output still restores independently. Essential one-pointer controls, capture Stop and app volume remain
visible. Do not restart the user's running monitor or discard unsaved edits.

Optional hotkey saving creates new exclusive revisions in its own runtime
subdirectory; earlier settings/profiles/features/models remain unchanged. Keep
ordinary Desktop and Codex-redirected AppData copies separate; do not merge them.
No real SMS (including test texts), recording, personal collection, watchdog or
startup work. Real messaging/caregiver participation remains deferred to Milestone
6 unless separately approved. Public website, global Python, isolated dependency
pins and OneDrive backup are preserved.

Pre-implementation baseline at 46bbe17 was clean: all 457 synthetic tests and
pip check passed in fresh scratch. Implementation and physical hotkey/audio
verification remain pending. Finish synthetic tests and independent review,
update next handoff/checkpoint, inspect staged privacy, then commit and push.

## Latest October 7 follow-up: scroll protection and selected-mask removal

Tyler approved repairing wheel input intercepted by right-panel option fields,
and explicitly approved a button/tap/confirm individual-mask tool. Active Desktop
inspection verified the prior layout repair is loaded and the picture is clear.
During the scrolling demonstration the requested FPS changed 15 -> 30; Tyler
explicitly chose to keep 30. The agent did not save settings/restart camera,
capture features or remove any real masks. Computer Use was reset before coding.

The new guard redirects wheel/pixel gestures from closed dropdowns and numeric
editors into their containing Camera/Calibration/Simulation scroll panel.
Deliberate popup selection and numeric typing/arrows remain available. Camera
index 0 now has a visible first-camera label. Masks are numbered; Remove Selected
Mask requests a tap and a default-No 60-pixel confirmation before deleting only
that index. Misses/overlaps do not delete anything. Fully overlapping masks cannot
be chosen by this tap tool. Capture/replay and changed-scene/session guards are
rechecked after confirmation. Saving is separate; saved revisions remain intact.

All **457 synthetic tests passed**, including focused controls, inner numeric
editors, pixel-only input, deliberate option changes, earlier/later removal,
cancel/miss/overlap and confirmation changes. New source live behavior remains
pending the next convenient Desktop restart. Preserve unsaved session data.
Independent review found no concrete defect; the seven-file staged privacy and
whitespace checks passed. Public website and dependency pins are unchanged.
Milestone 3 remains unapproved; actual texts, including test SMS, remain deferred
to Milestone 6 unless separately approved earlier.

## October 7 follow-up: dashboard layout repair

Tyler requested correction of live-view obstruction and separately approved
inspection of the current monitor screenshot. The native short/scaled window
showed controls overlapping the picture. Detailed statistics/notes now move
to Camera / Masks, with compact camera state and pose status still visible.
The caregiver evidence counter remains visible above every side tab. Responsive
volume controls retain 60-pixel height and readable captions. Simulation details
scroll independently of current state/countdown and Cancel/Play.
All **433 synthetic tests passed**, including picture/control non-overlap,
requested window bounds, wide-to-small resizing, enlarged text and persistent
essential controls. The isolated dependency check passed; independent review
found no remaining concrete layout regression.
The eight-file staged privacy review and whitespace check passed. Public website,
dependency pins and all private runtime data remain unchanged.

Computer Use was reset after the active inspection before continued coding.
Only synthetic frames were saved for layout QA; no real imagery/features were
saved. The running Desktop monitor retains its existing session and still needs
a user-convenient restart for live verification of the new layout. Do not discard
unsaved data/settings to restart. Milestone 3 remains unapproved.

Tyler requested durable deferral of all real SMS, including test texts, until
Milestone 6 unless separately approved earlier. This is now in AGENTS, the
blueprint's milestone instructions and the next handoff. Milestone 4 remains
simulated until approved supervised messaging checks.

## October 7, 2026: approved simulated Milestone 2 implementation

Tyler approved Milestone 2's simulated source/replay/interface/tests/documentation
in the current conversation. Source is implemented; all 430 synthetic tests and
the isolated dependency check passed. Independent review found no remaining
concrete source defect; the 19-file staged privacy review and staged whitespace
check passed. Earlier references below to
Milestone 2 being unapproved describe the tracking-repair session, not current
authorization. Milestone 3 still requires a separate proposal and source approval.

The independent simulation does not require restored dim lighting, movement,
caregiver participation or new personal data. Current brighter-light tracking
is reported reliable; dim-light recognition and physical acceptance remain
pending. Tests preserve missing-data uncertainty and original incident deadlines.
Before caregiver qualification, missed/ambiguous observations reset the strict
two-second confirmation. After qualification, loss does not prove departure;
uncertainty remains visible. Reliable departure restores simulated saved audio
immediately, with 30 continuous safe seconds required separately for rearming.

Tyler expressly approved that posture recovery cannot cancel manual choking.
Only explicit Cancel/Resolve, a valid caregiver reply or confirmed caregiver
presence stops repeats. The initial manual intent remains possible in every
mode; caregiver silence takes priority. Departure must not revive a suppressed
incident. Existing calibration data, feature schemas, Full-pose selection and
experimental face comparison are unchanged. Model fusion is a later validation
option, not enabled by this milestone.

Next handoff: `NEXT_CHAT_HANDOFF.md`; implementation details and deferred gates:
`fall_detector/docs/MILESTONE_2.md`. All older repair evidence is retained below.

Tyler additionally requested a live diagnostic two-second second-person counter.
It is implemented with candidate/status, observed 0.0-2.0 seconds, reset count and
reason. It requires fresh Full-pose evidence plus explicit Tyler designation,
and resets on missing/ambiguous/stale results, unsupported association, selection
changes, camera pause or scene edits. It does not claim caregiver identity or
connect to alert suppression/audio. Actual Desktop and caregiver checks remain
pending; no caregiver participation or new personal collection occurred.

Updated October 6, 2026. The notation-first checkpoint preceded all new source
edits. Persistent selection implementation is now synthetically verified;
the basic ordinary Desktop selection check is now verified, while a live
new-ID reattachment remains unobserved. Read this first after compaction, then AGENTS.md and the project
Markdown requirements. This checkpoint records authorized work, not a new
milestone approval.

## Authorization and immediate objective

Tyler approved: "Perfect. Go for it. And just in case compaction/context is a
concern, please notate necessary information into an md file" after the proposal
for persistent Tyler selection plus improved head detection. He then explicitly
requested notation first. Write this checkpoint before implementation edits.

Goal: selecting Tyler for calibration must survive a change of temporary P ID
when a short detection gap can be conservatively resolved. The persistent slot
must never treat every candidate as Tyler, silently transfer calibration to a
caregiver, fabricate a missing head, or hide ambiguity. Caregiver presence later
requires a separate real person continuously and reliably tracked for two
seconds; two markers alone are insufficient. No caregiver logic is being enabled
in this repair. Milestone 2 detection/threshold state machine remains unapproved.

## Repository, launch, and preservation

Authoritative repository: C:\Codex Projects\Tyler Safety Monitor
Branch: main; origin: https://github.com/Colonelwheel/tyler-safety-monitor.git
Baseline before this repair: 38ab8e5 (experimental cutoff live notes).
Notation-first checkpoint commit: 442b589. Use git log for the current HEAD.
Tool cwd may still be the old OneDrive project. Use the authoritative path for
all work; escalated shell permission is required outside the listed write roots.
Retain C:\Users\Tyler\OneDrive\Documents\ChatGPT\Falling Video Detection as
an intact backup. Do not reset, clean, delete, or replace either checkout/data.

Ordinary Desktop shortcut: OneDrive\Desktop\Tyler Safety Monitor.lnk ->
local project\fall_detector\Start Monitor.cmd. Use the project's isolated
fall_detector\.venv Python; preserve global Python installations/packages.
Use -B and pytest -p no:cacheprovider with a fresh scratch --basetemp per run.

Ordinary user runtime data: %LOCALAPPDATA%\TylerSafetyMonitor. Codex-launched
processes can be redirected to Codex's MSIX private cache despite identical
logical paths. User-launch verification is essential. Earlier missing-model
issue was resolved by explicitly approved exclusive copies into ordinary AppData;
all originals were retained. Do not repeat model reinstalls/runtime migration.

Preserve all saved profiles, feature replays, settings revisions, and models.
Existing camera access and session dashboard screenshots are authorized, with no
imagery saved. New personalized capture/save requires the app's separate visible
confirmations. No new feature capture is part of this repair. Current user-saved
object masks must remain; do not restore old masks. They may hide caregiver heads,
so review coverage in later supervised validation. Caregiver participation stays
deferred, normally until Milestone 6. No unsafe movements or brighter lighting.

## Verified findings and existing implementation

- 68f21c8 replaced greedy matching with maximum-cardinality/minimum-distance
  association and added explicit uncertainty, stable keyed candidate rows,
  bounded native no-pose diagnostics, and conservative missing-track handling.
- Full pose still genuinely loses the head in tolerable nighttime lighting.
  PersonTracker retains missing IDs for one second; after that a new P ID can
  appear at the same location. This is temporary tracking identity, not a new
  model loaded. Never claim the whole problem is fixed by smoother display.
- 5f62f21 added separate Google BlazeFace Full Range comparison, explicit verified
  model acquisition, capped two samples/second, current magenta estimates, same
  masks/ROI, and no identity decisions or saved experimental measurements.
- 7c7d3fd added experimental 50/80/90 percent score filtering. Scores are detector
  outputs, not match probabilities. Cutoff changes invalidate pending/in-flight
  old results, overlays and recent counters. All 271 synthetic tests passed;
  independent review and staged privacy checks passed. Source committed/pushed.
- Current ordinary Desktop comparison runs at 80 percent. Two unobstructed live
  views showed the estimate on the head at approximately 89/90 percent, without
  the earlier pillow estimate visible. Counters read 3/19, 0/19, and 1/19 missing
  qualifying samples; these were score-only rejections. Full pose had substantial
  native misses. Camera remained approximately 14 FPS, read/reconnect failures
  zero. Third view was occluded; its counters alone do not prove head location.
  These short differently sampled windows do not establish identity accuracy or
  sustained reliability. Main cyan-ID churn is not repaired by this comparison.
- Experimental comparison currently blocks calibration deliberately. Keep that
  isolation: face estimates cannot silently become pose-calibration samples.

## Proposed implementation boundaries (still to implement/review)

Add a session-local persistent monitored-subject slot separate from numeric P
IDs. Explicitly designate a currently visible unambiguous candidate as Tyler.
Keep designation/epoch stable across supported short-gap P-ID reassociation;
only expose a current eligible track when supported by fresh pose observations.
Show missing, confirming, or manual-reselection-required states explicitly.

Conservative diagnostic association policy to review/test: short bounded gap,
small original-frame spatial allowance, multiple fresh observations over time
before a new P ID attaches, unchanged anchor until confirmation. Ambiguity,
competing people during a gap, large jumps, long absence, invalid/stale time or
camera/scene/session reset must prevent automatic attachment. These are tracking
policy parameters, not approved safety thresholds. Position alone cannot prove
biometric identity or rule out every person replacement.

Capture must lock the persistent selection epoch, camera generation, dimensions,
scene and existing model provenance. Changing designation requires a new session
before additional samples can mix. Keep raw feature serialization and existing
profile schema/provenance unchanged. Loaded profiles remain review-only for new
capture and must not seed automatic identity. Never hold old coordinates as
current observations. Existing continuous-safe timing must not be inferred
through gaps; no safety timer is implemented in this repair.

## Work ownership and next steps

Parent owns calibration_ui.py/dashboard integration, integration tests and docs.
head_comparator subagent: read/design first, then subject.py plus unit tests only.
tracking_audit subagent: read-only integration/risk review; no computer use.
Parent told the implementation agent to pause source edits until checkpoint is
written. Resume only after this file exists and the parent confirms it.

1. Finish conservative subject API/design and meaningful synthetic tests.
2. Integrate explicit one-finger designation, persistent status, capture locking,
   and reset/expiry guards. Improve selection without relaxing missing-data rules.
3. Review regressions, run the full isolated suite, review staged public-data
   boundaries, commit and push finished source/docs with sensible messages.
4. Update this checkpoint and NEXT_CHAT_HANDOFF.md with exact verified results,
   unresolved risks and launch instructions. Keep Milestone 2 unapproved.
5. Request one ordinary Desktop restart for fresh live selection verification;
   no calibration capture/head movement required. Use Computer Use only during
   active UI inspection/actions, never coding/research/waits. Preserve camera
   imagery in memory only. If input guard blocks actions, ask minimal manual steps.

## Implementation checkpoint, in progress

The notation-first checkpoint was committed and pushed as 442b589 before source
implementation. Draft source now adds SubjectSlot/SubjectState, explicit Use
Selected Candidate as Tyler, a stable Tyler selector row, current-status display,
selection-epoch capture locks, post-consent eligibility checks, and reset guards.
Full pose observations and saved profile/feature schemas remain unchanged.
Focused dashboard tests passed before the final additional review guard; a full
suite and final review are still pending. No live app restart for this draft yet.

Independent review reproduced an unsafe reassociation case: a previously visible
second person could move into the missing subject's location and inherit the
selection. The subject worker is adding bounded recent-other-person evidence
and tests so such a gap requires manual reselection, including when that second
person gets a new ID. The integration regression must prevent new calibration
proposal points after this sequence. Do not commit source or claim completion
until this guard, full tests, final review and privacy checks pass.


## Latest status: source verification complete, live check pending

SubjectSlot and the UI integration are implemented. The full isolated suite
passed 323 tests. Recent-other-person evidence now prevents the reproduced
caregiver-replacement sequence; both unchanged/new IDs and active-capture point
isolation have regression coverage. Consent source/scene/comparison changes and
loaded-profile isolation are also covered. No personal feature collection or
runtime-data changes occurred during implementation. Source uses the original
Full pose measurement; the face comparison remains diagnostic only.

Final independent review passed with no remaining concrete source defect.
Source/docs are ready for staged privacy review, commit and push. Next request
an ordinary Desktop restart and explicitly select the
visible P candidate with Use Selected Candidate as Tyler. No feature capture or
head movement is needed. Verify the Tyler row remains designated across a
supported P-ID change while missing/ambiguous states remain unavailable. Do not
claim sustained tracking stability from synthetic tests. Update this checkpoint
and handoff with the actual live result and any remaining limitation.


## Current committed state

Persistent selection source/docs committed and pushed as 942873a after all 323
synthetic tests, final independent review and nine-file staged privacy review
passed. The source repair is complete; ordinary Desktop live behavior is not yet
verified. The user has been asked to exit/relaunch the usual Desktop shortcut,
open Calibration / Replay, choose the current P candidate on their head, and
click Use Selected Candidate as Tyler, then reply ready. Do not begin a feature
capture for this check. No Computer Use is needed while waiting/coding.

After ready, inspect only the monitor window to check current designation,
missing/confirming states and supported P-ID change. Do not treat another
person's unobserved real visit as a verified detection result; the competing
person finding above was synthetic. Keep masks/settings/private files intact.


### Ordinary Desktop selection check

The user restarted the usual Desktop shortcut and explicitly designated the
current P candidate as Tyler. The new controls and selected Tyler row were
visible. Three point-in-time checks retained the Tyler designation; the row
showed current P2/head visible on accessibility reads, and the unobstructed
preview also showed the explicit not-reliably-located/unavailable state during
a gap. Subsequent reads returned to current P2 without a new designation.
Camera delivery was approximately 13.4-14.2 FPS with zero read failures,
reconnects or pose submissions skipped. Calibration stayed idle with zero
samples. No capture, setting save, profile save, movement instruction or new
personal feature collection occurred.

No P-number change was observed in these checks. Supported new-ID reattachment
therefore remains verified by synthetic tests, not this live session. The final
screenshot was occluded, so its counters/selector text cannot independently
verify the head position. The basic live selection check confirms the new
interface and visible missing-data behavior; it does not establish continuous
correct head tracking, personal identity or caregiver recognition. Genuine pose
loss and alternative-model validation remain open before operational thresholds.


## Next unresolved verification

Source remains 942873a; checkpoint/handoff documentation has been updated after
the Desktop check. The Tyler row stayed selected through missing/visible states
but the observed current ID remained P2. Do not request a movement to force an
ID change or continuously spend Computer Use while waiting. If natural churn
occurs later, inspect the current selection and whether it confirms the new P
number or correctly requires reselection. A long gap or competing-person
condition requiring reselection is intentional, not proof that every ID should
be accepted. No Milestone 2 approval or new capture is implied by this check.


## Handoff decision and angle-dependent misses

The user reports that ordinary straight-ahead posture flickers more, while the
usual safely lowered posture flickers less. The latter is not perfect tracking;
this corrects the initial informal description. It is a user observation, not
a measured comparison or an isolated diagnosis of lighting/view angle. Do not
ask the user to remain head-down or repeat a movement to suit the detector.
Ordinary comfortable posture and tolerated lighting remain the required target.

Milestone 1 TOOLING is ready for handoff: guided capture, preservation/versioned
profiles, replay, visualization, persistent selection source and 323 synthetic
tests are complete within their approved scope. The basic Desktop selection
check retained the designation through missing/visible states. A live new-ID
reattachment was not observed, and native head-loss/angle sensitivity remains
unresolved. These limits must remain visible, not be smoothed into safe evidence.

It is appropriate to proceed to Milestone 2 SIMULATED state-machine development
after its separate source approval, with uncertainty/gap/fault behavior covered
by deterministic tests and existing measurement provenance preserved. Perfect
per-frame recognition is not a prerequisite to implementing that simulated
logic. This is not approval of operational thresholds, new personal capture,
caregiver audio changes, real messaging or live arming. Actual tracking quality,
longest gaps, caregiver coverage and supervised validation must satisfy the
blueprint's later live-alert acceptance gates. Caregiver participation remains
deferred to the agreed supervised stage. Do not declare safety readiness from
the current visual impression.
