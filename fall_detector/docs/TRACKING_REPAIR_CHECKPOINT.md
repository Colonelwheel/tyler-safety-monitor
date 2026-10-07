# Tracking repair checkpoint

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
