from dataclasses import replace

import pytest

from tyler_safety_monitor.subject import SubjectSlot
from tyler_safety_monitor.tracking import Track


def track(id_=1, x=.5, y=.5, timestamp=0., uncertain=False):
    return Track(id_, (x, y), None, .9, timestamp, timestamp,
                 identity_uncertain=uncertain)


def selected():
    slot = SubjectSlot()
    candidate = track()
    slot.select([candidate], 1, 0.)
    return slot


def test_selection_epoch_is_explicit_and_increases_on_reset_and_reselection():
    slot = SubjectSlot()
    assert not slot.state.selected
    assert slot.state.track_id is None
    assert slot.update([track(timestamp=1)], 1).status == "unselected"
    candidate = track(timestamp=1)
    slot.select([candidate], 1, 1)  # Same timestamp as current update is permitted.
    assert slot.state.selected
    assert slot.state.track_id == 1
    assert slot.state.selection_epoch == 1
    assert slot.eligible([candidate], 1.1) == candidate
    assert slot.reset().selection_epoch == 2
    assert not slot.state.selected
    assert slot.eligible([candidate], 1.1) is None
    slot.select([track(7, timestamp=2)], 7, 2)
    assert slot.state.selection_epoch == 3


@pytest.mark.parametrize("tracks, id_, timestamp", [
    ([], 1, 0),
    ([track(1, uncertain=True)], 1, 0),
    ([track(2)], 1, 0),
    ([track(1), track(2, x=.55)], 1, 0),
    ([track(1, timestamp=.2)], 1, 0),
    ([track(1)], True, 0),
    ([track(1)], 1, float("nan")),
    ([track(1)], 1, -.1),
])
def test_invalid_selection_does_not_mutate_existing_designation(tracks, id_, timestamp):
    slot = selected()
    before = slot.state
    with pytest.raises(ValueError):
        slot.select(tracks, id_, timestamp)
    assert slot.state is before
    assert slot.eligible([track()], .1) == track()


def test_same_bound_id_continues_after_short_missing_gap_and_anchor_updates():
    slot = selected()
    assert slot.update([], .1).status == "missing"
    assert slot.state.selected
    assert slot.state.track_id is None
    assert slot.eligible([], .1) is None
    candidate = track(x=.6, timestamp=.2)
    assert slot.update([candidate], .2).status == "visible"
    assert slot.state.track_id == 1
    assert slot.state.selection_epoch == 1
    assert slot.eligible([candidate], .3) == candidate
    candidate = track(x=.7, timestamp=.3)
    assert slot.update([candidate], .3).status == "visible"


def test_short_gap_new_id_requires_three_fresh_observations_and_half_second():
    slot = selected()
    slot.update([], .1)
    for timestamp in (.2, .45):
        candidate = track(7, x=.52, timestamp=timestamp)
        assert slot.update([candidate], timestamp).status == "confirming"
        assert slot.state.track_id is None
        assert slot.eligible([candidate], timestamp) is None
    candidate = track(7, x=.52, timestamp=.7)
    assert slot.update([candidate], .7).status == "visible"
    assert slot.state.track_id == 7
    assert slot.state.selection_epoch == 1
    assert slot.eligible([candidate], .8) == candidate
    assert candidate.id == 7  # Raw tracking ID is retained.


def test_many_fast_observations_do_not_replace_elapsed_confirmation_time():
    slot = selected()
    for timestamp in (.1, .2, .3, .4, .5):
        assert slot.update([track(2, timestamp=timestamp)], timestamp).status == "confirming"
    assert slot.update([track(2, timestamp=.6)], .6).status == "visible"


def test_missing_confirmation_batch_and_large_consecutive_gap_restart_evidence():
    slot = selected()
    slot.update([track(2, timestamp=.1)], .1)
    slot.update([track(2, timestamp=.35)], .35)
    slot.update([], .8)
    assert slot.update([track(2, timestamp=.9)], .9).status == "confirming"
    assert slot.update([track(2, timestamp=1.15)], 1.15).status == "confirming"
    assert slot.update([track(2, timestamp=1.4)], 1.4).status == "visible"

    slot = selected()
    slot.update([track(2, timestamp=.1)], .1)
    slot.update([track(2, timestamp=.35)], .35)
    assert slot.update([track(2, timestamp=.8)], .8).status == "confirming"
    assert slot.update([track(2, timestamp=1.05)], 1.05).status == "confirming"
    assert slot.update([track(2, timestamp=1.3)], 1.3).status == "visible"


