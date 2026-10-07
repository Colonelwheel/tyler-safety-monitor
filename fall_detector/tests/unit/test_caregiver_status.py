"""Fresh second-person diagnostic evidence; no camera or operational behavior."""
from dataclasses import replace

import pytest

from tyler_safety_monitor.caregiver_status import CaregiverStatusCounter
from tyler_safety_monitor.tracking import Track


def tracks(t, second=True):
    first = Track(1, (.5, .5), None, .9, t, 0)
    return [first, Track(2, (.8, .3), None, .9, t, 0)] if second else [first]


def test_counter_uses_fresh_observed_time_and_confirms_at_exact_two_seconds():
    counter = CaregiverStatusCounter()
    for i in range(10):
        state = counter.update(tracks(i / 5), 1, i / 5)
        assert state.status == "confirming"
    assert state.elapsed == pytest.approx(1.8)
    assert counter.tick(1.99).elapsed == pytest.approx(1.8)
    state = counter.update(tracks(2), 1, 2)
    assert state.status == "confirmed" and state.elapsed == 2


def test_missing_result_resets_and_reason_remains_visible_on_return():
    counter = CaregiverStatusCounter()
    counter.update(tracks(0), 1, 0)
    counter.update(tracks(.2), 1, .2)
    state = counter.update(tracks(.4, False), 1, .4)
    assert state.elapsed == 0 and state.resets == 1
    assert "No current second" in state.reset_reason
    state = counter.update(tracks(.6), 1, .6)
    assert state.status == "confirming" and state.elapsed == 0
    assert "No current second" in state.reset_reason


@pytest.mark.parametrize("kind", ["empty", "ambiguous", "new_id", "close", "jump", "missing_tyler"])
def test_each_loss_of_supported_continuity_breaks_confirmation(kind):
    counter = CaregiverStatusCounter()
    counter.update(tracks(0), 1, 0)
    current = tracks(.2)
    subject = 1
    if kind == "empty": current = []
    if kind == "ambiguous": current[1] = replace(current[1], identity_uncertain=True)
    if kind == "new_id": current[1] = replace(current[1], id=3)
    if kind == "close": current[1] = replace(current[1], head=(.51, .5))
    if kind == "jump": current[1] = replace(current[1], head=(.9, .8))
    if kind == "missing_tyler": subject = None
    state = counter.update(current, subject, .2)
    assert state.elapsed == 0 and state.resets == 1


def test_stale_counter_cannot_confirm_without_a_new_observation():
    counter = CaregiverStatusCounter()
    counter.update(tracks(0), 1, 0)
    state = counter.tick(2)
    assert state.status == "unavailable" and state.elapsed == 0
    state = counter.update(tracks(2.1), 1, 2.1)
    assert state.status == "confirming" and state.elapsed == 0


def test_sparse_batches_and_scene_reset_cannot_bridge_two_seconds():
    counter = CaregiverStatusCounter()
    counter.update(tracks(0), 1, 0)
    state = counter.update(tracks(2), 1, 2)
    assert state.status == "confirming" and state.elapsed == 0 and state.resets == 1
    counter.reset("Scene changed")
    state = counter.update(tracks(3), 1, 3)
    assert state.elapsed == 0 and state.reset_reason == "Scene changed"


def test_native_model_clock_mapping_can_differ_slightly_from_capture_clock():
    counter = CaregiverStatusCounter()
    current = [replace(track, last_seen=.2005) for track in tracks(.2)]
    assert counter.update(current, 1, .2).status == "confirming"


def test_late_callback_after_ui_refresh_cannot_restore_stale_evidence():
    counter = CaregiverStatusCounter()
    counter.tick(10)
    assert counter.update(tracks(1), 1, 1).status == "unavailable"


def test_duplicate_and_regressing_batches_rejected_without_mutation():
    counter = CaregiverStatusCounter()
    before = counter.update(tracks(1), 1, 1)
    for stamp in (1, .9, float("nan")):
        with pytest.raises(ValueError):
            counter.update(tracks(stamp), 1, stamp)
        assert counter.snapshot == before


def test_confirmed_diagnostic_resets_on_missing_but_never_changes_audio_or_files():
    counter = CaregiverStatusCounter()
    for i in range(11): counter.update(tracks(i / 5), 1, i / 5)
    assert counter.snapshot.status == "confirmed"
    state = counter.update(tracks(2.2, False), 1, 2.2)
    assert state.status == "none" and state.elapsed == 0
