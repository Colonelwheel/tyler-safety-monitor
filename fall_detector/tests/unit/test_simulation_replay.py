"""Source-time replay invariants; every input is synthetic and in memory."""
import pytest

from tyler_safety_monitor.simulation_state import Evidence, Incident, Mode
from tyler_safety_monitor.simulation_replay import (
    Scenario, SimulationCommand, SimulationRunner, builtin_scenarios, feature_scenario,
)
from tyler_safety_monitor.replay import FeatureSample, FeatureSequence
from tyler_safety_monitor.scene import SceneConfig
from tyler_safety_monitor.tracking import PoseObservation


def named(name):
    return next(s for s in builtin_scenarios() if s.name == name)


def sends(runner):
    return [e for e in runner.engine.effects if e.kind.startswith("would_send_")]


def test_batched_gui_delivery_matches_regular_source_processing():
    scenario = named("Lean flicker preserves deadlines")
    regular, batched = SimulationRunner(scenario), SimulationRunner(scenario)
    for i in range(226):
        regular.advance_to(i / 5)
    batched.advance_to(45)
    assert batched.snapshot == regular.snapshot
    assert sends(batched)[0].timestamp == 41


def test_pause_and_resume_freeze_source_deadline():
    runner = SimulationRunner(named("Ordinary lean and warning"))
    runner.play(100)
    runner.pause(110)
    assert runner.position(1000) == 10
    assert runner.snapshot.incident == Incident.LEAN_GRACE
    runner.play(1000)
    runner.advance(1020)
    assert runner.position(1020) == 30
    assert not sends(runner)
    runner.advance(1031)
    assert sends(runner)[0].timestamp == 41


def test_rewind_clears_all_incident_and_effect_history():
    runner = SimulationRunner(named("Severe warning through missing observations"))
    runner.play(0)
    runner.advance(10)
    assert sends(runner)
    runner.rewind(12)
    assert not runner.playing
    assert runner.position(12) == 0
    assert not runner.engine.effects
    assert runner.snapshot.incident == Incident.NONE


def test_fast_forward_evaluates_every_source_event_and_resumes_from_new_time():
    runner = SimulationRunner(named("Ordinary lean and warning"))
    runner.play(100)
    runner.step(30, 110)
    assert not runner.playing
    assert runner.position(200) == 40
    assert runner.snapshot.incident == Incident.NORMAL_WARNING
    assert runner.snapshot.remaining == 1
    runner.play(200)
    runner.advance(201)
    assert sends(runner)[0].timestamp == 41


@pytest.mark.parametrize("offset,expected", [(8.999, False), (9., False), (9.001, True)])
def test_manual_cancel_boundary_and_no_retroactive_cancellation(offset, expected):
    runner = SimulationRunner(named("Severe warning through missing observations"))
    runner.play(100)
    runner.command("cancel", 100 + offset)
    assert bool(sends(runner)) == expected
    assert runner.snapshot.incident == Incident.RESOLVED


def test_end_of_replay_does_not_manufacture_extra_elapsed_time():
    runner = SimulationRunner(Scenario("short", "No observations", (), 1))
    runner.play(0)
    runner.command("fall", 0)
    runner.advance(100)
    assert not runner.playing
    assert runner.position(200) == 1
    assert runner.snapshot.remaining == 7
    assert not sends(runner)


def test_unclassified_feature_replay_keeps_source_intervals_and_original_data():
    sequence = FeatureSequence(SceneConfig(), {"source_kind": "synthetic"}, (
        FeatureSample(100., 0, (PoseObservation((.5, .4), None, .9),)),
        FeatureSample(100.1, 1, ()),
        FeatureSample(103., 2, (PoseObservation((.5, .7), None, .9),)),
    ))
    before = sequence.to_dict()
    scenario = feature_scenario(sequence, selected_track_id=1)
    assert [event.timestamp for event in scenario.events] == pytest.approx([0, .1, 3])
    assert scenario.events[0].subject_valid
    assert not scenario.events[1].subject_valid
    assert all(not e.calibrated and e.posture == "unknown" for e in scenario.events)
    assert all(not e.caregiver_valid and not e.paired_exit and not e.safe_confirmed for e in scenario.events)
    runner = SimulationRunner(scenario)
    runner.advance_to(3)
    assert runner.snapshot.mode == Mode.READY
    assert runner.snapshot.uncertain
    assert not runner.engine.effects
    assert sequence.to_dict() == before


def test_slow_recovery_does_not_resolve_until_positive_confirmation():
    runner = SimulationRunner(named("Slow recovery"))
    runner.advance_to(34)
    assert runner.snapshot.incident == Incident.NORMAL_WARNING
    runner.advance_to(35)
    assert runner.snapshot.incident == Incident.RESOLVED
    assert not sends(runner)


def test_caregiver_occlusion_and_departure_restore_before_rearm():
    runner = SimulationRunner(named("Caregiver arrival and departure"))
    runner.advance_to(4)
    assert runner.snapshot.mode == Mode.CAREGIVER_PRESENT
    runner.advance_to(7)
    assert runner.snapshot.audio_priority == "caregiver_silent"
    runner.advance_to(8)
    assert runner.snapshot.mode == Mode.READY
    assert any(e.kind == "would_restore_audio" and e.timestamp == 8 for e in runner.engine.effects)
    runner.advance_to(37.8)
    assert runner.snapshot.mode == Mode.READY
    runner.advance_to(38)
    assert runner.snapshot.mode == Mode.ARMED


def test_explicit_paired_exit_and_manual_night_scenarios():
    runner = SimulationRunner(named("Supported paired exit"))
    runner.advance_to(5)
    assert runner.snapshot.mode == Mode.AWAY
    night = SimulationRunner(named("Night and manual emergency"))
    night.advance_to(10.8)
    assert night.snapshot.mode == Mode.NIGHT
    assert not sends(night)
    night.advance_to(11)
    assert sends(night)[0].timestamp == 11


def test_disconnected_caregiver_hits_never_qualify():
    runner = SimulationRunner(named("Caregiver flicker cannot qualify"))
    runner.advance_to(8)
    assert runner.snapshot.mode == Mode.ARMED
    assert not any(e.kind == "would_silence_audio" for e in runner.engine.effects)


@pytest.mark.parametrize("duration,events", [
    (1, (Evidence(2),)), (2, (Evidence(1), Evidence(1))),
    (2, (Evidence(1), Evidence(0))), (True, ()),
    (2, (SimulationCommand(1, "real_sms"),)), (float("nan"), ()),
])
def test_invalid_scenarios_rejected(duration, events):
    with pytest.raises(ValueError):
        Scenario("invalid", "test", events, duration)


def test_backward_or_nonfinite_playback_is_rejected():
    runner = SimulationRunner(named("Ordinary lean and warning"))
    runner.play(100)
    with pytest.raises(ValueError):
        runner.advance(99)
    with pytest.raises(ValueError):
        runner.advance(float("nan"))
    runner.advance_to(5)
    with pytest.raises(ValueError):
        runner.advance_to(4)
