"""Lap-first leader selection for the public portfolio edition.

Reaching the lead and choosing to lead are different events.  This module
keeps physical early speed separate from observed lead conversion so that a
fast stalker is not automatically classified as the natural leader.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import prod, sqrt
from typing import Literal, Sequence

LeaderRole = Literal[
    "NATURAL_LEADER",
    "FAST_STALKER",
    "INHERITED_CANDIDATE",
    "UNMEASURED",
]


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


@dataclass(frozen=True)
class LeaderCandidate:
    horse_id: str
    physical_reach_probability: float
    lead_conversion_rate: float | None
    hold_conversion_rate: float | None
    evidence_reliability: float

    @property
    def selection_probability(self) -> float:
        """Joint support for physically reaching and intentionally taking lead."""

        if self.lead_conversion_rate is None:
            return 0.0
        conversion = clamp(self.lead_conversion_rate)
        reliability = clamp(self.evidence_reliability)
        supported_conversion = conversion * (0.35 + 0.65 * reliability)
        return clamp(self.physical_reach_probability) * supported_conversion


@dataclass(frozen=True)
class LeaderAssessment:
    horse_id: str
    role: LeaderRole
    selection_probability: float

    def to_dict(self) -> dict[str, str | float]:
        return asdict(self)


@dataclass(frozen=True)
class VacancyPressure:
    pressure_score: float
    substantial_pressure: float
    middle_lull_probability: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


def classify_leader(candidate: LeaderCandidate) -> LeaderAssessment:
    """Distinguish a natural leader from a fast horse that usually settles."""

    physical = clamp(candidate.physical_reach_probability)
    if candidate.lead_conversion_rate is None:
        role: LeaderRole = "UNMEASURED"
    else:
        lead_rate = clamp(candidate.lead_conversion_rate)
        hold_rate = clamp(candidate.hold_conversion_rate or 0.0)
        if physical >= 0.50 and lead_rate >= 0.45:
            role = "NATURAL_LEADER"
        elif physical >= 0.65 and hold_rate >= max(0.35, lead_rate * 1.25):
            role = "FAST_STALKER"
        elif physical >= 0.45:
            role = "INHERITED_CANDIDATE"
        else:
            role = "UNMEASURED"
    return LeaderAssessment(
        horse_id=candidate.horse_id,
        role=role,
        selection_probability=round(candidate.selection_probability, 4),
    )


def no_clear_leader_probability(candidates: Sequence[LeaderCandidate]) -> float:
    """Return the probability that no horse has both speed and lead intent."""

    if not candidates:
        return 1.0
    return round(
        clamp(prod(1.0 - candidate.selection_probability for candidate in candidates)),
        4,
    )


def leader_settlement_distance(race_distance: int) -> int:
    """Representative 200 m horizon for resolving the early formation."""

    if race_distance <= 0:
        raise ValueError("race_distance must be positive.")
    if race_distance <= 1400:
        return 400
    if race_distance <= 1800:
        return 600
    if race_distance <= 2400:
        return 800
    return 1000


def evaluate_vacancy_pressure(
    *,
    field_pace_pressure: float,
    leader_battle: float,
    front_mass: float,
    stalking_pressure: float,
    makuri_pressure: float,
) -> VacancyPressure:
    """Keep a middle-race lull unless independent lap pressure is substantial.

    The returned values describe a decision structure, not production
    coefficients.  A missing natural leader does not itself create a flowing
    middle phase; pace pressure must be supported by the field's lap profile.
    """

    pace = clamp(field_pace_pressure)
    battle = clamp(leader_battle)
    mass = clamp(front_mass)
    stalking = clamp(stalking_pressure)
    makuri = clamp(makuri_pressure)
    pressure = max(pace, stalking, sqrt(battle * mass), 0.82 * makuri)
    substantial = clamp((pressure - 0.58) / 0.24)
    return VacancyPressure(
        pressure_score=round(pressure, 4),
        substantial_pressure=round(substantial, 4),
        middle_lull_probability=round(1.0 - substantial, 4),
    )

