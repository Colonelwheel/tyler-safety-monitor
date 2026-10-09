"""Scenario contracts for pure simulation; no physical recognition claims."""
from dataclasses import replace

import pytest

from tyler_safety_monitor.simulation_state import Config, Effect, Engine, Evidence, Incident, Mode, Snapshot


def safe(timestamp, **changes):
    return Evidence(timestamp, "safe", True, True, calibrated=True, **changes)


def posture(timestamp, value, **changes):
    return Evidence(timestamp, value, True, calibrated=True, **changes)


def armed():
    engine = Engine()
    assert engine.observe(safe(0)).mode == Mode.ARMED
    return engine


def qualify_caregiver(engine, began=0, **changes):
    for step in range(11):
        engine.observe(safe(began + step / 5, caregiver_id=2,
                            caregiver_valid=True, **changes))
    assert engine.snapshot.audio_priority == "caregiver_silent"


def kinds(engine):
    return [effect.kind for effect in engine.effects]


def sends(engine):
    return [effect for effect in engine.effects if effect.kind.startswith("would_send_")]


def test_lean_deadlines_and_missing_observations_do_not_restart_grace():
    engine = armed()
    engine.observe(posture(1, "lean"))
    assert engine.snapshot.incident == Incident.LEAN_GRACE
    assert engine.snapshot.remaining == 30
    engine.observe(Evidence(20, calibrated=True))
    assert engine.snapshot.uncertain
    assert engine.snapshot.remaining == 11
    engine.tick(30.999)
    assert engine.snapshot.incident == Incident.LEAN_GRACE
    assert engine.tick(31).incident == Incident.NORMAL_WARNING
    assert engine.snapshot.remaining == 10
    engine.observe(Evidence(35, calibrated=True))
    assert engine.snapshot.remaining == 6
    assert engine.tick(41).incident == Incident.ALERT_ACTIVE
    assert [(effect.timestamp, effect.kind) for effect in sends(engine)] == [(41, "would_send_fall")]


def test_unknown_at_grace_expiry_is_unresolved_warning_not_safe_recovery():
    engine = armed()
    engine.observe(posture(.1, "lean"))
    result = engine.observe(Evidence(30.1, calibrated=True))
    assert result.incident == Incident.NORMAL_WARNING
    assert result.uncertain
    assert not sends(engine)


def test_late_tick_dispatches_original_deadlines_without_catchup_sms_burst():
    engine = armed()
    engine.observe(posture(1, "lean"))
    engine.tick(900)
    assert [(effect.timestamp, effect.kind) for effect in engine.effects] == [
        (31, "normal_warning"), (41, "would_send_fall")]
    assert engine.snapshot.message_count == 1
    engine.tick(900)
    assert engine.snapshot.message_count == 1
    engine.tick(960)
    assert engine.snapshot.message_count == 2


@pytest.mark.parametrize("recovery_time", [2, 5, 8])
def test_slow_recovery_requires_positive_stable_safe_confirmation(recovery_time):
    engine = armed()
    engine.observe(posture(1, "severe"))
    engine.observe(posture(recovery_time, "safe"))
    assert engine.snapshot.incident == Incident.SEVERE_WARNING
    engine.observe(safe(recovery_time + .1, recovery_confirmed=True))
    assert engine.snapshot.incident == Incident.RESOLVED
    engine.tick(10)
    assert not sends(engine)


def test_exact_deadline_recovery_wins_but_late_recovery_does_not_erase_dispatch():
    exact = armed()
    exact.observe(posture(1, "severe"))
    assert exact.observe(safe(9, recovery_confirmed=True)).incident == Incident.RESOLVED
    assert not sends(exact)
    late = armed()
    late.observe(posture(1, "severe"))
    assert late.observe(safe(10, recovery_confirmed=True)).incident == Incident.RESOLVED
    assert [(effect.timestamp, effect.kind) for effect in sends(late)] == [(9, "would_send_fall")]


def test_exact_deadline_cancel_wins_late_cancel_preserves_prior_effect():
    exact = Engine()
    exact.command("fall", 0)
    exact.command("cancel", 8)
    assert not sends(exact)
    late = Engine()
    late.command("fall", 0)
    late.command("cancel", 9)
    assert sends(late)[0].timestamp == 8
    assert late.snapshot.incident == Incident.RESOLVED


