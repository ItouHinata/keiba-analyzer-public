"""Privacy-safe reconstruction of position-conditioned race demands.

The private application uses observed track and field data, a three-phase
pace forecast, and database-calibrated samples.  This public module keeps the
core decision structure while intentionally omitting collectors, private data,
and production coefficients outside this small representative matrix.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal, Mapping

AbilityCode = Literal[
    "BASE_SPEED",
    "MAX_SPEED",
    "GEAR_CHANGE",
    "LONG_SPRINT",
    "STAMINA",
]
PositionBand = Literal["FRONT", "MIDDLE", "REAR"]
PaceStyle = Literal["RELAXED", "FLOWING"]

ABILITY_CODES: tuple[AbilityCode, ...] = (
    "BASE_SPEED",
    "MAX_SPEED",
    "GEAR_CHANGE",
    "LONG_SPRINT",
    "STAMINA",
)

# Tuple order follows ABILITY_CODES. Values are relative importance before
# normalization, not additive score bonuses.
POSITION_MULTIPLIERS: dict[
    str, dict[PositionBand, tuple[float, float, float, float, float]]
] = {
    "LOW_FRICTION_HIGH_GRIP_RELAXED": {
        "FRONT": (0.68, 1.38, 1.30, 1.18, 0.70),
        "MIDDLE": (0.72, 1.42, 1.34, 1.15, 0.70),
        "REAR": (0.85, 1.45, 1.38, 1.00, 0.70),
    },
    "LOW_FRICTION_HIGH_GRIP_FLOWING": {
        "FRONT": (0.72, 1.24, 0.62, 1.45, 0.92),
        "MIDDLE": (0.80, 1.22, 0.60, 1.48, 0.95),
        "REAR": (1.00, 1.18, 0.55, 1.40, 0.98),
    },
    "LOW_FRICTION_LOW_GRIP_RELAXED": {
        "FRONT": (1.30, 0.65, 0.55, 1.40, 0.92),
        "MIDDLE": (1.32, 0.60, 0.50, 1.42, 0.96),
        "REAR": (1.38, 0.55, 0.45, 1.35, 1.00),
    },
    "LOW_FRICTION_LOW_GRIP_FLOWING": {
        "FRONT": (1.25, 0.58, 0.45, 1.38, 1.15),
        "MIDDLE": (1.30, 0.55, 0.42, 1.42, 1.18),
        "REAR": (1.38, 0.50, 0.38, 1.38, 1.22),
    },
    "HIGH_FRICTION_HIGH_GRIP_RELAXED": {
        "FRONT": (1.18, 1.18, 1.15, 0.95, 1.20),
        "MIDDLE": (1.20, 1.20, 1.15, 0.95, 1.18),
        "REAR": (1.25, 1.22, 1.18, 0.90, 1.18),
    },
    "HIGH_FRICTION_HIGH_GRIP_FLOWING": {
        "FRONT": (1.34, 0.72, 0.55, 1.28, 1.38),
        "MIDDLE": (1.32, 0.75, 0.55, 1.32, 1.40),
        "REAR": (1.38, 0.78, 0.55, 1.24, 1.42),
    },
    "HIGH_FRICTION_LOW_GRIP_RELAXED": {
        "FRONT": (1.35, 0.50, 0.40, 1.32, 1.28),
        "MIDDLE": (1.35, 0.48, 0.38, 1.35, 1.30),
        "REAR": (1.42, 0.45, 0.35, 1.30, 1.35),
    },
    "HIGH_FRICTION_LOW_GRIP_FLOWING": {
        "FRONT": (1.42, 0.42, 0.30, 1.38, 1.48),
        "MIDDLE": (1.38, 0.42, 0.30, 1.42, 1.50),
        "REAR": (1.45, 0.38, 0.28, 1.38, 1.52),
    },
}


@dataclass(frozen=True)
class SurfaceFlowRegime:
    """One of eight continuous track-and-flow contexts."""

    code: str
    friction_band: Literal["LOW_FRICTION", "HIGH_FRICTION"]
    grip_band: Literal["LOW_GRIP", "HIGH_GRIP"]
    pace_style: PaceStyle
    flow_signal: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, float(value)))


def classify_surface_flow(
    friction: float,
    grip: float,
    *,
    middle_relief: float,
    continuous_flow: float,
    pace_consumption: float,
    explicit_flow: bool = False,
    explicit_relief: bool = False,
) -> SurfaceFlowRegime:
    """Classify physical surface and predicted phase flow into eight regimes."""

    friction_value = clamp(friction)
    grip_value = clamp(grip)
    relief = clamp(middle_relief)
    flow_signal = clamp(
        0.58 * clamp(continuous_flow)
        + 0.27 * clamp(pace_consumption)
        + 0.15 * (1.0 - relief)
    )
    flowing = (
        True
        if explicit_flow
        else False
        if explicit_relief
        else flow_signal >= 0.52
    )
    friction_band = (
        "HIGH_FRICTION" if friction_value >= 0.50 else "LOW_FRICTION"
    )
    grip_band = "HIGH_GRIP" if grip_value >= 0.50 else "LOW_GRIP"
    pace_style: PaceStyle = "FLOWING" if flowing else "RELAXED"
    return SurfaceFlowRegime(
        code=f"{friction_band}_{grip_band}_{pace_style}",
        friction_band=friction_band,
        grip_band=grip_band,
        pace_style=pace_style,
        flow_signal=round(flow_signal, 4),
    )


def position_ability_weights(
    regime: SurfaceFlowRegime | str,
    position: PositionBand,
    *,
    base_weights: Mapping[str, float] | None = None,
) -> dict[AbilityCode, float]:
    """Return normalized five-ability demand for one predicted position band."""

    code = regime.code if isinstance(regime, SurfaceFlowRegime) else str(regime)
    if code not in POSITION_MULTIPLIERS:
        raise ValueError(f"Unknown regime: {code}")
    if position not in {"FRONT", "MIDDLE", "REAR"}:
        raise ValueError(f"Unknown position band: {position}")
    defaults = {ability: 1.0 for ability in ABILITY_CODES}
    if base_weights is not None:
        defaults.update(
            {
                ability: max(0.0, float(base_weights.get(ability, 1.0)))
                for ability in ABILITY_CODES
            }
        )
    raw = {
        ability: defaults[ability] * multiplier
        for ability, multiplier in zip(
            ABILITY_CODES,
            POSITION_MULTIPLIERS[code][position],
            strict=True,
        )
    }
    total = sum(raw.values())
    return {
        ability: round(raw[ability] / total, 4)
        for ability in ABILITY_CODES
    }
