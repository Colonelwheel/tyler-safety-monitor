"""Observational head association for the foundation benchmark.

These tracks are candidates, never confirmed identities or caregiver presence.
Nearest-position matching cannot resolve overlapping people or long occlusions;
uncertainty resets continuity and must not suppress a future safety warning.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import hypot, isfinite
from typing import Sequence


def _point(point: Sequence[float], name: str) -> tuple[float, float]:
    if len(point) != 2:
        raise ValueError(f"{name} must contain two coordinates")
    values = tuple(float(v) for v in point)
    if any(not isfinite(v) or not 0 <= v <= 1 for v in values):
        raise ValueError(f"{name} must be finite normalized coordinates")
    return values


def _landmark_scores(scores, landmarks) -> tuple[tuple[float, float], ...]:
    """Validate optional paired visibility/presence metadata, in landmark order."""
    values = tuple(tuple(float(value) for value in pair) for pair in scores)
    if values and len(values) != len(landmarks):
        raise ValueError("landmark scores must match the landmark count")
    if any(len(pair) != 2 or any(not isfinite(value) or not 0 <= value <= 1
                                 for value in pair) for pair in values):
        raise ValueError("landmark scores must contain finite [0, 1] visibility/presence pairs")
    return values


@dataclass(frozen=True)
class PoseObservation:
    head: tuple[float, float]
    shoulders: tuple[float, float] | None
    confidence: float
    landmarks: tuple[tuple[float, float, float], ...] = ()
    landmark_scores: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "head", _point(self.head, "head"))
        if self.shoulders is not None:
            object.__setattr__(self, "shoulders", _point(self.shoulders, "shoulders"))
        confidence = float(self.confidence)
        if not isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("confidence must lie inside [0, 1]")
        object.__setattr__(self, "confidence", confidence)
        landmarks = tuple(tuple(float(v) for v in point) for point in self.landmarks)
        if any(len(point) != 3 or any(not isfinite(v) for v in point) for point in landmarks):
            raise ValueError("landmarks must contain finite x, y, z triples")
        object.__setattr__(self, "landmarks", landmarks)
        object.__setattr__(self, "landmark_scores", _landmark_scores(self.landmark_scores, landmarks))


@dataclass(frozen=True)
class Track:
    id: int
    head: tuple[float, float]
    shoulders: tuple[float, float] | None
    confidence: float
    last_seen: float
    continuous_since: float
    landmarks: tuple[tuple[float, float, float], ...] = ()
    label: str = "person candidate"
    identity_uncertain: bool = False
    landmark_scores: tuple[tuple[float, float], ...] = ()
    uncertainty_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "landmark_scores", _landmark_scores(self.landmark_scores, self.landmarks))


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


def _assign_heads(previous, observations, max_distance):
    """Maximum-cardinality, then minimum-distance rectangular assignment.

    Real track columns plus one new-ID column per observation allow every row
    to be assigned. New-ID penalties dominate the sum of all legal distances.
    Hungarian potentials keep this polynomial, including bounded replay batches.
    """
    if not observations or not previous:
        return {}
    ids = sorted(previous)
    count = len(observations)
    # Normalized head coordinates bound every distance by sqrt(2).
    # Do not multiply an arbitrary, valid finite max_distance into infinity.
    penalty = (count + 1) * 3.0
    forbidden = (count + 1) * penalty
    costs = []
    for obs in observations:
        distances = [_distance(previous[id_].head, obs.head) for id_ in ids]
        costs.append([distance if distance <= max_distance else forbidden
                      for distance in distances] + [penalty] * count)
    columns = len(costs[0])
    row_potential = [0.0] * (count + 1)
    col_potential = [0.0] * (columns + 1)
    owner = [0] * (columns + 1)
    predecessor = [0] * (columns + 1)
    for row in range(1, count + 1):
        owner[0] = row
        column = 0
        remaining = [float("inf")] * (columns + 1)
        used = [False] * (columns + 1)
        while True:
            used[column] = True
            active = owner[column]
            delta = float("inf")
            next_column = 0
            for candidate in range(1, columns + 1):
                if used[candidate]:
                    continue
                cost = costs[active - 1][candidate - 1] - row_potential[active] - col_potential[candidate]
                if cost < remaining[candidate]:
                    remaining[candidate] = cost
                    predecessor[candidate] = column
                if remaining[candidate] < delta:
                    delta, next_column = remaining[candidate], candidate
            for candidate in range(columns + 1):
                if used[candidate]:
                    row_potential[owner[candidate]] += delta
                    col_potential[candidate] -= delta
                else:
                    remaining[candidate] -= delta
            column = next_column
            if owner[column] == 0:
                break
        while column:
            prior = predecessor[column]
            owner[column] = owner[prior]
            column = prior
    return {owner[column] - 1: ids[column - 1]
            for column in range(1, len(ids) + 1)
            if owner[column] and costs[owner[column] - 1][column - 1] < penalty}


@dataclass(frozen=True)
class TrackingDiagnostics:
    """Counts only, for the last ten seconds of accepted observation batches."""
    received: int = 0
    kept: int = 0
    suppressed: int = 0
    duplicate_uncertain: int = 0
    ambiguous_matches: int = 0
    frames: int = 0
    missing_frames: int = 0
    duplicate_frames: int = 0
    ambiguous_frames: int = 0
    uncertain_frames: int = 0

    def summary(self) -> str:
        return (f"Tracking: heads {self.received} / kept {self.kept} / duplicates {self.suppressed}; "
                f"uncertain: duplicate {self.duplicate_uncertain}, match {self.ambiguous_matches}. "
                f"Last 10s ({self.frames} frames): no head {self.missing_frames}, "
                f"duplicates {self.duplicate_frames}, ambiguous matches {self.ambiguous_frames}.")


class PersonTracker:
    """Bounded, one-to-one head association with explicit continuity breaks.

    update returns only tracks visible in the current observation batch. Missing
    tracks are retained privately for ttl_seconds, and reacquisition resets their
    continuous_since time. Exact timestamp repeats and regressions are rejected
    without mutating tracker state.
    """

    def __init__(
        self, max_distance: float = 0.15, ttl_seconds: float = 1.0,
        duplicate_distance: float = 0.035, ambiguity_margin: float = 0.025,
    ) -> None:
        for name, value in (("max_distance", max_distance), ("ttl_seconds", ttl_seconds),
                            ("duplicate_distance", duplicate_distance), ("ambiguity_margin", ambiguity_margin)):
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        self.max_distance = max_distance
        self.ttl_seconds = ttl_seconds
        self.duplicate_distance = duplicate_distance
        self.ambiguity_margin = ambiguity_margin
        self._tracks: dict[int, Track] = {}
        self._visible: set[int] = set()
        self._next_id = 1
        self._timestamp: float | None = None
        self._diagnostic_frames = deque(maxlen=1024)
        self.diagnostics = TrackingDiagnostics()

    def update(self, observations: Sequence[PoseObservation], timestamp: float) -> list[Track]:
        timestamp = float(timestamp)
        if not isfinite(timestamp) or timestamp < 0:
            raise ValueError("timestamp must be finite monotonic seconds")
        if self._timestamp is not None and timestamp <= self._timestamp:
            raise ValueError("observation timestamp must increase strictly")
        if any(not isinstance(observation, PoseObservation) for observation in observations):
            raise ValueError("observations must contain PoseObservation values")

        # Confidence-first suppression stops duplicate detections from creating
        # a spurious second candidate. Coordinate sorting breaks order ties.
        ordered = sorted(observations, key=lambda obs: (-obs.confidence, obs.head))
        unique: list[PoseObservation] = []
        duplicate_indices: set[int] = set()
        for obs in ordered:
            near = [i for i, other in enumerate(unique)
                    if _distance(obs.head, other.head) <= self.duplicate_distance]
            if near:
                duplicate_indices.update(near)
            else:
                unique.append(obs)

        previous = {id_: track for id_, track in self._tracks.items()
                    if timestamp - track.last_seen <= self.ttl_seconds}
        edges = sorted(
            (distance, id_, index)
            for id_, track in previous.items()
            for index, obs in enumerate(unique)
            if (distance := _distance(track.head, obs.head)) <= self.max_distance
        )
        ambiguous: set[int] = set()
        for index in range(len(unique)):
            distances = sorted(distance for distance, _, i in edges if i == index)
            if len(distances) > 1 and distances[1] - distances[0] <= self.ambiguity_margin:
                ambiguous.add(index)
        for id_ in previous:
            candidates = sorted((distance, index) for distance, id2, index in edges if id2 == id_)
            if len(candidates) > 1 and candidates[1][0] - candidates[0][0] <= self.ambiguity_margin:
                ambiguous.update(index for _, index in candidates)

        matches = _assign_heads(previous, unique, self.max_distance)

        visible: list[Track] = []
        for index, obs in enumerate(unique):
            id_ = matches.get(index)
            old = previous.get(id_) if id_ is not None else None
            if id_ is None:
                id_ = self._next_id
                self._next_id += 1
            uncertain = index in ambiguous or index in duplicate_indices
            continuous_since = (
                old.continuous_since
                if old is not None and id_ in self._visible
                and not uncertain and not old.identity_uncertain
                else timestamp
            )
            track = Track(id_, obs.head, obs.shoulders, obs.confidence, timestamp,
                          continuous_since, obs.landmarks, identity_uncertain=uncertain,
                          landmark_scores=obs.landmark_scores,
                          uncertainty_reasons=tuple(reason for applies, reason in (
                              (index in duplicate_indices, "duplicate heads"),
                              (index in ambiguous, "competing matches")) if applies))
            previous[id_] = track
            visible.append(track)
        self._tracks = previous
        self._visible = {track.id for track in visible}
        self._timestamp = timestamp
        self._diagnostic_frames.append((timestamp, not unique, bool(duplicate_indices),
                                        bool(ambiguous), any(t.identity_uncertain for t in visible)))
        while self._diagnostic_frames and timestamp - self._diagnostic_frames[0][0] > 10:
            self._diagnostic_frames.popleft()
        window = self._diagnostic_frames
        self.diagnostics = TrackingDiagnostics(
            len(observations), len(unique), len(observations) - len(unique),
            len(duplicate_indices), len(ambiguous), len(window),
            sum(frame[1] for frame in window), sum(frame[2] for frame in window),
            sum(frame[3] for frame in window), sum(frame[4] for frame in window))
        return sorted(visible, key=lambda track: track.id)