def test_severe_escalation_never_extends_normal_or_restarts_severe_warning():
    engine = armed()
    engine.observe(posture(1, "lean"))
    engine.tick(31)
    engine.observe(posture(39, "severe"))
    assert engine.snapshot.incident == Incident.SEVERE_WARNING
    assert engine.snapshot.remaining == 2
    engine.observe(posture(40, "severe"))
    assert engine.snapshot.remaining == 1
    assert engine.tick(41).incident == Incident.ALERT_ACTIVE
    early = armed()
    early.observe(posture(1, "lean"))
    early.observe(posture(3, "severe"))
    assert early.snapshot.remaining == 8
    assert early.tick(11).incident == Incident.ALERT_ACTIVE


def test_severe_during_late_grace_receives_eight_seconds_without_delaying_alert():
    engine = armed()
    engine.observe(posture(1, "lean"))
    engine.observe(posture(27, "severe"))
    assert engine.snapshot.remaining == 8
    assert engine.tick(34.999).incident == Incident.SEVERE_WARNING
    engine.tick(35)
    assert sends(engine)[0].timestamp == 35
    during_normal = armed()
    during_normal.observe(posture(1, "lean"))
    during_normal.observe(posture(35, "severe"))
    assert during_normal.snapshot.remaining == 6
    during_normal.tick(41)
    assert sends(during_normal)[0].timestamp == 41


def test_caregiver_requires_two_fresh_separate_tracks_not_sparse_ids():
    engine = armed()
    engine.observe(safe(.1, caregiver_id=2, caregiver_valid=True))
    engine.observe(safe(2.1, caregiver_id=2, caregiver_valid=True))
    assert engine.snapshot.mode == Mode.ARMED
    engine.observe(Evidence(2.2, caregiver_id=2, caregiver_valid=True))
    assert engine.snapshot.audio_priority != "caregiver_silent"
    for step in range(11):
        engine.observe(safe(3 + step / 5, caregiver_id=2, caregiver_valid=True))
    assert engine.snapshot.mode == Mode.CAREGIVER_PRESENT


@pytest.mark.parametrize("break_kind", ["missing", "changed_id", "invalid_candidate", "tick_gap"])
def test_caregiver_qualification_continuity_restarts_only_its_own_timer(break_kind):
    engine = armed()
    for step in range(9):
        engine.observe(safe(.1 + step / 5, caregiver_id=2, caregiver_valid=True))
    if break_kind == "missing":
        engine.observe(safe(1.9))
    elif break_kind == "changed_id":
        engine.observe(safe(1.9, caregiver_id=3, caregiver_valid=True))
    elif break_kind == "invalid_candidate":
        engine.observe(safe(1.9, caregiver_id=2, caregiver_valid=False))
    else:
        engine.tick(2.2)
    engine.observe(safe(2.3, caregiver_id=2, caregiver_valid=True))
    assert engine.snapshot.mode != Mode.CAREGIVER_PRESENT
    assert "would_silence_audio" not in kinds(engine)


def test_qualified_caregiver_locks_silence_through_missing_observations():
    engine = Engine()
    engine.command("fall", 0)
    qualify_caregiver(engine, began=.1)
    engine.observe(Evidence(3, calibrated=True))
    engine.tick(100)
    assert engine.snapshot.mode == Mode.CAREGIVER_PRESENT
    assert engine.snapshot.audio_priority == "caregiver_silent"
    assert engine.snapshot.uncertain
    assert not sends(engine)
    assert kinds(engine).count("would_silence_audio") == 1


def test_caregiver_qualification_at_deadline_wins_without_safe_recovery():
    engine = Engine()
    engine.command("fall", 0)
    for step in range(11):
        engine.observe(posture(6 + step / 5, "lean", caregiver_id=2,
                               caregiver_valid=True))
    assert engine.snapshot.incident == Incident.RESOLVED
    assert not sends(engine)


