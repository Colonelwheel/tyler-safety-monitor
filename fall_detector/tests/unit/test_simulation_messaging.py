"""Synthetic messaging contracts: no devices, network, or personal runtime storage."""
from dataclasses import replace
from copy import deepcopy

import pytest

from tyler_safety_monitor.simulation_messaging import (
    CHOKING_MESSAGE, FALL_MESSAGE, MessagingSession, SimulatedReply,
)
from tyler_safety_monitor.simulation_state import Config, Engine, Evidence, Incident


def choking(now=0, session=None):
    engine = Engine()
    session = session or MessagingSession("test-session")
    session.sync(engine.command("choking", now), now=now)
    return engine, session


def reply(session, **changes):
    return replace(session.make_reply(.1), **changes)


def test_default_transport_preserves_blueprint_preview_and_never_resolves():
    engine, session = choking()
    record, = session.records
    assert record.preview == "SIMULATION ONLY: " + CHOKING_MESSAGE
    assert record.intent_time == record.submitted_time == 0
    assert [status for _, status in record.history] == ["submitted", "accepted", "sent", "delivered"]
    assert session.summary().attempted == session.summary().accepted == session.summary().delivered == 1
    assert engine.snapshot.choking and engine.snapshot.incident == Incident.ALERT_ACTIVE


def test_fall_preview_has_no_urgent_and_delayed_clock_starts_at_submission():
    engine = Engine()
    session = MessagingSession("fall")
    session.set_outcome("delayed", 10)
    session.sync(engine.command("fall", 0), now=0)
    session.sync(engine.tick(500), now=500)
    record, = session.records
    assert record.preview == "SIMULATION ONLY: " + FALL_MESSAGE
    assert "URGENT" not in record.preview
    assert record.intent_time == 8 and record.submitted_time == 500
    assert record.status == "delayed"
    session.advance(509.999)
    assert session.summary().delivered == 0
    session.advance(510)
    assert session.summary().delivered == 1


@pytest.mark.parametrize("outcome,accepted,delivered,failed,pending,unknown", [
    ("accepted", 1, 0, 0, 1, 0), ("sent", 1, 0, 0, 1, 0),
    ("delivered", 1, 1, 0, 0, 0), ("rejected", 0, 0, 1, 0, 0),
    ("failed", 1, 0, 1, 0, 0), ("undelivered", 1, 0, 1, 0, 0),
    ("unknown", 0, 0, 0, 0, 1),
])
def test_outcomes_are_separate_from_attempt_and_delivery(outcome, accepted, delivered, failed, pending, unknown):
    session = MessagingSession("outcome")
    session.set_outcome(outcome)
    engine, session = choking(session=session)
    summary = session.summary()
    assert (summary.intent, summary.attempted) == (1, 1)
    assert (summary.accepted, summary.delivered, summary.failed, summary.pending, summary.unknown) == (
        accepted, delivered, failed, pending, unknown)
    assert session.messaging_unavailable() == (outcome in {"rejected", "failed", "undelivered", "unknown"})
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE


def test_fake_failure_does_not_add_attempts_or_automatic_retries():
    session = MessagingSession("failure")
    session.set_outcome("unknown")
    engine, session = choking(session=session)
    for now in (0, 20, 59.999):
        session.sync(engine.tick(now), now=now)
        session.advance(now)
    assert len(session.records) == 1
    session.sync(engine.tick(60), now=60)
    assert len(session.records) == 2
    for now in range(120, 601, 60):
        session.sync(engine.tick(now), now=now)
    session.advance(99999)
    assert len(session.records) == 10
    assert session.summary().unknown == 10


def test_render_and_duplicate_snapshots_do_not_dispatch():
    engine, session = choking()
    for _ in range(50):
        assert session.sync(engine.snapshot) == ()
        session.summary()
        session.current_preview
    assert len(session.records) == 1