def test_prospective_id_changes_restart_confirmation_without_moving_anchor():
    slot = selected()
    assert slot.update([track(2, x=.55, timestamp=.1)], .1).status == "confirming"
    assert slot.update([track(3, x=.57, timestamp=.35)], .35).status == "confirming"
    # Near the previous prospective point but too far from confirmed .5 anchor.
    assert slot.update([track(3, x=.6, timestamp=.6)], .6).status == "reselection_required"
    assert slot.update([track(2, x=.5, timestamp=.7)], .7).status == "reselection_required"


@pytest.mark.parametrize("id_", [1, 7])
def test_long_gap_latches_even_if_original_id_is_reused(id_):
    slot = selected()
    slot.update([], .1)
    candidate = track(id_, timestamp=3.01)
    assert slot.update([candidate], 3.01).status == "reselection_required"
    assert slot.state.selected
    assert slot.state.track_id is None
    assert slot.eligible([candidate], 3.01) is None
    assert slot.update([track(id_, timestamp=3.1)], 3.1).status == "reselection_required"
    slot.select([track(id_, timestamp=3.1)], id_, 3.1)
    assert slot.state.status == "visible"
    assert slot.state.selection_epoch == 2


@pytest.mark.parametrize("tracks", [
    [track(1, timestamp=.1, uncertain=True)],
    [track(1, timestamp=.1), track(2, x=.55, timestamp=.1)],
    [track(2, timestamp=.1, uncertain=True)],
    [track(2, timestamp=.1), track(3, x=.9, timestamp=.1)],
    [track(2, x=.9, timestamp=.1)],
    [track(1, x=.8, timestamp=.1)],
])
def test_ambiguity_competition_other_person_or_large_jump_latches(tracks):
    slot = selected()
    assert slot.update(tracks, .1).status == "reselection_required"
    assert slot.state.track_id is None
    assert slot.eligible(tracks, .1) is None
    assert slot.update([track(1, timestamp=.2)], .2).status == "reselection_required"


def test_far_person_can_coexist_with_bound_subject_but_blocks_missing_reassociation():
    slot = selected()
    tracks = [track(1, timestamp=.1), track(2, x=.9, timestamp=.1)]
    assert slot.update(tracks, .1).status == "visible"
    assert slot.eligible(tracks, .2) == tracks[0]
    # Only the other person remains; cannot relabel them.
    assert slot.update([track(2, x=.9, timestamp=.2)], .2).status == "reselection_required"
    assert slot.update([track(1, timestamp=.3)], .3).status == "reselection_required"


@pytest.mark.parametrize("timestamp", [0., -.1, float("nan"), float("inf"), True])
def test_invalid_or_duplicate_update_revokes_eligibility_and_preserves_high_water(timestamp):
    slot = selected()
    assert slot.update([track(1)], timestamp).status == "invalid_observation"
    assert slot.state.track_id is None
    assert slot.eligible([track()], .1) is None
    assert slot._last_update == 0.
    current = track(1, timestamp=.1)
    assert slot.update([current], .1).status == "visible"
    assert slot.eligible([current], .1) == current


def test_regression_and_repeated_confirmation_cannot_establish_attachment():
    slot = selected()
    slot.update([track(2, timestamp=.2)], .2)
    slot.update([track(2, timestamp=.45)], .45)
    assert slot.update([track(2, timestamp=.45)], .45).status == "invalid_observation"
    assert slot.update([track(2, timestamp=.4)], .4).status == "invalid_observation"
    assert slot._last_update == .45
    for timestamp in (.7, .95):
        assert slot.update([track(2, timestamp=timestamp)], timestamp).status == "confirming"
    assert slot.update([track(2, timestamp=1.2)], 1.2).status == "visible"


def test_stale_eligibility_is_read_only_and_cannot_use_changed_or_uncertain_tracks():
    slot = selected()
    before = slot.state
    assert slot.eligible([track()], .4) == track()
    assert slot.eligible([track()], .400001) is None
    assert slot.eligible([track()], -.1) is None
    assert slot.eligible([track()], float("nan")) is None
    assert slot.eligible([], .1) is None
    assert slot.eligible([track(2)], .1) is None
    assert slot.eligible([track(1, uncertain=True)], .1) is None
    assert slot.eligible([track(1, x=.51)], .1) is None
    assert slot.eligible([track(1, timestamp=.1)], .1) is None
    assert slot.state is before


def test_stale_or_malformed_candidate_update_cannot_move_confirmed_anchor():
    slot = selected()
    assert slot.update([track(timestamp=0)], .1).status == "invalid_observation"
    assert slot.state.track_id is None
    assert slot.update([replace(track(timestamp=.2), head=(float("nan"), .5))], .2).status == "invalid_observation"
    assert slot._anchor == (.5, .5)
    assert slot.update([track(timestamp=.3)], .3).status == "visible"