@pytest.mark.parametrize("mode", ["night", "fault", "away", "ready"])
def test_departure_restores_simulated_audio_independent_of_monitoring(mode):
    engine = Engine()
    qualify_caregiver(engine)
    if mode == "night":
        engine.command("night", 2)
    engine.observe(Evidence(3, caregiver_departed=True, fault=mode == "fault",
                            paired_exit=mode == "away", calibrated=True))
    assert engine.snapshot.audio_priority == "idle"
    assert kinds(engine).count("would_restore_audio") == 1
    assert engine.snapshot.mode == {"night": Mode.NIGHT, "fault": Mode.FAULT,
                                   "away": Mode.AWAY, "ready": Mode.READY}[mode]


def test_caregiver_departure_requires_30_continuous_confirmed_safe_seconds_to_rearm():
    engine = Engine()
    qualify_caregiver(engine)
    engine.observe(safe(3, caregiver_departed=True))
    for step in range(1, 150):
        engine.observe(safe(3 + step / 5))
    assert engine.snapshot.mode == Mode.READY
    assert engine.observe(safe(33)).mode == Mode.ARMED


def test_missing_or_unknown_rearm_data_breaks_continuous_safe_period():
    engine = Engine()
    qualify_caregiver(engine)
    engine.observe(safe(3, caregiver_departed=True))
    for step in range(1, 100):
        engine.observe(safe(3 + step / 5))
    engine.observe(Evidence(23, calibrated=True))
    for step in range(150):
        engine.observe(safe(24 + step / 5))
    assert engine.snapshot.mode == Mode.READY
    assert engine.observe(safe(54)).mode == Mode.ARMED


def test_away_requires_previously_confirmed_caregiver_and_asserted_joint_exit():
    alone = armed()
    alone.observe(Evidence(1, paired_exit=True, calibrated=True))
    assert alone.snapshot.mode != Mode.AWAY
    with_caregiver = Engine()
    qualify_caregiver(with_caregiver)
    with_caregiver.observe(Evidence(3, paired_exit=True, calibrated=True))
    assert with_caregiver.snapshot.mode == Mode.AWAY
    with_caregiver.observe(safe(4, caregiver_id=2, caregiver_valid=True))
    assert with_caregiver.snapshot.mode == Mode.CAREGIVER_PRESENT


def test_night_does_not_resolve_incident_and_manual_triggers_remain_available():
    engine = armed()
    engine.observe(posture(1, "lean"))
    engine.command("night", 2)
    assert engine.snapshot.mode == Mode.NIGHT
    assert engine.snapshot.incident == Incident.LEAN_GRACE
    engine.tick(41)
    assert sends(engine)[0].kind == "would_send_fall"
    engine.command("choking", 42)
    assert sends(engine)[-1].kind == "would_send_choking"
    assert engine.snapshot.audio_priority == "choking_maximum_simulated"
    engine.command("resolve", 43)
    assert engine.snapshot.mode == Mode.NIGHT
    assert engine.snapshot.audio_priority == "idle"


def test_choking_is_immediate_silent_with_caregiver_and_idempotent_when_repeated():
    engine = Engine()
    qualify_caregiver(engine)
    engine.command("choking", 3)
    engine.command("choking", 3)
    assert [(effect.timestamp, effect.kind) for effect in sends(engine)] == [(3, "would_send_choking")]
    assert engine.snapshot.audio_priority == "caregiver_silent"
    engine.tick(1000)
    assert engine.snapshot.message_count == 1
    engine.command("reply", 1000)
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.choking
    engine.command("cancel", 1001)
    assert engine.snapshot.incident == Incident.RESOLVED
    assert not engine.snapshot.choking


def test_upright_stable_posture_and_positive_visual_recovery_do_not_resolve_choking():
    engine = armed()
    engine.command("choking", 1)
    engine.observe(safe(2))
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.audio_priority == "choking_maximum_simulated"
    engine.observe(safe(3, recovery_confirmed=True))
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    engine.tick(61)
    assert engine.snapshot.message_count == 2
    engine.command("resolve", 62)
    assert engine.snapshot.incident == Incident.RESOLVED


def test_newly_confirmed_caregiver_keeps_choking_active_and_stops_repeats():
    engine = Engine()
    engine.command("choking", 0)
    qualify_caregiver(engine, began=1)
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.choking
    assert engine.snapshot.audio_priority == "caregiver_silent"
    engine.tick(1000)
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.message_count == 1


