"""Explainable base-speed scoring logic.

This module is a privacy-safe, dependency-free reconstruction of the core
ideas used in the private project. It intentionally contains no collector,
credentials, local paths, or collected race data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from statistics import pstdev
from typing import Literal, Sequence

PaceClass = Literal["FAST", "STANDARD", "SLOW", "STANDARD_ESTIMATED"]
EvaluationStatus = Literal["MEASURED", "ESTIMATED", "NOT_TESTED"]

PACE_FAST_DELTA = 0.5
PACE_SLOW_DELTA = -0.5
FRONT_GROUP_RATIO = 0.30
TOP_RUN_WEIGHTS = (0.35, 0.25, 0.18, 0.13, 0.09)


@dataclass(frozen=True)
class PaceAssessment:
    """Result of comparing a race's early pace with a baseline."""

    pace_class: PaceClass
    delta_seconds: float | None
    confidence: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RunEvaluation:
    """One past race evaluation used for aggregation."""

    label: str
    score: float | None
    confidence: float
    recency_rank: int
    status: EvaluationStatus

    @property
    def evidence_strength(self) -> float:
        if self.score is None:
            return 0.0
        return self.score * self.confidence

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["evidence_strength"] = round(self.evidence_strength, 4)
        return result


@dataclass(frozen=True)
class AggregateResult:
    """Aggregated base-speed estimate and its uncertainty."""

    central_score: float | None
    lower_score: float | None
    upper_score: float | None
    confidence: float
    runs_used: int
    stability_score: float | None
    status: EvaluationStatus
    selected_runs: tuple[RunEvaluation, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "central_score": self.central_score,
            "lower_score": self.lower_score,
            "upper_score": self.upper_score,
            "confidence": self.confidence,
            "runs_used": self.runs_used,
            "stability_score": self.stability_score,
            "status": self.status,
            "selected_runs": [item.to_dict() for item in self.selected_runs],
        }


def clamp(value: float, lower: float, upper: float) -> float:
    """Clamp a numeric value to an inclusive range."""

    return max(lower, min(upper, value))


def round_score(value: float) -> float:
    """Round and constrain an ability score to the 0-10 range."""

    return round(clamp(float(value), 0.0, 10.0), 3)


def classify_pace(
    current_early_time: float | None,
    baseline_early_time: float | None,
    baseline_confidence: float,
) -> PaceAssessment:
    """Classify the first 600 m against a comparable-race baseline.

    A positive delta means the current race was faster than the baseline.
    """

    confidence = clamp(float(baseline_confidence), 0.0, 1.0)

    if current_early_time is None or baseline_early_time is None:
        return PaceAssessment(
            pace_class="STANDARD_ESTIMATED",
            delta_seconds=None,
            confidence=confidence,
        )

    delta = round(float(baseline_early_time) - float(current_early_time), 3)

    if delta >= PACE_FAST_DELTA:
        pace_class: PaceClass = "FAST"
    elif delta <= PACE_SLOW_DELTA:
        pace_class = "SLOW"
    else:
        pace_class = "STANDARD"

    return PaceAssessment(
        pace_class=pace_class,
        delta_seconds=delta,
        confidence=confidence,
    )


def distance_transfer_factor(source_distance: int, target_distance: int) -> float:
    """Reduce overvaluation when transferring a longer-race result.

    A result at a shorter or equal distance keeps full weight. For every
    additional 200 m in the source race, the factor falls by 0.1, down to 0.5.
    """

    if source_distance <= 0 or target_distance <= 0:
        raise ValueError("Distances must be positive integers.")

    if source_distance <= target_distance:
        return 1.0

    distance_gap = source_distance - target_distance
    steps = math.ceil(distance_gap / 200)
    return round(max(0.5, 1.0 - 0.1 * steps), 3)


def score_tracking_speed(
    pace_class: PaceClass,
    early_position: int,
    field_size: int,
    transfer_factor: float = 1.0,
) -> float:
    """Score the ability to obtain a forward position under pace pressure."""

    if field_size <= 0:
        raise ValueError("field_size must be positive.")
    if not 1 <= early_position <= field_size:
        raise ValueError("early_position must be within the field.")

    factor = clamp(float(transfer_factor), 0.0, 1.0)
    position_ratio = early_position / field_size

    if position_ratio <= 0.30:
        tier = {
            "FAST": 4.0,
            "STANDARD": 3.4,
            "STANDARD_ESTIMATED": 3.2,
            "SLOW": 2.6,
        }
    elif position_ratio <= 0.50:
        tier = {
            "FAST": 3.2,
            "STANDARD": 2.6,
            "STANDARD_ESTIMATED": 2.4,
            "SLOW": 1.8,
        }
    elif position_ratio <= 0.70:
        tier = {
            "FAST": 2.2,
            "STANDARD": 1.7,
            "STANDARD_ESTIMATED": 1.5,
            "SLOW": 1.0,
        }
    else:
        tier = {
            "FAST": 1.2,
            "STANDARD": 0.8,
            "STANDARD_ESTIMATED": 0.7,
            "SLOW": 0.4,
        }

    return round(tier[pace_class] * factor, 3)


