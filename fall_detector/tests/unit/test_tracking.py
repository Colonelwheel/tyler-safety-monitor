import pytest

from tyler_safety_monitor.tracking import PersonTracker, PoseObservation


def observation(x, y=0.7, confidence=0.9):
    return PoseObservation((x, y), (x, min(1, y + 0.1)), confidence)


def test_detector_order_changes_do_not_swap_separate_person_ids():
    tracker = PersonTracker()
    initial = tracker.update([observation(0.2), observation(0.8)], 1)
    moved = tracker.update([observation(0.79), observation(0.21)], 1.1)
    assert [(t.id, t.head[0]) for t in initial] == [(1, 0.2), (2, 0.8)]
    assert [(t.id, t.head[0]) for t in moved] == [(1, 0.21), (2, 0.79)]
    assert all(t.continuous_since == 1 and not t.identity_uncertain for t in moved)
    assert all(t.label == "person candidate" for t in moved)


def test_near_duplicate_does_not_become_second_person_or_continuous_confirmation():
    tracker = PersonTracker()
    tracks = tracker.update([observation(0.4), observation(0.41, confidence=0.7)], 1)
    assert len(tracks) == 1
    assert tracks[0].confidence == 0.9
    assert tracks[0].identity_uncertain
    tracks = tracker.update([observation(0.405)], 2)
    assert tracks[0].continuous_since == 2
    assert not tracks[0].identity_uncertain


def test_missing_frame_breaks_continuity_but_short_reacquisition_retains_id():
    tracker = PersonTracker(ttl_seconds=1)
    first = tracker.update([observation(0.4)], 1)[0]
    assert tracker.update([], 1.2) == []
    returned = tracker.update([observation(0.42)], 1.5)[0]
    assert returned.id == first.id
    assert returned.continuous_since == 1.5
    assert tracker.update([], 2) == []
    expired = tracker.update([observation(0.43)], 3)[0]
    assert expired.id != returned.id


def test_large_jump_is_not_associated_as_same_person():
    tracker = PersonTracker(max_distance=0.1)
    first = tracker.update([observation(0.2)], 1)[0]
    jumped = tracker.update([observation(0.7)], 1.1)[0]
    assert jumped.id != first.id
    assert jumped.continuous_since == 1.1


def test_competing_associations_mark_uncertainty_and_are_one_to_one():
    tracker = PersonTracker(duplicate_distance=0.02, ambiguity_margin=0.04)
    first = tracker.update([observation(0.45), observation(0.55)], 1)
    second = tracker.update([observation(0.485), observation(0.515)], 1.1)
    assert len(second) == 2
    assert {track.id for track in second} == {track.id for track in first}
    assert all(track.identity_uncertain for track in second)
    assert all(track.continuous_since == 1.1 for track in second)


@pytest.mark.parametrize("timestamp", [1, 0.5, float("nan"), float("inf"), -1])
def test_bad_timestamp_does_not_mutate_identity_or_continuity(timestamp):
    tracker = PersonTracker()
    first = tracker.update([observation(0.2)], 1)[0]
    with pytest.raises(ValueError):
        tracker.update([observation(0.8)], timestamp)
    next_track = tracker.update([observation(0.21)], 2)[0]
    assert next_track.id == first.id
    assert next_track.continuous_since == 1


@pytest.mark.parametrize("head,confidence", [((float("nan"), 0.5), 0.8), ((1.1, 0.5), 0.8), ((0.5, 0.5), 2)])
def test_invalid_observation_is_rejected(head, confidence):
    with pytest.raises(ValueError):
        PoseObservation(head, None, confidence)