def test_manual_fall_with_retained_caregiver_is_handled_without_warning_or_message():
    engine = Engine()
    qualify_caregiver(engine)
    engine.command("fall", 3)
    assert engine.snapshot.incident == Incident.RESOLVED
    engine.observe(safe(4, caregiver_departed=True))
    engine.tick(1000)
    assert not sends(engine)
    assert any(effect.kind == "manual_fall_handled_by_caregiver" for effect in engine.effects)


def test_visible_subject_does_not_hide_missing_caregiver_evidence_after_confirmation():
    engine = Engine()
    qualify_caregiver(engine)
    assert engine.snapshot.caregiver_current
    engine.observe(safe(3))
    assert engine.snapshot.caregiver
    assert not engine.snapshot.caregiver_current
    assert engine.snapshot.uncertain
    assert engine.snapshot.audio_priority == "caregiver_silent"
    engine.observe(safe(4, caregiver_departed=True))
    assert not engine.snapshot.caregiver
    assert not engine.snapshot.uncertain


def test_choking_with_existing_caregiver_repeats_do_not_resume_after_departure():
    engine = Engine()
    qualify_caregiver(engine)
    engine.command("choking", 3)
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.choking
    assert engine.snapshot.audio_priority == "caregiver_silent"
    engine.observe(safe(4, caregiver_departed=True))
    assert engine.snapshot.audio_priority == "choking_silent_simulated"
    assert engine.snapshot.choking and engine.snapshot.choking_silent
    assert kinds(engine).count("would_restore_audio") == 1
    engine.tick(63)
    assert engine.snapshot.message_count == 1
    assert [(effect.timestamp, effect.kind) for effect in sends(engine)] == [(3, "would_send_choking")]


@pytest.mark.parametrize("action", ["cancel", "resolve"])
def test_explicit_choking_resolution_restores_simulated_audio(action):
    engine = Engine()
    engine.command("choking", 0)
    engine.command(action, 1)
    assert kinds(engine).count("would_restore_audio") == 1
    assert engine.snapshot.audio_priority == "idle"
    engine.command(action, 1)
    assert kinds(engine).count("would_restore_audio") == 1


def test_caregiver_choking_resolution_never_restores_audio_over_silence_lock():
    engine = Engine()
    engine.command("choking", 0)
    qualify_caregiver(engine, began=1)
    engine.command("resolve", 4)
    assert "would_restore_audio" not in kinds(engine)
    assert engine.snapshot.audio_priority == "caregiver_silent"


def test_night_does_not_hide_fault_or_retained_caregiver_audio_lock():
    engine = Engine()
    qualify_caregiver(engine)
    engine.command("night", 2)
    engine.observe(safe(3, fault=True))
    state = engine.snapshot
    assert state.mode == Mode.NIGHT
    assert state.night and state.fault and state.caregiver and state.uncertain
    assert state.audio_priority == "caregiver_silent"


def test_fault_alone_sends_nothing_and_existing_warning_survives_fault():
    empty = Engine()
    empty.observe(Evidence(0, fault=True))
    assert empty.snapshot.mode == Mode.FAULT
    empty.tick(1000)
    assert not sends(empty)
    warning = armed()
    warning.observe(posture(1, "severe"))
    warning.observe(Evidence(2, fault=True, calibrated=True))
    assert warning.snapshot.mode == Mode.FAULT
    warning.tick(9)
    assert sends(warning)[0].timestamp == 9


def test_uncalibrated_input_never_arms_or_creates_automatic_incident():
    engine = Engine()
    engine.command("start", 0)
    engine.observe(Evidence(0, "severe", True, calibrated=False))
    assert engine.snapshot.mode == Mode.READY
    assert engine.snapshot.incident == Incident.NONE
    engine.observe(safe(1))
    assert engine.snapshot.mode == Mode.ARMED
    engine.observe(Evidence(2, "severe", True, calibrated=False))
    assert engine.snapshot.mode == Mode.READY
    assert not sends(engine)


