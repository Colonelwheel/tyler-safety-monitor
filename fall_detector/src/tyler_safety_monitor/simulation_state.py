"""Pure, explicitly simulated policy; never performs audio, messaging, or I/O.

Posture and confirmation flags are supplied scenario evidence, not a detector or
validated personal thresholds. Timers use source seconds and survive uncertainty.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from enum import Enum
from math import isfinite


class Mode(str, Enum):
    STARTING = "STARTING"
    READY = "READY"
    ARMED = "ARMED"
    NIGHT = "NIGHT"
    CAREGIVER_PRESENT = "CAREGIVER_PRESENT"
    AWAY = "AWAY"
    FAULT = "FAULT"


class Incident(str, Enum):
    NONE = "NONE"
    LEAN_GRACE = "LEAN_GRACE"
    NORMAL_WARNING = "NORMAL_WARNING"
    SEVERE_WARNING = "SEVERE_WARNING"
    ALERT_ACTIVE = "ALERT_ACTIVE"
    RESOLVED = "RESOLVED"


def _seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("time must be finite nonnegative source seconds")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError("time must be finite nonnegative source seconds") from None
    if not isfinite(value) or value < 0:
        raise ValueError("time must be finite nonnegative source seconds")
    return value


@dataclass(frozen=True)
class Config:
    lean_grace: float = 30.
    normal_warning: float = 10.
    severe_warning: float = 8.
    caregiver_confirm: float = 2.
    rearm: float = 30.
    repeat: float = 60.
    max_messages: int = 10
    max_gap: float = .4  # Synthetic continuity policy, not an operational threshold.
    max_effects: int = 256

    def __post_init__(self):
        for name in ("lean_grace", "normal_warning", "severe_warning",
                     "caregiver_confirm", "rearm", "repeat", "max_gap"):
            if _seconds(getattr(self, name)) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("max_messages", "max_effects"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_messages > 10 or self.max_effects > 4096:
            raise ValueError("message cap is at most ten; effect history is bounded to 4096")


@dataclass(frozen=True)
class Evidence:
    timestamp: float
    posture: str = "unknown"
    subject_valid: bool = False
    safe_confirmed: bool = False
    caregiver_id: int | str | None = None
    caregiver_valid: bool = False
    caregiver_departed: bool = False
    paired_exit: bool = False
    fault: bool = False
    calibrated: bool = False
    recovery_confirmed: bool = False

    def __post_init__(self):
        object.__setattr__(self, "timestamp", _seconds(self.timestamp))
        if not isinstance(self.posture, str) or self.posture not in {"safe", "lean", "severe", "unknown"}:
            raise ValueError("unsupported posture evidence")
        for name in ("subject_valid", "safe_confirmed", "caregiver_valid",
                     "caregiver_departed", "paired_exit", "fault", "calibrated", "recovery_confirmed"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be boolean")
        identity = self.caregiver_id
        if identity is not None and not (
                type(identity) is int and identity > 0
                or isinstance(identity, str) and 0 < len(identity) <= 128):
            raise ValueError("caregiver ID must be a positive integer or bounded text")
        if self.caregiver_valid and identity is None:
            raise ValueError("qualified caregiver evidence requires a separate candidate ID")
        if self.caregiver_valid and self.caregiver_departed:
            raise ValueError("caregiver cannot be currently visible and departed")
        if self.paired_exit and self.subject_valid:
            raise ValueError("paired exit cannot claim a currently visible subject")


@dataclass(frozen=True)
class Effect:
    timestamp: float
    kind: str


@dataclass(frozen=True)
class Snapshot:
    mode: Mode
    incident: Incident
    remaining: float | None
    uncertain: bool
    reason: str
    audio_priority: str
    effects: tuple[Effect, ...]
    message_count: int
    fault: bool = False
    caregiver: bool = False
    night: bool = False
    caregiver_current: bool = False
    choking: bool = False
    choking_silent: bool = False


class Engine:
    """Bounded deterministic reducer, disconnected from every operational adapter.

