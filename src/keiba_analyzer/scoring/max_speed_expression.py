"""Two-layer maximum-speed model for the public portfolio edition.

The private application keeps a horse's observed absolute peak separate from
the speed that is likely to be expressed in the target race.  This module is a
small, dependency-free reconstruction of that contract.  It contains no
collected data and no production coefficients.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))


@dataclass(frozen=True)
class ReserveObservation:
    """A measured terminal speed paired with remaining energy before L3."""

    remaining_energy: float
    speed_mps: float
    confidence: float = 1.0


@dataclass(frozen=True)
class MaxSpeedProfile:
    """Absolute peak and the response of expressed speed to remaining energy."""

    absolute_speed_mps: float
    reference_remaining_energy: float
    reserve_speed_slope: float
    observations_used: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class MaxSpeedExpression:
    """Maximum speed expected to be available in the target race."""

    absolute_speed_mps: float
    effective_speed_mps: float
    expression_ratio: float
    remaining_energy: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def _validated_observations(
    observations: Sequence[ReserveObservation],
) -> list[ReserveObservation]:
    usable: list[ReserveObservation] = []
    for item in observations:
        if item.speed_mps <= 0:
            continue
        usable.append(
            ReserveObservation(
                remaining_energy=clamp(item.remaining_energy, 0.0, 1.0),
                speed_mps=float(item.speed_mps),
                confidence=clamp(item.confidence, 0.0, 1.0),
            )
        )
    if not usable:
        raise ValueError("At least one positive measured speed is required.")
    return usable


def fit_max_speed_profile(
    observations: Sequence[ReserveObservation],
    *,
    population_slope: float = 1.0,
    minimum_reserve_spread: float = 0.12,
) -> MaxSpeedProfile:
    """Fit a monotone reserve-to-speed response without shrinking the peak.

    Absolute speed is always the best measured physical speed.  Confidence is
    used only when estimating the response slope; it is never multiplied into
    the absolute peak.  Sparse evidence borrows the population slope instead
    of inventing a precise horse-specific response.
    """

    usable = _validated_observations(observations)
    peak = max(usable, key=lambda item: item.speed_mps)
    absolute = peak.speed_mps
    reference_energy = peak.remaining_energy
    reserve_spread = max(item.remaining_energy for item in usable) - min(
        item.remaining_energy for item in usable
    )

    population = max(0.0, float(population_slope))
    if len(usable) < 2 or reserve_spread < minimum_reserve_spread:
        slope = population
    else:
        pairs: list[tuple[float, float]] = []
        for low in usable:
            for high in usable:
                energy_gap = high.remaining_energy - low.remaining_energy
                if energy_gap <= 0.05:
                    continue
                speed_gain = max(0.0, high.speed_mps - low.speed_mps)
                weight = low.confidence * high.confidence
                if weight > 0:
                    pairs.append((speed_gain / energy_gap, weight))

        if pairs:
            horse_slope = sum(value * weight for value, weight in pairs) / sum(
                weight for _, weight in pairs
            )
            evidence_weight = clamp((len(usable) - 1) / 4.0, 0.0, 1.0)
            slope = population * (1.0 - evidence_weight) + horse_slope * evidence_weight
        else:
            slope = population

    return MaxSpeedProfile(
        absolute_speed_mps=round(absolute, 5),
        reference_remaining_energy=round(reference_energy, 5),
        reserve_speed_slope=round(max(0.0, slope), 5),
        observations_used=len(usable),
    )


def express_max_speed(
    profile: MaxSpeedProfile,
    remaining_energy: float,
) -> MaxSpeedExpression:
    """Apply the fitted response curve while preserving the absolute ceiling."""

    reserve = clamp(remaining_energy, 0.0, 1.0)
    reserve_shortfall = max(0.0, profile.reference_remaining_energy - reserve)
    effective = max(
        0.0,
        profile.absolute_speed_mps
        - profile.reserve_speed_slope * reserve_shortfall,
    )
    effective = min(profile.absolute_speed_mps, effective)
    ratio = effective / profile.absolute_speed_mps
    return MaxSpeedExpression(
        absolute_speed_mps=round(profile.absolute_speed_mps, 5),
        effective_speed_mps=round(effective, 5),
        expression_ratio=round(ratio, 5),
        remaining_energy=round(reserve, 5),
    )