def test_repeat_timing_cap_and_resolution_stop_future_simulated_intents():
    engine = Engine()
    engine.command("choking", 0)
    engine.tick(59.999)
    assert engine.snapshot.message_count == 1
    for index in range(1, 10):
        engine.tick(index * 60)
    assert engine.snapshot.message_count == 10
    engine.tick(10000)
    assert engine.snapshot.message_count == 10
    early = Engine()
    early.command("choking", 0)
    early.command("reply", 30)
    early.tick(10000)
    assert early.snapshot.message_count == 1


def test_bounded_effect_history_and_immutable_snapshots():
    engine = Engine(Config(max_effects=3))
    first = engine.command("fall", 0)
    for index in range(5):
        engine.command("cancel", index * 2 + 1)
        engine.command("fall", index * 2 + 2)
    assert len(engine.effects) == 3
    assert first.incident == Incident.SEVERE_WARNING
    assert first.effects == ()


@pytest.mark.parametrize("value", [-1, float("nan"), float("inf"), True, "1", 10**1000])
def test_invalid_source_times_rejected(value):
    with pytest.raises(ValueError):
        Evidence(value)
    with pytest.raises(ValueError):
        Engine().tick(value)


def test_timestamp_regression_and_duplicate_observation_are_atomic():
    engine = armed()
    engine.observe(posture(1, "lean"))
    before = engine.snapshot
    with pytest.raises(ValueError):
        engine.observe(posture(1, "severe"))
    with pytest.raises(ValueError):
        engine.command("night", .5)
    assert engine.snapshot == before
    assert engine.tick(1).remaining == 30
    assert engine.command("fall", 1).remaining == 8


@pytest.mark.parametrize("changes", [dict(posture=[]), dict(subject_valid=1),
    dict(caregiver_id=True), dict(caregiver_valid=True),
    dict(caregiver_id=2, caregiver_valid=True, caregiver_departed=True),
    dict(subject_valid=True, paired_exit=True)])
def test_contradictory_or_invalid_evidence_is_rejected(changes):
    with pytest.raises(ValueError):
        replace(Evidence(0), **changes)


@pytest.mark.parametrize("changes", [dict(lean_grace=0), dict(max_gap=-1),
    dict(repeat=float("nan")), dict(max_messages=True), dict(max_effects=0),
    dict(max_messages=11), dict(max_effects=4097)])
def test_config_rejects_invalid_policy(changes):
    with pytest.raises(ValueError):
        Config(**changes)


@pytest.mark.parametrize("action", ["cancel", "resolve"])
def test_choking_reply_stops_repeats_durably_without_resolution(action):
    engine = Engine()
    engine.command("choking", 0)
    engine.command("reply", 1)
    assert engine.snapshot.choking
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.audio_priority == "choking_maximum_simulated"
    assert "would_restore_audio" not in kinds(engine)
    engine.observe(safe(2, recovery_confirmed=True))
    engine.command("night", 3)
    engine.command("start", 4)
    engine.command("choking", 5)  # Active incident cannot restart its stopped repeats.
    engine.tick(1000)
    assert engine.snapshot.message_count == 1
    assert engine.snapshot.choking
    assert kinds(engine).count("choking_repeats_stopped") == 1
    engine.command(action, 1001)
    assert not engine.snapshot.choking
    assert engine.snapshot.incident == Incident.RESOLVED
    assert kinds(engine).count("would_restore_audio") == 1


def test_choking_paired_exit_and_manual_fall_cannot_resolve_or_restart_repeats():
    engine = Engine()
    engine.command("choking", 0)
    qualify_caregiver(engine, began=1)
    engine.command("fall", 4)
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.choking and engine.snapshot.caregiver
    assert "manual_fall_handled_by_caregiver" not in kinds(engine)
    engine.observe(Evidence(5, paired_exit=True, caregiver_departed=True))
    assert engine.snapshot.mode == Mode.AWAY
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.choking and engine.snapshot.choking_silent
    assert engine.snapshot.audio_priority == "choking_silent_simulated"
    engine.tick(1000)
    assert engine.snapshot.message_count == 1
    assert "incident_resolved" not in kinds(engine)
    engine.command("resolve", 1001)
    assert not engine.snapshot.choking