def test_history_eviction_is_fail_closed_with_visible_error():
    engine = Engine(Config(max_effects=1))
    session = MessagingSession("history")
    session.sync(engine.observe(Evidence(0, "safe", True, True, calibrated=True)))
    session.sync(engine.observe(Evidence(1, "lean", True, calibrated=True)))
    assert session.sync(engine.tick(50)) == ()
    assert "history gap" in session.error
    assert not session.records
    engine.tick(110)
    assert not session.sync(engine.snapshot)


def test_consumed_history_eviction_is_safe():
    engine = Engine(Config(max_effects=1))
    session = MessagingSession("consumed")
    session.sync(engine.command("choking", 0))
    for now in range(60, 601, 60):
        session.sync(engine.tick(now), now=now)
    assert not session.error
    assert len(session.records) == 10


def test_record_capacity_fault_never_evicts_previous_identity():
    engine, session = choking(session=MessagingSession("bounded", max_records=1))
    first = session.records
    session.sync(engine.tick(60), now=60)
    assert "capacity" in session.error
    assert session.records == first
    assert session.sync(engine.snapshot) == ()


def test_duplicate_episode_slot_with_new_sequence_fails_before_dispatch():
    engine, session = choking()
    old = engine.effects[0]
    duplicate = replace(old, sequence=2)
    snapshot = replace(engine.snapshot, effects=(old, duplicate), effect_sequence=2)
    assert session.sync(snapshot) == ()
    assert "duplicate episode slot" in session.error
    assert len(session.records) == 1


def test_status_callbacks_reject_wrong_session_unknown_id_and_terminal_regressions():
    engine, session = choking()
    record, = session.records
    assert not session.apply_status("old-session", record.message_id, "failed", 1)
    assert not session.apply_status(session.session_id, "unknown-message", "delivered", 1)
    for status in ("accepted", "sent", "delivered", "failed", "unknown"):
        assert not session.apply_status(session.session_id, record.message_id, status, 1)
    assert session.records == (record,)
    assert not session.receive_reply(reply(session, session_id="old-session"), engine.snapshot, 1)


def test_pending_unknown_can_be_resolved_but_never_cycles_or_regresses():
    session = MessagingSession("unknown")
    session.set_outcome("unknown")
    engine, session = choking(session=session)
    record, = session.records
    session.advance(1)
    assert not session.apply_status(session.session_id, record.message_id, "sent", 1)
    assert not session.apply_status(session.session_id, record.message_id, "accepted", 1)
    assert session.apply_status(session.session_id, record.message_id, "delivered", 1)
    assert not session.messaging_unavailable()
    assert session.summary().delivered == 1
    assert len(session.records[0].history) == 3
    assert engine.snapshot.choking


def test_closed_session_discards_delayed_status_and_replies():
    session = MessagingSession("old")
    session.set_outcome("delayed", 2)
    engine, session = choking(session=session)
    prior = session.records
    pending_reply = session.make_reply(.1)
    session.close()
    session.advance(10)
    assert session.records == prior
    assert not session.receive_reply(pending_reply, engine.snapshot, 10)
    assert not session.sync(engine.tick(60), now=60)
    new = MessagingSession("new")
    assert not new.receive_reply(pending_reply, engine.snapshot, 10)


def test_reply_accepts_any_body_without_changing_engine_or_claiming_presence():
    engine, session = choking()
    valid = reply(session, body="anything")
    assert session.receive_reply(valid, engine.snapshot, .1)
    assert engine.snapshot.choking and not engine.snapshot.caregiver
    engine.command("reply", .1)
    assert engine.snapshot.choking and not engine.snapshot.choking_silent
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    session.sync(engine.tick(60), now=60)
    assert len(session.records) == 1