def score_position_maintenance(
    early_position: int,
    late_position: int,
    field_size: int,
) -> float:
    """Score whether a horse maintained position after the early phase.

    The public edition keeps this function deliberately small and explicit so
    that reviewers can inspect the assumptions without private race data.
    """

    if field_size <= 0:
        raise ValueError("field_size must be positive.")
    if not 1 <= early_position <= field_size:
        raise ValueError("early_position must be within the field.")
    if not 1 <= late_position <= field_size:
        raise ValueError("late_position must be within the field.")

    position_change = late_position - early_position
    front_limit = max(1, math.ceil(field_size * FRONT_GROUP_RATIO))
    half_limit = max(front_limit, math.ceil(field_size * 0.50))
    seventy_limit = max(half_limit, math.ceil(field_size * 0.70))

    if late_position <= front_limit and position_change <= 1:
        return 2.5
    if late_position <= half_limit and position_change <= 1:
        return 2.1
    if position_change <= 0:
        return 1.8
    if late_position <= seventy_limit and position_change <= 2:
        return 1.1
    return 0.3


def apply_position_threshold_correction(
    base_threshold: float,
    position_ratio: float | None,
) -> float:
    """Widen the tolerated deceleration for horses carrying more early load."""

    if base_threshold < 0:
        raise ValueError("base_threshold must be non-negative.")

    if position_ratio is None:
        correction = 0.0
    elif not 0.0 < position_ratio <= 1.0:
        raise ValueError("position_ratio must be within (0, 1].")
    elif position_ratio <= 0.10:
        correction = 0.3
    elif position_ratio <= 0.30:
        correction = 0.2
    elif position_ratio <= 0.50:
        correction = 0.1
    else:
        correction = 0.0

    return round(float(base_threshold) + correction, 3)


def score_non_deceleration(
    max_deceleration: float,
    base_threshold: float,
    position_ratio: float | None,
) -> float:
    """Score late-race deceleration against a track-aware threshold."""

    if max_deceleration < 0:
        raise ValueError("max_deceleration must be non-negative.")

    threshold = apply_position_threshold_correction(
        base_threshold=base_threshold,
        position_ratio=position_ratio,
    )

    if max_deceleration < threshold - 0.2:
        return 2.5
    if max_deceleration < threshold:
        return 2.1
    if max_deceleration < threshold + 0.3:
        return 0.9
    return 0.2


def aggregate_horse_scores(
    evaluations: Sequence[RunEvaluation],
) -> AggregateResult:
    """Aggregate up to five evidence-rich past races.

    Runs are ordered by score × confidence, then score, then recency. The
    selected runs receive 35%, 25%, 18%, 13%, and 9% weights. Uncertainty grows
    when confidence or score stability is low.
    """

    usable = [item for item in evaluations if item.score is not None]
    usable.sort(
        key=lambda item: (
            item.evidence_strength,
            float(item.score or 0.0),
            -item.recency_rank,
        ),
        reverse=True,
    )
    selected = tuple(usable[: len(TOP_RUN_WEIGHTS)])

    if not selected:
        return AggregateResult(
            central_score=None,
            lower_score=None,
            upper_score=None,
            confidence=0.0,
            runs_used=0,
            stability_score=None,
            status="NOT_TESTED",
            selected_runs=(),
        )

    weights = TOP_RUN_WEIGHTS[: len(selected)]
    weight_sum = sum(weights)

    central_score = sum(
        float(item.score) * weight
        for item, weight in zip(selected, weights, strict=True)
    ) / weight_sum

    base_confidence = sum(
        clamp(item.confidence, 0.0, 1.0) * weight
        for item, weight in zip(selected, weights, strict=True)
    ) / weight_sum

    count_factor = {
        1: 0.45,
        2: 0.65,
        3: 0.80,
        4: 0.90,
        5: 1.00,
    }[len(selected)]
    confidence = clamp(base_confidence * count_factor, 0.0, 1.0)

    selected_scores = [float(item.score) for item in selected]
    if len(selected_scores) == 1:
        stability_score = 0.5
    else:
        stability_score = clamp(1.0 - pstdev(selected_scores) / 3.0, 0.0, 1.0)

    uncertainty = (1.0 - confidence) * 1.5 + (1.0 - stability_score) * 0.8
    all_measured = all(item.status == "MEASURED" for item in selected)
    status: EvaluationStatus = (
        "MEASURED" if all_measured and confidence >= 0.70 else "ESTIMATED"
    )

    return AggregateResult(
        central_score=round_score(central_score),
        lower_score=round_score(central_score - uncertainty),
        upper_score=round_score(central_score + uncertainty),
        confidence=round(confidence, 3),
        runs_used=len(selected),
        stability_score=round(stability_score, 3),
        status=status,
        selected_runs=selected,
    )