@pytest.mark.parametrize("mode", ["night", "fault", "away", "ready"])
def test_choking_departure_restores_audio_independent_of_mode_without_resuming_repeats(mode):
    engine = Engine()
    engine.command("choking", 0)
    qualify_caregiver(engine, began=1)
    engine.observe(Evidence(4))  # Missing people retain silence and choking kind.
    assert engine.snapshot.choking and engine.snapshot.caregiver
    assert engine.snapshot.choking_silent
    assert engine.snapshot.audio_priority == "caregiver_silent"
    if mode == "night":
        engine.command("night", 4)
    engine.observe(Evidence(5, caregiver_departed=True, fault=mode == "fault",
                            paired_exit=mode == "away"))
    assert not engine.snapshot.caregiver
    assert engine.snapshot.choking
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.snapshot.choking_silent
    assert engine.snapshot.audio_priority == "choking_silent_simulated"
    assert kinds(engine).count("would_restore_audio") == 1
    assert engine.snapshot.mode == {"night": Mode.NIGHT, "fault": Mode.FAULT,
                                   "away": Mode.AWAY, "ready": Mode.READY}[mode]
    engine.tick(1000)
    assert engine.snapshot.message_count == 1


def test_reply_still_resolves_fall_and_cannot_mark_it_as_choking():
    engine = Engine()
    engine.command("fall", 0)
    assert not engine.snapshot.choking
    engine.command("reply", 1)
    assert engine.snapshot.incident == Incident.RESOLVED
    assert not engine.snapshot.choking
    engine.tick(1000)
    assert not sends(engine)


@pytest.mark.parametrize("action", ["cancel", "resolve"])
def test_manual_resolution_clears_choking_silence_and_new_incident_can_sound(action):
    engine = Engine()
    engine.command("choking", 0)
    assert not engine.snapshot.choking_silent
    qualify_caregiver(engine, began=1)
    assert engine.snapshot.choking_silent
    engine.observe(Evidence(4))
    assert engine.snapshot.choking_silent and engine.snapshot.caregiver
    engine.observe(Evidence(5, caregiver_departed=True))
    assert engine.snapshot.audio_priority == "choking_silent_simulated"
    assert kinds(engine).count("would_restore_audio") == 1
    engine.command(action, 6)
    assert not engine.snapshot.choking and not engine.snapshot.choking_silent
    assert engine.snapshot.audio_priority == "idle"
    assert kinds(engine).count("would_restore_audio") == 1  # Already restored on departure.
    engine.command("choking", 7)
    assert engine.snapshot.choking and not engine.snapshot.choking_silent
    assert engine.snapshot.audio_priority == "choking_maximum_simulated"
    engine.tick(67)
    assert engine.snapshot.message_count == 2


def test_reply_alone_stops_choking_repeats_without_caregiver_silence_latch():
    engine = Engine()
    engine.command("choking", 0)
    engine.command("reply", 1)
    assert not engine.snapshot.choking_silent
    assert engine.snapshot.audio_priority == "choking_maximum_simulated"
    engine.tick(1000)
    assert engine.snapshot.choking and engine.snapshot.message_count == 1


def test_legacy_effect_and_snapshot_constructions_keep_identity_defaults():
    effect = Effect(2, "normal_warning")
    assert (effect.sequence, effect.episode_id, effect.message_number,
            effect.episode_started) == (0, 0, 0, None)
    state = Snapshot(Mode.READY, Incident.NONE, None, True, "No observation.",
                     "idle", (), 0)
    assert (state.episode_id, state.episode_started, state.effect_sequence) == (0, None, 0)


def test_cancel_then_new_fall_at_same_timestamp_has_distinct_episode_identity():
    engine = Engine()
    first = engine.command("fall", 4)
    cancelled = engine.command("cancel", 4)
    second = engine.command("fall", 4)
    assert (first.episode_id, cancelled.episode_id, second.episode_id) == (1, 1, 2)
    assert first.episode_started == second.episode_started == 4
    engine.tick(12)
    assert engine.effects[-1].episode_id == 2
    assert engine.effects[-1].message_number == 1
    assert engine.effects[-1].sequence > cancelled.effect_sequence