@pytest.mark.parametrize("changes", [
    {"sender": "synthetic:other"}, {"recipient": "synthetic:other"},
    {"session_id": "old"}, {"created": 0}, {"created": -.1},
    {"created": float("nan")}, {"created": float("inf")}, {"created": True},
    {"created": 2}, {"reply_id": ""}, {"reply_id": "x" * 129},
])
def test_invalid_reply_envelopes_do_nothing(changes):
    engine, session = choking()
    assert not session.receive_reply(reply(session, **changes), engine.snapshot, 1)
    assert engine.snapshot.choking and len(session.records) == 1


def test_duplicate_reply_id_stays_rejected_across_episodes():
    engine, session = choking()
    valid = reply(session, reply_id="once")
    assert session.receive_reply(valid, engine.snapshot, .1)
    assert not session.receive_reply(valid, engine.snapshot, .1)
    session.sync(engine.command("cancel", 1), now=1)
    session.sync(engine.command("choking", 2), now=2)
    duplicate = replace(valid, created=2.1)
    assert not session.receive_reply(duplicate, engine.snapshot, 2.1)


def test_pre_choking_reply_is_stale_after_escalation_but_new_reply_accepts():
    engine = Engine()
    session = MessagingSession("upgrade")
    session.sync(engine.command("fall", 0), now=0)
    before = session.make_reply(.1)
    session.sync(engine.command("choking", 1), now=1)
    assert not session.receive_reply(before, engine.snapshot, 1.1)
    assert session.receive_reply(session.make_reply(1.01), engine.snapshot, 1.1)
    assert session.summary(engine.snapshot.episode_id).delivered == 1


def test_reply_capacity_fails_closed_without_reaccepting_evicted_ids():
    engine, session = choking(session=MessagingSession("reply-bound", max_reply_ids=1))
    first = reply(session, reply_id="first")
    assert session.receive_reply(first, engine.snapshot, .1)
    assert not session.receive_reply(reply(session, reply_id="second"), engine.snapshot, .2)
    assert "capacity" in session.error
    assert not session.receive_reply(first, engine.snapshot, .3)


def test_reply_cannot_acknowledge_resolved_or_absent_episode():
    engine = Engine()
    session = MessagingSession("inactive")
    assert not session.receive_reply(session.make_reply(.1), engine.snapshot, .1)
    session.sync(engine.command("choking", 1), now=1)
    session.sync(engine.command("cancel", 2), now=2)
    assert not session.receive_reply(session.make_reply(2.1), engine.snapshot, 2.1)


def test_pause_freezes_pending_delivery_and_cancel_does_not_retract_submission():
    session = MessagingSession("pause")
    session.set_outcome("delayed", 10)
    engine, session = choking(session=session)
    session.advance(2)
    for _ in range(20):
        session.advance(2)
    assert session.summary().pending == 1
    session.sync(engine.command("cancel", 2), now=2)
    session.advance(10)
    assert session.summary().delivered == 1
    assert engine.snapshot.incident == Incident.RESOLVED


@pytest.mark.parametrize("fault", ["history", "record_capacity"])
def test_valid_reply_survives_outbound_fault_and_stops_choking_repeats(fault):
    engine = Engine(Config(max_effects=1)) if fault == "history" else Engine()
    session = MessagingSession("outbound-fault", max_records=1)
    session.sync(engine.command("choking", 0), now=0)
    engine.tick(60)
    if fault == "history":
        engine.tick(120)
    session.sync(engine.snapshot, now=120 if fault == "history" else 60)
    assert session.error
    count = engine.snapshot.message_count
    reply_time = 121 if fault == "history" else 61
    accepted = session.receive_reply(session.make_reply(reply_time), engine.snapshot, reply_time)
    assert accepted
    engine.command("reply", reply_time)
    assert engine.snapshot.choking and not engine.snapshot.choking_silent
    assert not engine.snapshot.caregiver
    assert engine.snapshot.incident == Incident.ALERT_ACTIVE
    assert engine.tick(1000).message_count == count
    assert session.error


