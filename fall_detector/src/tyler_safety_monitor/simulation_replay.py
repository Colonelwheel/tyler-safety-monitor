"""In-memory scenario playback using source seconds, never camera or alert adapters.

Synthetic semantic evidence exercises decisions, not operational recognition.
Personal feature replays remain uncalibrated and cannot imply recovery, caregiver
presence, or a severe event. The source profile/feature schemas are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable

from .simulation_state import Engine, Evidence
from .replay import FeatureSequence
from .tracking import PersonTracker


@dataclass(frozen=True)
class SimulationCommand:
    timestamp: float
    action: str


def _seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Simulation time must be finite nonnegative seconds")
    try:
        result = float(value)
    except OverflowError:
        raise ValueError("Simulation time must be finite nonnegative seconds") from None
    if not isfinite(result) or result < 0:
        raise ValueError("Simulation time must be finite nonnegative seconds")
    return result


@dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    events: tuple
    duration: float

    def __post_init__(self):
        if not isinstance(self.name, str) or not self.name or len(self.name) > 128:
            raise ValueError("Scenario needs a bounded name")
        if not isinstance(self.description, str) or len(self.description) > 2048:
            raise ValueError("Scenario description must be bounded text")
        duration = _seconds(self.duration)
        events = tuple(self.events)
        if len(events) > 20000:
            raise ValueError("Too many simulation events")
        previous = -1.
        observed = -1.
        for event in events:
            if not isinstance(event, (Evidence, SimulationCommand)):
                raise ValueError("Scenario requires evidence or simulated commands")
            stamp = _seconds(event.timestamp)
            if stamp < previous or stamp > duration:
                raise ValueError("Scenario times must be ordered inside its duration")
            if isinstance(event, Evidence):
                if stamp <= observed:
                    raise ValueError("Evidence timestamps must strictly increase")
                observed = stamp
            elif event.action not in {"start", "night", "cancel", "fall", "choking", "reply", "resolve"}:
                raise ValueError("Unknown simulation command")
            previous = stamp
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "duration", duration)


class SimulationRunner:
    """Playback speed never changes event time; seeking backward requires restart."""
    def __init__(self, scenario: Scenario, engine_factory: Callable = Engine):
        if not isinstance(scenario, Scenario):
            raise ValueError("A validated scenario is required")
        self.scenario = scenario
        self._factory = engine_factory
        self.engine = engine_factory()
        self._position = 0.
        self._anchor = None
        self._last_clock = None
        self._index = 0
        self._processed_position = -1.

    @property
    def playing(self):
        return self._anchor is not None

    @property
    def finished(self):
        return self._processed_position >= self.scenario.duration

    @property
    def snapshot(self):
        return self.engine.snapshot

    def _clock(self, now):
        now = _seconds(now)
        if self._last_clock is not None and now < self._last_clock:
            raise ValueError("Playback clock cannot regress")
        self._last_clock = now
        return now

    def position(self, now):
        now = self._clock(now)
        elapsed = 0. if self._anchor is None else now - self._anchor
        return min(self.scenario.duration, self._position + elapsed)

    def play(self, now):
        now = self._clock(now)
        if self._anchor is None and not self.finished:
            self._anchor = now

    def advance_to(self, seconds):
        """Consume all source events, including deadlines between batches."""
        seconds = _seconds(seconds)
        if seconds < self._processed_position or seconds > self.scenario.duration:
            raise ValueError("Simulation time must advance within the scenario")
        self._consume_until(seconds)
        self.engine.tick(seconds)
        self._processed_position = seconds
        return self.engine.snapshot

    def _consume_until(self, seconds, include_equal=True):
        while self._index < len(self.scenario.events):
            event = self.scenario.events[self._index]
            if event.timestamp > seconds or not include_equal and event.timestamp == seconds:
                break
            if isinstance(event, Evidence):
                self.engine.observe(event)
            else:
                self.engine.command(event.action, event.timestamp)
            self._index += 1

    def advance(self, now):
        position = self.position(now)
        snapshot = self.advance_to(position)
        if position >= self.scenario.duration:
            self._position = position
            self._anchor = None
        return snapshot

    def pause(self, now):
        self._position = self.position(now)
        self.advance_to(self._position)
        self._anchor = None

    def rewind(self, now):
        self._clock(now)
        self.engine = self._factory()
        self._index = 0
        self._processed_position = -1.
        self._position = 0.
        self._anchor = None
        return self.advance_to(0.)

    def step(self, seconds, now):
        """Skip waiting while still evaluating every intervening source event."""
        seconds = _seconds(seconds)
        self.pause(now)
        self._position = min(self.scenario.duration, self._position + seconds)
        return self.advance_to(self._position)

    def command(self, action, now):
        position = self.position(now)
        # A cancellation received exactly at expiry precedes the expiry tick.
        # Earlier deadlines still expire inside Engine.command; no retroactivity.
        self._consume_until(position, include_equal=False)
        self.engine.command(action, position)
        snapshot = self.advance_to(position)
        if position >= self.scenario.duration:
            self._position = position
            self._anchor = None
        return snapshot


def _scenario(name, description, seconds, evidence_at, commands=()):
    # 5 Hz is synthetic evidence cadence, not a camera/model requirement.
    events = [evidence_at(round(i / 5, 6)) for i in range(int(seconds * 5) + 1)]
    events.extend(SimulationCommand(t, action) for t, action in commands)
    events.sort(key=lambda event: (event.timestamp, isinstance(event, SimulationCommand)))
    return Scenario(name, description, tuple(events), seconds)


def _safe(t, **changes):
    return Evidence(t, posture="safe", subject_valid=True, safe_confirmed=True,
                    calibrated=True, **changes)


def _posture(t, posture):
    return Evidence(t, posture=posture, subject_valid=True, calibrated=True)


def builtin_scenarios():
    """Named behavior demonstrations with no personal geometry or model scores."""
    return (
        _scenario("Ordinary lean and warning",
                  "A synthetic lean starts at 1s: grace ends at 31s, warning at 41s. No actual message.",
                  50, lambda t: _safe(t) if t < 1 else _posture(t, "lean")),
        _scenario("Slow recovery",
                  "A synthetic lean starts at 1s; slow movement toward safety is not recovery until confirmed at 35s.",
                  45, lambda t: _safe(t, recovery_confirmed=t >= 35) if t < 1 or t >= 35 else (
                      Evidence(t, posture="safe", subject_valid=True, calibrated=True)
                      if t >= 32 else _posture(t, "lean"))),
        _scenario("Severe warning through missing observations",
                  "Severe evidence at 1s starts an 8s countdown. Missing data after 2s cannot cancel or postpone it.",
                  15, lambda t: _safe(t) if t < 1 else (
                      _posture(t, "severe") if t < 2 else Evidence(t, calibrated=True))),
        _scenario("Lean flicker preserves deadlines",
                  "A lean starts at 1s. Repeated missing results never restart its 30s grace or 10s warning.",
                  45, lambda t: _safe(t) if t < 1 else (
                      Evidence(t, calibrated=True) if int(round(t * 5)) % 3 == 0 else _posture(t, "lean"))),
        _scenario("Caregiver arrival and departure",
                  "A separate synthetic person qualifies at 4s. Occlusion at 5s does not prove departure. Departure at 8s restores simulated audio; safe rearm ends at 38s.",
                  42, lambda t: _safe(t, caregiver_id="synthetic-other", caregiver_valid=True)
                  if 2 <= t < 5 else (
                      _safe(t, caregiver_departed=True) if t == 8 else
                      Evidence(t, calibrated=True) if 5 <= t < 8 else _safe(t))),
        _scenario("Caregiver flicker cannot qualify",
                  "One missing result every second breaks caregiver confirmation. Disconnected hits do not add up to two continuous seconds.",
                  8, lambda t: _safe(t, caregiver_id="synthetic-other", caregiver_valid=True)
                  if int(round(t * 5)) % 5 != 0 else _safe(t)),
        _scenario("Supported paired exit",
                  "A caregiver qualifies at 3s. Explicit synthetic paired-exit evidence at 5s allows Away; empty frames alone never do.",
                  10, lambda t: _safe(t, caregiver_id="synthetic-other", caregiver_valid=True)
                  if 1 <= t < 5 else (
                      Evidence(t, paired_exit=True, caregiver_departed=True, calibrated=True)
                      if t == 5 else Evidence(t, calibrated=True) if t > 5 else _safe(t))),
        _scenario("Night and manual emergency",
                  "Night disables automatic warnings. A manual possible-fall at 3s still has an 8s simulated countdown.",
                  15, lambda t: _safe(t) if t < 1 else _posture(t, "severe"),
                  ((0, "night"), (3, "fall"))),
        _scenario("Fault during warning",
                  "A severe warning starts at 1s; fault at 3s remains visible without clearing its deadline. Fault alone creates no incident.",
                  15, lambda t: _safe(t) if t < 1 else (
                      _posture(t, "severe") if t < 3 else Evidence(t, fault=True))),
        _scenario("Caregiver silence overrides choking",
                  "Caregiver qualifies at 3s. Manual choking at 4s creates an immediate simulated alert while audio stays silent. Departure at 6s restores saved simulated audio.",
                  12, lambda t: _safe(t, caregiver_id="synthetic-other", caregiver_valid=True)
                  if 1 <= t < 6 else _safe(t, caregiver_departed=True) if t == 6 else _safe(t),
                  ((4, "choking"),)),
    )


def feature_scenario(sequence: FeatureSequence, selected_track_id=None):
    """Read-only unknown-evidence playback, never infer identity from saved points.

    An optional ID explicitly designates one replay candidate for availability
    diagnostics only. Even visualization-reviewed profiles do not establish an
    approved risk policy, so every personal sample remains uncalibrated/unknown.
    """
    if not isinstance(sequence, FeatureSequence):
        raise ValueError("A validated feature sequence is required")
    if selected_track_id is not None and (type(selected_track_id) is not int or selected_track_id < 1):
        raise ValueError("Replay selection must be a positive candidate ID")
    # Validate mutable nested provenance without modifying the source object.
    validated = FeatureSequence.from_dict(sequence.to_dict())
    origin = validated.samples[0].timestamp
    tracker = PersonTracker()
    events = []
    for sample in validated.samples:
        tracks = tracker.update(sample.observations, sample.timestamp)
        selected = next((t for t in tracks if t.id == selected_track_id), None)
        events.append(Evidence(sample.timestamp - origin, posture="unknown",
                               subject_valid=selected is not None and not selected.identity_uncertain,
                               calibrated=False))
    return Scenario("Approved feature replay - uncalibrated",
                    "Original source intervals; no risk, recovery or caregiver classification. Saved files remain unchanged.",
                    tuple(events), validated.duration)