@pytest.mark.parametrize("severe_time, expected_deadline", [(27, 35), (35, 41)])
def test_severe_upgrade_retains_episode_start_and_fixed_fall_deadline(severe_time, expected_deadline):
    engine = armed()
    initial = engine.observe(posture(1, "lean"))
    upgraded = engine.observe(posture(severe_time, "severe"))
    assert upgraded.episode_id == initial.episode_id == 1
    assert upgraded.episode_started == initial.episode_started == 1
    assert upgraded.remaining == expected_deadline - severe_time
    engine.tick(expected_deadline)
    message = engine.effects[-1]
    assert message.kind == "would_send_fall"
    assert (message.episode_id, message.episode_started, message.message_number) == (1, 1, 1)


def test_fall_to_choking_creates_new_episode_and_budget_without_repeated_reset():
    engine = Engine()
    engine.command("fall", 1)
    engine.tick(9)
    engine.tick(69)
    fall = engine.snapshot
    assert fall.message_count == 2
    choking = engine.command("choking", 70)
    assert choking.episode_id == fall.episode_id + 1
    assert choking.episode_started == 70
    assert choking.message_count == 1
    first_choking_message = engine.effects[-1]
    assert (first_choking_message.kind, first_choking_message.message_number) == (
        "would_send_choking", 1)
    engine.command("choking", 70)
    engine.command("choking", 71)
    assert engine.snapshot.episode_id == choking.episode_id
    assert engine.snapshot.episode_started == 70
    assert engine.snapshot.message_count == 1
    engine.tick(130)
    assert engine.effects[-1].message_number == 2
    assert engine.effects[-1].episode_id == choking.episode_id


def test_choking_same_timestamp_guard_survives_cancel_and_later_new_episode():
    engine = Engine()
    original = engine.command("choking", 1)
    engine.command("cancel", 1)
    blocked = engine.command("choking", 1)
    assert blocked.incident == Incident.RESOLVED
    assert blocked.episode_id == original.episode_id
    new = engine.command("choking", 1.1)
    assert new.choking and new.incident == Incident.ALERT_ACTIVE
    assert (new.episode_id, new.episode_started, new.message_count) == (2, 1.1, 1)


def test_effect_sequence_stays_monotonic_after_history_eviction_and_resolution():
    engine = Engine(Config(max_effects=2))
    first = engine.command("choking", 1)
    for timestamp in (2, 3, 4, 5):
        engine.command("cancel", timestamp)
        engine.command("choking", timestamp)
    assert first.effects[0].sequence == 1
    assert len(engine.effects) == 2
    assert [effect.sequence for effect in engine.effects] == [
        engine.snapshot.effect_sequence - 1, engine.snapshot.effect_sequence]
    assert engine.snapshot.effect_sequence > len(engine.effects)
    assert engine.effects[-1].episode_id == 5
    assert engine.effects[-1].episode_started == 5
    assert engine.effects[-1].message_number == 1


def test_only_message_effects_get_slot_numbers_and_cap_remains_transport_independent():
    engine = armed()
    engine.observe(posture(1, "lean"))
    engine.tick(31)
    assert engine.effects[-1].message_number == 0
    engine.tick(41)
    for index in range(1, 10):
        engine.tick(41 + index * 60)
    at_cap = engine.snapshot
    engine.tick(10000)
    assert engine.snapshot.effect_sequence == at_cap.effect_sequence
    message_effects = [effect for effect in engine.effects if effect.message_number]
    assert [effect.message_number for effect in message_effects] == list(range(1, 11))
    assert all((effect.episode_id, effect.episode_started) == (1, 1)
               for effect in message_effects)
    engine.command("cancel", 10000)
    assert engine.effects[-1].kind == "incident_resolved"
    assert engine.effects[-1].message_number == 0
    assert engine.snapshot.episode_id == 1


def test_late_warning_tick_preserves_episode_start_separately_from_effect_timestamp():
    engine = Engine()
    began = engine.command("fall", 5)
    late = engine.tick(900)
    message = late.effects[-1]
    assert (began.episode_started, message.episode_started) == (5, 5)
    assert message.timestamp == 13
    assert message.episode_id == began.episode_id
    assert message.message_number == late.message_count == 1
    assert engine.tick(900).effect_sequence == late.effect_sequence
