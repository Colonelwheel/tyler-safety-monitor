"""Scenario contracts for pure simulation; no physical recognition claims."""
from dataclasses import replace

import pytest

from tyler_safety_monitor.simulation_state import Config, Engine, Evidence, Incident, Mode


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
    assert engine.snapshot.incident == Incident.RESOLVED


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


def test_newly_confirmed_caregiver_resolves_choking_and_stops_repeats():
    engine = Engine()
    engine.command("choking", 0)
    qualify_caregiver(engine, began=1)
    assert engine.snapshot.incident == Incident.RESOLVED
    assert engine.snapshot.audio_priority == "caregiver_silent"
    engine.tick(1000)
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


def test_choking_with_existing_caregiver_does_not_resume_after_departure():
    engine = Engine()
    qualify_caregiver(engine)
    engine.command("choking", 3)
    assert engine.snapshot.incident == Incident.RESOLVED
    engine.observe(safe(4, caregiver_departed=True))
    assert engine.snapshot.audio_priority == "idle"
    engine.tick(63)
    assert engine.snapshot.message_count == 1
    assert [(effect.timestamp, effect.kind) for effect in sends(engine)] == [(3, "would_send_choking")]


@pytest.mark.parametrize("action", ["cancel", "resolve", "reply"])
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