def test_missing_time_expiry_eligible_read_does_not_advance_observation_high_water():
    slot = selected()
    assert slot.eligible([track()], 10) is None
    assert slot._last_update == 0
    # Actual next observation then latches the long gap.
    assert slot.update([track(timestamp=10)], 10).status == "reselection_required"


def test_reset_prevents_old_slot_recovery_and_selection_requires_fresh_timestamp():
    slot = selected()
    slot.update([track(2, timestamp=.1)], .1)
    slot.reset()
    assert slot.update([track(2, timestamp=.6)], .6).status == "unselected"
    with pytest.raises(ValueError):
        slot.select([track(2, timestamp=.1)], 2, .1)
    assert not slot.state.selected
    assert slot.state.selection_epoch == 2


def test_brief_missing_batches_preserve_evidence_without_qualifying_missing_head():
    slot = selected()
    assert slot.update([track(2, timestamp=.1)], .1).status == "confirming"
    assert slot.update([], .2).status == "missing"
    assert slot.eligible([], .2) is None
    assert slot.state.track_id is None
    assert slot.update([track(2, timestamp=.35)], .35).status == "confirming"
    assert slot.update([], .45).status == "missing"
    candidate = track(2, timestamp=.6)
    assert slot.update([candidate], .6).status == "visible"
    assert slot.eligible([candidate], .6) == candidate


def test_giant_integer_policy_is_rejected_as_value_error():
    with pytest.raises(ValueError):
        SubjectSlot(max_gap=10 ** 1000)


@pytest.mark.parametrize("replacement_id", [2, 9])
def test_recent_second_person_prevents_replacement_at_subject_anchor(replacement_id):
    slot = selected()
    assert slot.update([track(1, timestamp=.1), track(2, x=.9, timestamp=.1)], .1).status == "visible"
    assert slot.update([], .2).status == "reselection_required"
    for timestamp in (.3, .55, .8):
        candidate = track(replacement_id, x=.52, timestamp=timestamp)
        assert slot.update([candidate], timestamp).status == "reselection_required"
        assert slot.eligible([candidate], timestamp) is None
    assert slot.state.selection_epoch == 1


def test_recent_second_person_prevents_direct_id_replacement_without_empty_batch():
    slot = selected()
    slot.update([track(1, timestamp=.1), track(2, x=.9, timestamp=.1)], .1)
    assert slot.update([track(9, x=.52, timestamp=.2)], .2).status == "reselection_required"


def test_recent_second_person_prevents_same_id_return_after_unsupported_observation_gap():
    slot = selected()
    slot.update([track(1, timestamp=.1), track(2, x=.9, timestamp=.1)], .1)
    candidate = track(1, x=.52, timestamp=.6)
    assert slot.update([candidate], .6).status == "reselection_required"
    assert slot.eligible([candidate], .6) is None


def test_recent_other_evidence_expires_after_continuous_clear_subject_observations():
    slot = selected()
    slot.update([track(1, timestamp=.1), track(2, x=.9, timestamp=.1)], .1)
    for timestamp in (.3, .6, .9, 1.2, 1.5, 1.8, 2.1, 2.4, 2.7, 3., 3.2):
        assert slot.update([track(1, timestamp=timestamp)], timestamp).status == "visible"
    assert slot.update([], 3.3).status == "missing"
    for timestamp in (3.4, 3.65):
        assert slot.update([track(9, x=.52, timestamp=timestamp)], timestamp).status == "confirming"
    candidate = track(9, x=.52, timestamp=3.9)
    assert slot.update([candidate], 3.9).status == "visible"
    assert slot.eligible([candidate], 3.9) == candidate


def test_explicit_selection_records_current_other_and_clears_old_other_history():
    slot = SubjectSlot()
    slot.select([track(1), track(2, x=.9)], 1, 0)
    assert slot.update([], .1).status == "reselection_required"
    # Explicit selection with the subject alone starts a new designation/history.
    slot.select([track(1, timestamp=.2)], 1, .2)
    assert slot.update([], .3).status == "missing"
    for timestamp in (.4, .65):
        assert slot.update([track(9, x=.52, timestamp=timestamp)], timestamp).status == "confirming"
    assert slot.update([track(9, x=.52, timestamp=.9)], .9).status == "visible"
    assert slot.state.selection_epoch == 2


def test_reset_discards_recent_other_history_without_restoring_old_designation():
    slot = SubjectSlot()
    slot.select([track(1), track(2, x=.9)], 1, 0)
    slot.reset()
    slot.select([track(1, timestamp=.1)], 1, .1)
    assert slot.update([], .2).status == "missing"
    for timestamp in (.3, .55):
        assert slot.update([track(9, x=.52, timestamp=timestamp)], timestamp).status == "confirming"
    assert slot.update([track(9, x=.52, timestamp=.8)], .8).status == "visible"
    assert slot.state.selection_epoch == 3
