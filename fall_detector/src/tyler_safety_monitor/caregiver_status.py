"""Live second-candidate continuity diagnostics, never identity or suppression.

Only fresh Full-pose observations support the counter. No file writes, adapters,
model fusion or caregiver safety decisions occur here. Policy values are existing
diagnostic association allowances, not approved operational thresholds.
"""
from dataclasses import dataclass
from math import hypot, isfinite

from .tracking import Track


def _seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Diagnostic time must be finite nonnegative seconds")
    try:
        value = float(value)
    except OverflowError:
        raise ValueError("Diagnostic time must be finite nonnegative seconds") from None
    if not isfinite(value) or value < 0:
        raise ValueError("Diagnostic time must be finite nonnegative seconds")
    return value


@dataclass(frozen=True)
class CaregiverStatus:
    status: str = "unselected"
    elapsed: float = 0.
    candidate_id: int | None = None
    reset_reason: str = "Select Tyler before checking a second person."
    resets: int = 0


class CaregiverStatusCounter:
    def __init__(self, confirm_seconds=2., max_gap=.4, separation=.15):
        self.confirm_seconds = _seconds(confirm_seconds)
        self.max_gap = _seconds(max_gap)
        self.separation = _seconds(separation)
        if min(self.confirm_seconds, self.max_gap, self.separation) <= 0:
            raise ValueError("Diagnostic continuity parameters must be positive")
        self._snapshot = CaregiverStatus()
        self._began = None
        self._last_batch = None
        self._last_tick = None
        self._subject_id = None
        self._last_head = None

    @property
    def snapshot(self):
        return self._snapshot

    def _break(self, reason, status="unavailable"):
        resets = self._snapshot.resets + int(self._began is not None)
        self._began = self._last_head = None
        self._snapshot = CaregiverStatus(status, 0., None, reason, resets)
        return self._snapshot

    def reset(self, reason="Camera or scene changed; continuity cleared."):
        result = self._break(reason)
        self._last_batch = self._last_tick = self._subject_id = None
        return result

    def tick(self, timestamp):
        timestamp = _seconds(timestamp)
        if self._last_tick is not None and timestamp < self._last_tick:
            raise ValueError("Diagnostic refresh time cannot regress")
        self._last_tick = timestamp
        if (self._began is not None and self._last_batch is not None
                and timestamp - self._last_batch > self.max_gap):
            self._break("Fresh pose results stopped; confirmation restarted.")
        return self._snapshot

    def update(self, tracks, subject_id, timestamp):
        timestamp = _seconds(timestamp)
        if self._last_batch is not None and timestamp <= self._last_batch:
            raise ValueError("Diagnostic observation time must increase")
        tracks = tuple(tracks)
        ids = set()
        for track in tracks:
            if not isinstance(track, Track) or type(track.id) is not int or track.id < 1 or track.id in ids:
                raise ValueError("Distinct positive current candidate IDs required")
            ids.add(track.id)
            if (not all(isfinite(v) and 0 <= v <= 1 for v in track.head)
                    or not isfinite(track.last_seen) or abs(track.last_seen - timestamp) > self.max_gap):
                raise ValueError("Candidates must have valid fresh Full-pose evidence")
        if subject_id is not None and (type(subject_id) is not int or subject_id < 1):
            raise ValueError("Tyler designation must be a current candidate ID")
        previous_batch = self._last_batch
        self._last_batch = timestamp
        if self._last_tick is not None and self._last_tick - timestamp > self.max_gap:
            return self._break("Pose result arrived stale; confirmation restarted.")
        if subject_id is None:
            self._subject_id = None
            return self._break("Tyler is unselected or not reliably located; counter unavailable.")
        if self._subject_id is not None and subject_id != self._subject_id:
            self._break("Tyler association changed; confirmation restarted.")
        self._subject_id = subject_id
        subject = next((track for track in tracks if track.id == subject_id), None)
        if subject is None or subject.identity_uncertain:
            return self._break("Tyler is missing or ambiguous; confirmation restarted.")
        others = [track for track in tracks if track.id != subject_id]
        if not others:
            return self._break("No current second person detected; confirmation restarted.", "none")
        if len(others) != 1 or others[0].identity_uncertain:
            return self._break("Second-person association is ambiguous; confirmation restarted.", "ambiguous")
        candidate = others[0]
        if hypot(candidate.head[0] - subject.head[0], candidate.head[1] - subject.head[1]) <= self.separation:
            return self._break("Heads are too close to distinguish reliably; confirmation restarted.", "ambiguous")
        if self._began is not None:
            if candidate.id != self._snapshot.candidate_id:
                self._break("Second-person candidate ID changed; confirmation restarted.")
            elif previous_batch is None or timestamp - previous_batch > self.max_gap:
                self._break("Observation gap exceeded freshness allowance; confirmation restarted.")
            elif self._last_head is not None and hypot(candidate.head[0] - self._last_head[0],
                                                      candidate.head[1] - self._last_head[1]) > self.separation:
                self._break("Second-person movement exceeded association support; confirmation restarted.")
        if self._began is None:
            self._began = timestamp
        elapsed = min(self.confirm_seconds, timestamp - self._began)
        status = "confirmed" if elapsed >= self.confirm_seconds - 1e-9 else "confirming"
        self._last_head = candidate.head
        self._snapshot = CaregiverStatus(status, elapsed, candidate.id,
                                         self._snapshot.reset_reason, self._snapshot.resets)
        return self._snapshot
