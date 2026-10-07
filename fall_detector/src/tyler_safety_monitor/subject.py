"""Session-local selected-subject association, never biometric identity or safety."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite
from typing import Sequence

from .tracking import Track


@dataclass(frozen=True)
class SubjectState:
    status: str = "unselected"
    track_id: int | None = None
    selected: bool = False
    selection_epoch: int = 0
    reason: str = "Select a currently visible candidate."


def _seconds(value):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or value < 0):
        raise ValueError("timestamp must be finite nonnegative seconds")
    try:
        if not isfinite(value):
            raise ValueError("timestamp must be finite nonnegative seconds")
        return float(value)
    except OverflowError:
        raise ValueError("timestamp must be finite nonnegative seconds") from None


def _current_tracks(tracks, timestamp):
    tracks = tuple(tracks)
    ids = set()
    for track in tracks:
        if (not isinstance(track, Track) or isinstance(track.id, bool)
                or not isinstance(track.id, int) or track.id < 1 or track.id in ids):
            raise ValueError("current candidates require distinct positive track IDs")
        ids.add(track.id)
        try:
            valid_head = (len(track.head) == 2
                          and all(isfinite(v) and 0 <= v <= 1 for v in track.head))
            valid_time = (isfinite(track.last_seen)
                          and abs(track.last_seen - timestamp) <= 1e-9)
            valid_score = isfinite(track.confidence) and 0 <= track.confidence <= 1
        except (TypeError, ValueError, OverflowError):
            raise ValueError("invalid current candidate") from None
        if not valid_head or not valid_time or not valid_score:
            raise ValueError("candidate must be valid and observed at this timestamp")
    return tracks


def _distance(a, b):
    return hypot(a[0] - b[0], a[1] - b[1])


class SubjectSlot:
    """Persistent explicit designation with a conservative position-only bridge.

    New IDs require a sole nearby clear candidate over several fresh batches.
    Missing or uncertain observations never become capture eligible. Parameters
    describe diagnostic association, not an approved danger or identity threshold.
    """
    def __init__(self, *, max_gap=3., reattach_distance=.075,
                 max_distance=.15, confirm_seconds=.5, confirm_observations=3,
                 consecutive_gap=.4, fresh_seconds=.4):
        for name, value in (("max_gap", max_gap), ("reattach_distance", reattach_distance),
                            ("max_distance", max_distance), ("confirm_seconds", confirm_seconds),
                            ("consecutive_gap", consecutive_gap), ("fresh_seconds", fresh_seconds)):
            try:
                valid = (not isinstance(value, bool) and isinstance(value, (int, float))
                         and isfinite(value) and value > 0)
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError(f"{name} must be finite and positive")
        if (isinstance(confirm_observations, bool)
                or not isinstance(confirm_observations, int) or confirm_observations < 3):
            raise ValueError("confirm_observations must be at least three")
        self.max_gap = max_gap
        self.reattach_distance = reattach_distance
        self.max_distance = max_distance
        self.confirm_seconds = confirm_seconds
        self.confirm_observations = confirm_observations
        self.consecutive_gap = consecutive_gap
        self.fresh_seconds = fresh_seconds
        self._state = SubjectState()
        self._last_update = None
        self._bound_id = None
        self._anchor = None
        self._confirmed_at = None
        self._current = None
        self._manual = False
        self._manual_reason = ""
        self._prospective = None  # ID, first time, last time, number of fresh batches
        self._last_other_at = None  # One bounded timestamp, never a growing ID history.

    @property
    def state(self):
        return self._state

    def _unqualified(self, status, reason):
        self._current = None
        self._state = SubjectState(status, None, self._state.selected,
                                   self._state.selection_epoch, reason)
        return self._state

    def _latch(self, reason):
        self._manual = True
        self._manual_reason = reason
        self._prospective = None
        return self._unqualified("reselection_required", reason)

    def _qualify(self, track, timestamp):
        self._bound_id = track.id
        self._anchor = track.head
        self._confirmed_at = timestamp
        self._current = track
        self._prospective = None
        self._state = SubjectState("visible", track.id, True,
                                   self._state.selection_epoch,
                                   "Current clear observation of the selected subject.")
        return self._state

    def select(self, current_tracks: Sequence[Track], track_id: int, timestamp):
        """Explicitly designate a fresh unambiguous candidate; invalid input is atomic."""
        timestamp = _seconds(timestamp)
        if self._last_update is not None and timestamp < self._last_update:
            raise ValueError("selection cannot use an older observation")
        tracks = _current_tracks(current_tracks, timestamp)
        if isinstance(track_id, bool) or not isinstance(track_id, int):
            raise ValueError("select a current candidate ID")
        candidate = next((track for track in tracks if track.id == track_id), None)
        if candidate is None or candidate.identity_uncertain:
            raise ValueError("select a currently visible unambiguous candidate")
        if any(track.id != candidate.id
               and _distance(track.head, candidate.head) <= self.max_distance
               for track in tracks):
            raise ValueError("nearby competing candidates prevent selection")
        self._state = SubjectState(selected=True,
                                   selection_epoch=self._state.selection_epoch + 1)
        self._last_update = timestamp
        self._manual = False
        self._manual_reason = ""
        self._last_other_at = timestamp if any(track.id != candidate.id for track in tracks) else None
        return self._qualify(candidate, timestamp)

    def reset(self):
        """Invalidate designation, including every capture holding its old epoch."""
        self._state = SubjectState(selection_epoch=self._state.selection_epoch + 1)
        self._last_update = None
        self._bound_id = self._anchor = self._confirmed_at = self._current = None
        self._manual = False
        self._manual_reason = ""
        self._prospective = None
        self._last_other_at = None
        return self._state

    def update(self, current_tracks: Sequence[Track], timestamp):
        try:
            timestamp = _seconds(timestamp)
        except ValueError:
            self._prospective = None
            return self._unqualified("invalid_observation", "Observation timestamp is invalid.")
        if self._last_update is not None and timestamp <= self._last_update:
            self._prospective = None
            return self._unqualified("invalid_observation", "A fresh increasing observation is required.")
        self._last_update = timestamp
        if not self._state.selected:
            return self._unqualified("unselected", "Select a currently visible candidate.")
        if self._manual:
            return self._unqualified("reselection_required", self._manual_reason)
        if timestamp - self._confirmed_at > self.max_gap:
            return self._latch("Absence exceeded the supported gap; select the subject again.")
        try:
            tracks = _current_tracks(current_tracks, timestamp)
        except (TypeError, ValueError):
            self._prospective = None
            return self._unqualified("invalid_observation", "Candidates are not valid current observations.")
        bound = next((track for track in tracks if track.id == self._bound_id), None)
        if bound is not None and any(track.id != bound.id for track in tracks):
            self._last_other_at = timestamp
        recent_other = (self._last_other_at is not None
                        and timestamp - self._last_other_at <= self.max_gap)
        if recent_other and (bound is None
                             or timestamp - self._confirmed_at > self.consecutive_gap):
            return self._latch("Another candidate was recently visible before this gap; select again.")
        if bound is not None:
            if bound.identity_uncertain:
                return self._latch("Selected candidate is uncertain; select again when clear.")
            if _distance(bound.head, self._anchor) > self.max_distance:
                return self._latch("Selected candidate moved beyond association support; select again.")
            if any(track.id != bound.id
                   and (_distance(track.head, bound.head) <= self.max_distance
                        or _distance(track.head, self._anchor) <= self.max_distance)
                   for track in tracks):
                return self._latch("Nearby competing candidates require manual selection.")
            return self._qualify(bound, timestamp)
        if not tracks:
            if (self._prospective is not None
                    and timestamp - self._prospective[2] > self.consecutive_gap):
                self._prospective = None
            return self._unqualified("missing", "Selected subject is missing; no current observation.")
        if len(tracks) != 1:
            return self._latch("Other candidates appeared while the subject was missing; select again.")
        candidate = tracks[0]
        if candidate.identity_uncertain:
            return self._latch("A returning candidate is uncertain; select again when clear.")
        if _distance(candidate.head, self._anchor) > self.reattach_distance:
            return self._latch("A different-location candidate appeared during absence; select again.")
        prior = self._prospective
        if (prior is None or prior[0] != candidate.id
                or timestamp - prior[2] > self.consecutive_gap):
            self._prospective = (candidate.id, timestamp, timestamp, 1)
        else:
            self._prospective = (candidate.id, prior[1], timestamp, prior[3] + 1)
        _, began, _, count = self._prospective
        if (timestamp - began >= self.confirm_seconds - 1e-9
                and count >= self.confirm_observations):
            return self._qualify(candidate, timestamp)
        return self._unqualified("confirming", "Confirming a nearby new P ID; capture is unavailable.")

    def eligible(self, current_tracks: Sequence[Track], timestamp) -> Track | None:
        """Read-only gate against stale, changed, uncertain or missing observations."""
        try:
            timestamp = _seconds(timestamp)
        except ValueError:
            return None
        current = self._current
        if (current is None or self._state.status != "visible" or self._manual
                or timestamp < current.last_seen
                or timestamp - current.last_seen > self.fresh_seconds):
            return None
        try:
            tracks = _current_tracks(current_tracks, current.last_seen)
        except (TypeError, ValueError):
            return None
        candidate = next((track for track in tracks if track.id == current.id), None)
        if candidate != current or candidate.identity_uncertain:
            return None
        if any(track.id != candidate.id
               and _distance(track.head, candidate.head) <= self.max_distance
               for track in tracks):
            return None
        return candidate