Observations increase strictly. Commands/ticks may share a source timestamp.
At an observation deadline, positive recovery/caregiver evidence is evaluated
before expiry. Once an earlier tick expires a warning, a later command cannot
retroactively cancel its already emitted simulated intent.
"""
    def __init__(self, config: Config | None = None):
        self.config = config if config is not None else Config()
        if not isinstance(self.config, Config):
            raise ValueError("config must be Config")
        self._mode = Mode.STARTING
        self._incident = Incident.NONE
        self._now = 0.
        self._last_observation = None
        self._deadline = None
        self._uncertain = True
        self._reason = "Simulation starting; no validated observation."
        self._night = self._fault = self._caregiver = self._away = False
        self._caregiver_candidate = None
        self._caregiver_since = self._caregiver_last = None
        self._rearm_required = False
        self._safe_since = self._safe_last = None
        self._message_count = 0
        self._next_repeat = None
        self._choking = False
        self._choking_silent = False
        self._last_choking_command = None
        self._effects = deque(maxlen=self.config.max_effects)

    @property
    def effects(self):
        return tuple(self._effects)

    @property
    def snapshot(self):
        caregiver_current = bool(self._caregiver and self._caregiver_last is not None
                                 and self._now - self._caregiver_last <= self.config.max_gap)
        priority = ("caregiver_silent" if self._caregiver else
                    "choking_silent_simulated" if self._choking_silent else
                    "choking_maximum_simulated" if self._choking else
                    "selected_volume_simulated" if self._incident in {
                        Incident.NORMAL_WARNING, Incident.SEVERE_WARNING,
                        Incident.ALERT_ACTIVE} else "idle")
        return Snapshot(self._mode, self._incident,
                        None if self._deadline is None else max(0., self._deadline - self._now),
                        self._uncertain or self._caregiver and not caregiver_current,
                        self._reason, priority, self.effects,
                        self._message_count, self._fault, self._caregiver, self._night,
                        caregiver_current, self._choking, self._choking_silent)

    def _clock(self, timestamp):
        timestamp = _seconds(timestamp)
        if timestamp < self._now:
            raise ValueError("simulation source time cannot regress")
        self._now = timestamp
        if self._mode == Mode.STARTING:
            self._mode = Mode.READY
        return timestamp

    def _effect(self, kind, timestamp=None):
        self._effects.append(Effect(self._now if timestamp is None else timestamp, kind))

    def _resolve(self, reason):
        if self._incident not in {Incident.NONE, Incident.RESOLVED}:
            if self._choking and not self._caregiver and not self._choking_silent:
                self._effect("would_restore_audio")
            self._incident = Incident.RESOLVED
            self._deadline = self._next_repeat = None
            self._choking = self._choking_silent = False
            self._effect("incident_resolved")
        self._reason = reason

    def _stop_choking_repeats(self, reason):
        # Acknowledgement/presence stops messaging, not the manual emergency.
        # Only a subsequent explicit Cancel/Resolve clears choking.
        if self._next_repeat is not None:
            self._effect("choking_repeats_stopped")
        self._next_repeat = None
        self._reason = reason

    def _begin(self, severe=False):
        new_deadline = self._now + (self.config.severe_warning if severe else self.config.lean_grace)
        if self._incident not in {Incident.NONE, Incident.RESOLVED}:
            if severe and self._incident in {Incident.LEAN_GRACE, Incident.NORMAL_WARNING}:
                previous_alert_deadline = self._deadline
                if self._incident == Incident.LEAN_GRACE:
                    previous_alert_deadline += self.config.normal_warning
                self._incident = Incident.SEVERE_WARNING
                self._deadline = min(previous_alert_deadline, new_deadline)
                self._reason = "Simulated severe evidence; existing deadline cannot be postponed."
            return
        self._message_count = 0
        self._next_repeat = None
        self._choking = self._choking_silent = False
        self._incident = Incident.SEVERE_WARNING if severe else Incident.LEAN_GRACE
        self._deadline = new_deadline
        self._reason = "Simulated severe warning." if severe else "Simulated ordinary lean grace."

    def _send(self, timestamp, repeat=False):
        if self._message_count >= self.config.max_messages:
            self._next_repeat = None
            return
        self._message_count += 1
        kind = "would_repeat_" if repeat else "would_send_"
        self._effect(kind + ("choking" if self._choking else "fall"), timestamp)
        self._next_repeat = timestamp + self.config.repeat
        if self._message_count >= self.config.max_messages:
            self._next_repeat = None

    def _advance(self, include_equal=True):
        def due(deadline):
            return self._now >= deadline if include_equal else self._now > deadline
        if self._incident == Incident.LEAN_GRACE and due(self._deadline):
            deadline = self._deadline
            self._incident = Incident.NORMAL_WARNING
            self._deadline = deadline + self.config.normal_warning
            self._reason = "Lean episode unresolved at grace expiry; simulated warning."
            self._effect("normal_warning", deadline)
        if self._incident in {Incident.NORMAL_WARNING, Incident.SEVERE_WARNING} and due(self._deadline):
            deadline = self._deadline
            self._deadline = None
            self._incident = Incident.ALERT_ACTIVE
            self._send(deadline)
            self._reason = "Simulated alert intent only; no message was sent."
            # A late clock update emits only the initial intent, never a backlog.
            if self._next_repeat is not None and self._next_repeat <= self._now:
                self._next_repeat = self._now + self.config.repeat
        elif (self._incident == Incident.ALERT_ACTIVE and self._next_repeat is not None
              and due(self._next_repeat) and not self._caregiver):
            self._send(self._now, repeat=True)

    def _mode_priority(self):
        if self._fault:
            self._reason = "Simulated required-component fault; unresolved incident deadlines retained."
        if self._night:
            self._mode = Mode.NIGHT
        elif self._fault:
            self._mode = Mode.FAULT
        elif self._away:
            self._mode = Mode.AWAY
        elif self._caregiver:
            self._mode = Mode.CAREGIVER_PRESENT
        elif self._mode != Mode.ARMED:
            self._mode = Mode.READY

    def tick(self, timestamp):
        self._clock(timestamp)
        if self._last_observation is None or self._now - self._last_observation > self.config.max_gap:
            self._uncertain = True
            self._safe_since = self._safe_last = None
            self._caregiver_candidate = self._caregiver_since = self._caregiver_last = None
        self._mode_priority()
        self._advance()
        return self.snapshot

    def observe(self, evidence: Evidence):
        if not isinstance(evidence, Evidence):
            raise ValueError("observe requires Evidence")
        now = evidence.timestamp
        if (now < self._now or self._last_observation is not None
                and now <= self._last_observation):
            raise ValueError("observations require fresh increasing source time")
        self._clock(now)
        self._advance(include_equal=False)
        was_resolved = self._incident == Incident.RESOLVED
        had_caregiver = self._caregiver
        self._last_observation = now
        self._fault = evidence.fault
        self._uncertain = evidence.fault or not (evidence.subject_valid and evidence.posture != "unknown")
        if evidence.caregiver_departed and self._caregiver:
            self._caregiver = False
            self._caregiver_candidate = self._caregiver_since = self._caregiver_last = None
            self._rearm_required = True
            self._safe_since = self._safe_last = None
            self._mode = Mode.READY
            self._effect("would_restore_audio")
        if evidence.caregiver_valid and (self._caregiver or evidence.subject_valid):
            if (self._caregiver_candidate != evidence.caregiver_id
                    or self._caregiver_last is None
                    or now - self._caregiver_last > self.config.max_gap):
                self._caregiver_candidate = evidence.caregiver_id
                self._caregiver_since = now
            self._caregiver_last = now
            if not self._caregiver and now - self._caregiver_since >= self.config.caregiver_confirm - 1e-9:
                self._caregiver = True
                self._rearm_required = True
                self._mode = Mode.CAREGIVER_PRESENT
                self._effect("would_silence_audio")
                if self._choking:
                    self._choking_silent = True
                    self._stop_choking_repeats("Simulated caregiver confirmed; choking repeats stopped. Manual Cancel/Resolve still required.")
                else:
                    self._resolve("Separate simulated caregiver continuously confirmed.")
        else:
            self._caregiver_candidate = self._caregiver_since = self._caregiver_last = None
        if evidence.paired_exit and (self._caregiver or had_caregiver):
            self._away = True
            self._mode = Mode.AWAY
            if self._choking:
                self._stop_choking_repeats("Supported paired exit; choking remains active until manual Cancel/Resolve.")
            else:
                self._resolve("Previously confirmed caregiver and subject jointly exited in simulation.")
        if evidence.subject_valid:
            self._away = False
        safe = (evidence.calibrated and evidence.subject_valid
                and evidence.posture == "safe" and evidence.safe_confirmed)
        if safe and not self._fault:
            if self._safe_last is None or now - self._safe_last > self.config.max_gap:
                self._safe_since = now
            self._safe_last = now
            # A posture return cannot establish that a manual choking emergency
            # ended. Only manual Cancel/Resolve ends the choking incident.
            if evidence.recovery_confirmed and not self._choking:
                self._resolve("Positive stable recovery evidence confirmed in simulation.")
            if was_resolved:
                self._incident = Incident.NONE
            if not self._night and not self._caregiver:
                if not self._rearm_required or now - self._safe_since >= self.config.rearm - 1e-9:
                    self._rearm_required = False
                    self._mode = Mode.ARMED
                    self._reason = "Simulated calibrated stable safe confirmation; automatic simulation active."
        else:
            self._safe_since = self._safe_last = None
        if not evidence.calibrated and self._mode == Mode.ARMED:
            self._mode = Mode.READY
        self._mode_priority()
        if (self._mode == Mode.ARMED and evidence.calibrated and evidence.subject_valid
                and self._incident != Incident.RESOLVED):
            if evidence.posture == "severe":
                self._begin(severe=True)
            elif evidence.posture == "lean":
                self._begin()
        if not evidence.calibrated and self._incident == Incident.NONE:
            self._reason = "Uncalibrated simulation; no operational thresholds inferred."
        self._advance()
        return self.snapshot

    def command(self, action: str, timestamp):
        if not isinstance(action, str) or action not in {"start", "night", "cancel", "fall", "choking", "reply", "resolve"}:
            raise ValueError("unsupported simulation command")
        self._clock(timestamp)
        self._advance(include_equal=False)
        if action == "night":
            self._night = True
            self._safe_since = self._safe_last = None
            self._reason = "Deliberate simulated Night; existing incident retained."
        elif action == "start":
            self._night = False
            self._mode = Mode.READY
            self._reason = "Start requested; fresh calibrated safe confirmation required."
        elif action in {"cancel", "resolve"}:
            self._resolve("Incident explicitly resolved in simulation.")
        elif action == "reply":
            if self._choking:
                self._stop_choking_repeats("Valid simulated caregiver reply; choking repeats stopped. Manual Cancel/Resolve still required.")
            else:
                self._resolve("Incident acknowledged by a valid simulated caregiver reply.")
        elif action == "fall":
            if self._choking:
                self._reason = "Manual fall request cannot resolve an active choking incident."
            else:
                self._begin(severe=True)
                if self._caregiver:
                    self._effect("manual_fall_handled_by_caregiver")
                    self._resolve("Manual fall request handled by already confirmed caregiver; warning suppressed.")
        elif action == "choking":
            if not self._choking and self._last_choking_command != self._now:
                self._last_choking_command = self._now
                self._message_count = 0
                self._choking = True
                self._choking_silent = self._caregiver
                self._incident = Incident.ALERT_ACTIVE
                self._deadline = None
                self._send(self._now)
                self._reason = "Immediate simulated choking intent; no message or audio action."
                if self._caregiver:
                    self._stop_choking_repeats("Immediate choking intent with a confirmed caregiver; repeats stopped. Manual Cancel/Resolve still required.")
        self._mode_priority()
        self._advance()
        return self.snapshot
