"""Bounded fake messaging for synthetic sessions only; no I/O or repeat scheduler.

Engine owns every intent and cap. This ledger records each effect sequence once.
Storage is deliberately in memory: process-restart durability is future scope.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite
import re
from uuid import uuid4

from .simulation_state import Incident, Snapshot


FALL_TEXT = ("Tyler Safety Monitor detected a possible dangerous forward fall. "
             "Tyler did not recover or cancel the alert. Please come check his position immediately.")
CHOKING_TEXT = ("URGENT: Tyler activated the choking emergency alert and may be "
                "unable to breathe or respond. Come immediately.")
FALL_MESSAGE = FALL_TEXT
CHOKING_MESSAGE = CHOKING_TEXT
MESSAGE_KINDS = frozenset({"would_send_fall", "would_repeat_fall",
                          "would_send_choking", "would_repeat_choking"})
OUTCOMES = ("delivered", "accepted", "sent", "rejected", "failed",
            "undelivered", "delayed", "unknown")
TERMINAL = frozenset({"delivered", "rejected", "failed", "undelivered"})
UNAVAILABLE = frozenset({"rejected", "failed", "undelivered", "unknown"})
LABEL = re.compile(r"synthetic:[A-Za-z][A-Za-z0-9_-]{0,47}\Z")


def _time(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("time must be finite nonnegative simulation seconds")
    try:
        result = float(value)
    except OverflowError:
        raise ValueError("time must be finite nonnegative simulation seconds") from None
    if not isfinite(result) or result < 0:
        raise ValueError("time must be finite nonnegative simulation seconds")
    return result


def _identity(value):
    return isinstance(value, str) and 0 < len(value) <= 128 and value.strip() == value


@dataclass(frozen=True)
class MessageRecord:
    message_id: str
    session_id: str
    sequence: int
    episode_id: int
    message_number: int
    kind: str
    preview: str
    intent_time: float
    submitted_time: float
    status: str
    history: tuple[tuple[float, str], ...]


@dataclass(frozen=True)
class SimulatedReply:
    reply_id: str
    sender: str
    recipient: str
    created: float
    session_id: str
    # Any body acknowledges after envelope validation. Never displayed or stored.
    body: str = ""


@dataclass(frozen=True)
class MessagingSummary:
    intent: int
    attempted: int
    accepted: int
    delivered: int
    failed: int
    pending: int
    unknown: int
    last_status: str
    error: str | None


class MessagingSession:
    """Fake transport, exactly-once sequence consumption and envelope filtering.

    Caller must pair this with one Engine and replace/close it on Engine reset.
    Methods never command the Engine: validated replies are returned to its owner.
    """
    def __init__(self, session_id=None, *, sender="synthetic:monitor",
                 recipient="synthetic:caregiver", max_records=256, max_reply_ids=256):
        if not isinstance(sender, str) or not LABEL.fullmatch(sender):
            raise ValueError("sender must be a synthetic label, never a phone number")
        if not isinstance(recipient, str) or not LABEL.fullmatch(recipient) or recipient == sender:
            raise ValueError("recipient must be a distinct synthetic label")
        for capacity in (max_records, max_reply_ids):
            if type(capacity) is not int or not 1 <= capacity <= 4096:
                raise ValueError("in-memory capacities must be integers between 1 and 4096")
        session_id = uuid4().hex if session_id is None else session_id
        if not _identity(session_id):
            raise ValueError("session identity must be bounded text")
        self.session_id = session_id
        self.sender, self.recipient = sender, recipient
        self.max_records, self.max_reply_ids = max_records, max_reply_ids
        self._records: dict[str, MessageRecord] = {}
        self._pending: dict[str, tuple[float, str]] = {}
        self._reply_ids: set[str] = set()
        self._reply_serial = 0
        self._cursor = 0
        self._now = 0.
        self._closed = False
        self._outcome = "delivered"
        self._delay = 0.
        self.error: str | None = None

    @property
    def records(self):
        return tuple(self._records.values())

    @property
    def current_preview(self):
        return self.records[-1].preview if self._records else "SIMULATION ONLY: no message intent."

    def close(self):
        self._closed = True
        self._pending.clear()

    def set_outcome(self, status, delay=0.):
        if not isinstance(status, str) or status not in OUTCOMES:
            raise ValueError("unsupported fake delivery outcome")
        delay = _time(delay)
        if delay > 86400 or status == "delayed" and delay <= 0:
            raise ValueError("delay must be at most 86400 seconds; delayed needs a positive delay")
        self._outcome, self._delay = status, delay

    def _fail(self, text):
        # No eviction or subsequent dispatch after a gap/capacity fault.
        if self.error is None:
            self.error = "SIMULATION ONLY: " + text
        self._pending.clear()

    def sync(self, snapshot: Snapshot, now=None):
        """Consume new contiguous effects once; optional now sets submission time."""
        if not isinstance(snapshot, Snapshot):
            raise ValueError("sync requires an Engine Snapshot")
        if self._closed or self.error:
            return ()
        if now is not None:
            self.advance(now)
        end = snapshot.effect_sequence
        if type(end) is not int or end < 0:
            self._fail("invalid effect sequence; messaging unavailable.")
            return ()
        if end < self._cursor:
            # Stale snapshots cannot rewind this session or re-dispatch.
            return ()
        if any(type(effect.sequence) is not int or effect.sequence < 1 for effect in snapshot.effects):
            self._fail("invalid effect sequence; messaging unavailable.")
            return ()
        effects = tuple(effect for effect in snapshot.effects if effect.sequence > self._cursor)
        expected = self._cursor + 1
        for effect in effects:
            if type(effect.sequence) is not int or effect.sequence != expected:
                self._fail("effect history gap; no missing message was fabricated.")
                return ()
            expected += 1
        if expected - 1 != end:
            self._fail("effect history gap; no missing message was fabricated.")
            return ()
        for effect in effects:
            if effect.kind in MESSAGE_KINDS and (
                    type(effect.episode_id) is not int or effect.episode_id <= 0
                    or type(effect.message_number) is not int or not 1 <= effect.message_number <= 10):
                self._fail("invalid message identity; messaging unavailable.")
                return ()
        messages = [effect for effect in effects if effect.kind in MESSAGE_KINDS]
        if len(self._records) + len(messages) > self.max_records:
            self._fail("message ledger capacity reached; no history was discarded.")
            return ()
        # Slot identities are independent of timestamps/kinds. Reject malformed
        # duplicate slots before submitting any part of this snapshot.
        slots = {(record.episode_id, record.message_number) for record in self._records.values()}
        for effect in messages:
            slot = (effect.episode_id, effect.message_number)
            if slot in slots:
                self._fail("duplicate episode slot; messaging unavailable.")
                return ()
            slots.add(slot)
            try:
                _time(effect.timestamp)
            except ValueError:
                self._fail("invalid message time; messaging unavailable.")
                return ()
        new_ids = []
        for effect in effects:
            self._cursor = effect.sequence
            if effect.kind not in MESSAGE_KINDS:
                continue
            submitted = max(self._now, _time(effect.timestamp))
            self._now = submitted
            message_id = f"{self.session_id}:{effect.episode_id}:{effect.message_number}"
            content = CHOKING_TEXT if effect.kind.endswith("choking") else FALL_TEXT
            record = MessageRecord(message_id, self.session_id, effect.sequence,
                                   effect.episode_id, effect.message_number,
                                   effect.kind, "SIMULATION ONLY: " + content,
                                   effect.timestamp, submitted, "submitted",
                                   ((submitted, "submitted"),))
            self._records[message_id] = record
            new_ids.append(message_id)
            if self._delay > 0:
                self.apply_status(self.session_id, message_id, "delayed", submitted)
                final = "delivered" if self._outcome == "delayed" else self._outcome
                self._pending[message_id] = (submitted + self._delay, final)
            else:
                self._complete(message_id, self._outcome, submitted)
        return tuple(self._records[message_id] for message_id in new_ids)

    def _complete(self, message_id, status, now):
        if status in {"accepted", "sent", "delivered", "failed", "undelivered"}:
            self.apply_status(self.session_id, message_id, "accepted", now)
        if status in {"sent", "delivered", "undelivered"}:
            self.apply_status(self.session_id, message_id, "sent", now)
        self.apply_status(self.session_id, message_id, status, now)

    def advance(self, now):
        now = _time(now)
        if now < self._now:
            raise ValueError("fake delivery source time cannot regress")
        self._now = now
        if self._closed or self.error:
            return
        for message_id, (due, final) in tuple(self._pending.items()):
            if due <= now:
                del self._pending[message_id]
                self._complete(message_id, final, due)

    def apply_status(self, session_id, message_id, status, now):
        """Apply a fake provider event only to this active session and known ID."""
        now = _time(now)
        if (self._closed or self.error or session_id != self.session_id
                or not isinstance(status, str)
                or status not in {"submitted", "delayed", "accepted", "sent", "unknown"} | TERMINAL):
            return False
        record = self._records.get(message_id)
        if record is None or now > self._now or now < record.history[-1][0]:
            return False
        if status == record.status or record.status in TERMINAL:
            return False
        transitions = {
            "submitted": {"delayed", "accepted", "sent", "unknown"} | TERMINAL,
            "delayed": {"accepted", "sent", "unknown"} | TERMINAL,
            "accepted": {"sent", "unknown", "delivered", "failed", "undelivered"},
            "sent": {"unknown", "delivered", "failed", "undelivered"},
            "unknown": {"delivered", "failed", "undelivered", "rejected"},
        }
        if status not in transitions.get(record.status, set()):
            return False
        self._records[message_id] = replace(
            record, status=status, history=record.history + ((now, status),))
        if status in TERMINAL:
            self._pending.pop(message_id, None)
        return True

    def summary(self, episode_id=None):
        records = tuple(record for record in self._records.values()
                        if episode_id is None or record.episode_id == episode_id)
        return MessagingSummary(
            len(records), len(records),
            sum(any(status in {"accepted", "sent", "delivered", "undelivered"}
                    for _, status in record.history) for record in records),
            sum(record.status == "delivered" for record in records),
            sum(record.status in {"rejected", "failed", "undelivered"} for record in records),
            sum(record.status in {"submitted", "delayed", "accepted", "sent"} for record in records),
            sum(record.status == "unknown" for record in records),
            records[-1].status if records else "none", self.error)

    def messaging_unavailable(self, episode_id=None):
        return bool(self.error or any(record.status in UNAVAILABLE for record in self._records.values()
                                      if episode_id is None or record.episode_id == episode_id))

    def make_reply(self, created, reply_id=None):
        created = _time(created)
        self._reply_serial += 1
        reply_id = reply_id or f"synthetic-reply-{self._reply_serial}"
        return SimulatedReply(reply_id, self.recipient, self.sender, created, self.session_id)

    def receive_reply(self, reply, snapshot, now):
        """Validate synthetic envelope; any body acknowledges, without presence."""
        now = _time(now)
        if (self._closed or not isinstance(reply, SimulatedReply)
                or not isinstance(snapshot, Snapshot)
                or not _identity(reply.reply_id) or reply.reply_id in self._reply_ids
                or reply.session_id != self.session_id
                or reply.sender != self.recipient or reply.recipient != self.sender
                or type(snapshot.episode_id) is not int or snapshot.episode_id <= 0
                or snapshot.incident in {Incident.NONE, Incident.RESOLVED}
                or snapshot.episode_started is None):
            return False
        try:
            created, started = _time(reply.created), _time(snapshot.episode_started)
        except ValueError:
            return False
        if now < self._now or not started < created <= now:
            return False
        if len(self._reply_ids) >= self.max_reply_ids:
            self._fail("reply identity capacity reached; duplicate protection retained.")
            return False
        self._reply_ids.add(reply.reply_id)
        return True