def test_future_status_callback_cannot_advance_paused_fake_delivery():
    session = MessagingSession("paused-callback")
    session.set_outcome("delayed", 10)
    engine, session = choking(session=session)
    session.advance(2)
    message = session.records[0]
    assert not session.apply_status(session.session_id, message.message_id, "delivered", 10)
    assert session.records[0].status == "delayed"
    session.advance(2)
    assert session.summary().delivered == 0
    session.advance(10)
    assert session.summary().delivered == 1


@pytest.mark.parametrize("kwargs", [
    {"sender": "+15551234567"}, {"recipient": "+15551234567"},
    {"recipient": "synthetic:monitor"}, {"max_records": 0},
    {"max_records": True}, {"max_reply_ids": 4097}, {"session_id": ""},
])
def test_configuration_accepts_only_bounded_synthetic_identity(kwargs):
    with pytest.raises(ValueError):
        MessagingSession(**kwargs)


@pytest.mark.parametrize("status,delay", [("real", 0), ("delayed", 0), ("delayed", -1),
                                          ("sent", float("nan")), ("sent", 86401)])
def test_invalid_fake_outcomes_fail_validation(status, delay):
    with pytest.raises(ValueError):
        MessagingSession().set_outcome(status, delay)


def test_source_clock_validation_and_stale_status_timestamp():
    session = MessagingSession("clock")
    session.set_outcome("sent")
    engine, session = choking(session=session)
    message = session.records[0]
    session.advance(2)
    with pytest.raises(ValueError):
        session.advance(1)
    assert not session.receive_reply(session.make_reply(.1), engine.snapshot, 1)
    assert session.apply_status(session.session_id, message.message_id, "unknown", 2)
    assert not session.apply_status(session.session_id, message.message_id, "delivered", 1)


def test_synthetic_object_copy_continuation_retains_cursors_and_reply_ids():
    # Object copies exercise only in-memory checkpoint continuation. They provide
    # no evidence of filesystem persistence or process-restart durability.
    session = MessagingSession("object-copy")
    session.set_outcome("accepted")
    engine, session = choking(session=session)
    acknowledged = session.make_reply(.1, reply_id="already-acknowledged")
    assert session.receive_reply(acknowledged, engine.snapshot, .1)
    session.sync(engine.command("reply", .1), now=.1)
    session.sync(engine.command("cancel", 1), now=1)
    session.sync(engine.command("choking", 2), now=2)
    assert session.summary().accepted == 2
    checkpoint_engine, checkpoint_session = deepcopy((engine, session))
    identities = tuple(record.message_id for record in checkpoint_session.records)
    assert checkpoint_session.sync(checkpoint_engine.snapshot, now=2) == ()
    duplicate = replace(acknowledged, created=2.1)
    assert not checkpoint_session.receive_reply(duplicate, checkpoint_engine.snapshot, 2.1)
    added = checkpoint_session.sync(checkpoint_engine.tick(62), now=62)
    assert len(added) == 1
    assert added[0].episode_id == checkpoint_engine.snapshot.episode_id
    assert added[0].message_number == 2
    assert added[0].message_id not in identities
    assert tuple(record.message_id for record in checkpoint_session.records[:2]) == identities
    assert checkpoint_session.summary().accepted == 3
    assert session.summary().accepted == 2
    assert engine.snapshot.message_count == 1


def test_direct_unknown_to_delivered_implies_acceptance_without_intermediate_event():
    session = MessagingSession("delivery-proof")
    session.set_outcome("unknown")
    engine, session = choking(session=session)
    record = session.records[0]
    assert session.summary().accepted == session.summary().delivered == 0
    session.advance(1)
    assert session.apply_status(session.session_id, record.message_id, "delivered", 1)
    assert [status for _, status in session.records[0].history] == ["submitted", "unknown", "delivered"]
    summary = session.summary(engine.snapshot.episode_id)
    assert summary.accepted == summary.delivered == 1
    assert summary.accepted >= summary.delivered
