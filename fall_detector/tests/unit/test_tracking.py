import pytest

from tyler_safety_monitor.tracking import PersonTracker, PoseObservation, Track


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


def test_optional_landmark_scores_preserve_legacy_positional_construction():
    landmarks = ((.2, .7, 0),)
    legacy_observation = PoseObservation((.2, .7), None, .9, landmarks)
    legacy_track = Track(1, (.2, .7), None, .9, 1, 1, landmarks, "custom label", True)
    assert legacy_observation.landmark_scores == ()
    assert legacy_track.landmark_scores == ()
    assert legacy_track.label == "custom label"
    assert legacy_track.identity_uncertain


def test_tracker_retains_invisible_landmark_scores_and_updates_them():
    tracker = PersonTracker()
    landmarks = ((.2, .7, 0), (.2, .8, 0))
    first = PoseObservation((.2, .7), None, .9, landmarks, ((.9, .8), (0, .1)))
    tracked = tracker.update([first], 1)[0]
    assert tracked.landmarks == landmarks
    assert tracked.landmark_scores == first.landmark_scores
    second = PoseObservation((.2, .7), None, .9, landmarks, ((.8, .7), (.1, .2)))
    updated = tracker.update([second], 2)[0]
    assert updated.id == tracked.id
    assert updated.landmark_scores == second.landmark_scores


@pytest.mark.parametrize("scores", [
    ((.9,),), ((.9, .8, .7),), ((float("nan"), .8),),
    ((float("inf"), .8),), ((-.1, .8),), ((.9, 1.1),),
    ((.9, .8), (.7, .6)),
])
def test_malformed_landmark_score_metadata_is_rejected(scores):
    landmarks = ((.2, .7, 0),)
    with pytest.raises(ValueError):
        PoseObservation((.2, .7), None, .9, landmarks, scores)
    with pytest.raises(ValueError):
        Track(1, (.2, .7), None, .9, 1, 1, landmarks, landmark_scores=scores)


def test_scores_cannot_exist_without_landmarks():
    with pytest.raises(ValueError):
        PoseObservation((.2, .7), None, .9, landmark_scores=((.9, .9),))


def test_diagnostics_distinguish_duplicate_heads_and_missing_results():
    tracker = PersonTracker()
    tracks = tracker.update([observation(.4), observation(.41)], 1)
    d = tracker.diagnostics
    assert (d.received, d.kept, d.suppressed) == (2, 1, 1)
    assert (d.duplicate_uncertain, d.ambiguous_matches) == (1, 0)
    assert tracks[0].identity_uncertain
    tracker.update([], 1.1)
    d = tracker.diagnostics
    assert (d.frames, d.missing_frames, d.duplicate_frames) == (2, 1, 1)
    assert 'no head 1' in d.summary()
    tracker.update([observation(.4)], 12)
    d = tracker.diagnostics
    assert (d.frames, d.missing_frames, d.duplicate_frames) == (1, 0, 0)


def test_diagnostics_count_competing_matches_without_suppressed_duplicates():
    tracker = PersonTracker(duplicate_distance=.02, ambiguity_margin=.04)
    tracker.update([observation(.45), observation(.55)], 1)
    tracker.update([observation(.485), observation(.515)], 1.1)
    d = tracker.diagnostics
    assert d.suppressed == 0 and d.duplicate_uncertain == 0
    assert d.ambiguous_matches == 2 and d.ambiguous_frames == 1
    assert d.uncertain_frames == 1
    before = tracker.diagnostics
    with pytest.raises(ValueError):
        tracker.update([], 1.1)
    assert tracker.diagnostics == before


@pytest.mark.parametrize("reverse", [False, True])
def test_global_assignment_keeps_both_ids_when_greedy_would_strand_one(reverse):
    tracker = PersonTracker()
    first = tracker.update([observation(.4), observation(.5)], 1)
    moved = [observation(.47), observation(.58)]
    if reverse:
        moved.reverse()
    second = tracker.update(moved, 1.1)
    assert [(t.id, t.head[0]) for t in second] == [(first[0].id, .47), (first[1].id, .58)]
    assert all(t.continuous_since == 1 for t in second)


def test_duplicate_and_competing_match_reasons_remain_explicit():
    tracker = PersonTracker()
    duplicate = tracker.update([observation(.4), observation(.41)], 1)[0]
    assert duplicate.uncertainty_reasons == ("duplicate heads",)
    tracker = PersonTracker(duplicate_distance=.02, ambiguity_margin=.04)
    tracker.update([observation(.45), observation(.55)], 1)
    crossing = tracker.update([observation(.485), observation(.515)], 1.1)
    assert all(t.identity_uncertain for t in crossing)
    assert all(t.uncertainty_reasons == ("competing matches",) for t in crossing)


def test_global_matching_reaches_minimum_distance_at_maximum_cardinality():
    # Independent exhaustive oracle for small synthetic association graphs.
    import itertools
    import random
    from math import hypot
    from tyler_safety_monitor.tracking import _assign_heads
    randomizer = random.Random(1234)
    for count in range(1, 5):
        old = {i + 1: Track(i + 1, (randomizer.random(), .5), None, .9, 1, 1)
               for i in range(count)}
        for _ in range(10):
            new = [observation(randomizer.random(), y=.5) for _ in range(count)]
            limit = .15
            candidates = []
            for choices in itertools.product([None, *old], repeat=count):
                ids = [id_ for id_ in choices if id_ is not None]
                if len(ids) != len(set(ids)):
                    continue
                distances = [hypot(new[i].head[0] - old[id_].head[0],
                                   new[i].head[1] - old[id_].head[1])
                             for i, id_ in enumerate(choices) if id_ is not None]
                if any(d > limit for d in distances):
                    continue
                candidates.append((-len(ids), sum(distances)))
            expected = min(candidates)
            matches = _assign_heads(old, new, limit)
            actual = (-len(matches), sum(hypot(new[i].head[0] - old[id_].head[0],
                                               new[i].head[1] - old[id_].head[1])
                                        for i, id_ in matches.items()))
            assert actual[0] == expected[0]
            assert actual[1] == pytest.approx(expected[1])


def test_large_finite_match_distance_does_not_overflow_new_id_costs():
    tracker = PersonTracker(max_distance=1e308)
    first = tracker.update([observation(.4)], 1)[0]
    second = tracker.update([observation(.42), observation(.8)], 1.1)
    assert len(second) == 2
    assert second[0].id == first.id
    assert second[1].id != first.id
