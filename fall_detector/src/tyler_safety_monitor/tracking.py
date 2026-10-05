"""Observational head association for the foundation benchmark.

These tracks are candidates, never confirmed identities or caregiver presence.
Nearest-position matching cannot resolve overlapping people or long occlusions;
uncertainty resets continuity and must not suppress a future safety warning.
"""

from __future__ import annotations

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

    def __post_init__(self) -> None:
        object.__setattr__(self, "landmark_scores", _landmark_scores(self.landmark_scores, self.landmarks))


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return hypot(a[0] - b[0], a[1] - b[1])


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
        ambiguous: set[int] = set(duplicate_indices)
        for index in range(len(unique)):
            distances = sorted(distance for distance, _, i in edges if i == index)
            if len(distances) > 1 and distances[1] - distances[0] <= self.ambiguity_margin:
                ambiguous.add(index)
        for id_ in previous:
            candidates = sorted((distance, index) for distance, id2, index in edges if id2 == id_)
            if len(candidates) > 1 and candidates[1][0] - candidates[0][0] <= self.ambiguity_margin:
                ambiguous.update(index for _, index in candidates)

        matches: dict[int, int] = {}
        assigned_ids: set[int] = set()
        for _, id_, index in edges:
            if id_ not in assigned_ids and index not in matches:
                matches[index] = id_
                assigned_ids.add(id_)

        visible: list[Track] = []
        for index, obs in enumerate(unique):
            id_ = matches.get(index)
            old = previous.get(id_) if id_ is not None else None
            if id_ is None:
                id_ = self._next_id
                self._next_id += 1
            uncertain = index in ambiguous
            continuous_since = (
                old.continuous_since
                if old is not None and id_ in self._visible
                and not uncertain and not old.identity_uncertain
                else timestamp
            )
            track = Track(id_, obs.head, obs.shoulders, obs.confidence, timestamp,
                          continuous_since, obs.landmarks, identity_uncertain=uncertain,
                          landmark_scores=obs.landmark_scores)
            previous[id_] = track
            visible.append(track)
        self._tracks = previous
        self._visible = {track.id for track in visible}
        self._timestamp = timestamp
        return sorted(visible, key=lambda track: track.id)
