from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keiba_analyzer.scoring.race_context import (  # noqa: E402
    classify_surface_flow,
    position_ability_weights,
)


class SurfaceFlowClassificationTests(unittest.TestCase):
    def test_light_high_grip_relaxed_context(self) -> None:
        regime = classify_surface_flow(
            0.20,
            0.82,
            middle_relief=0.70,
            continuous_flow=0.25,
            pace_consumption=0.25,
        )
        self.assertEqual(regime.code, "LOW_FRICTION_HIGH_GRIP_RELAXED")

    def test_explicit_phase_state_has_priority(self) -> None:
        flowing = classify_surface_flow(
            0.20,
            0.82,
            middle_relief=0.80,
            continuous_flow=0.10,
            pace_consumption=0.10,
            explicit_flow=True,
        )
        self.assertEqual(flowing.pace_style, "FLOWING")


class PositionDemandTests(unittest.TestCase):
    def test_light_high_grip_relaxed_race_prioritizes_acceleration(self) -> None:
        weights = position_ability_weights(
            "LOW_FRICTION_HIGH_GRIP_RELAXED",
            "MIDDLE",
        )
        self.assertGreater(weights["MAX_SPEED"], weights["STAMINA"])
        self.assertGreater(weights["GEAR_CHANGE"], weights["BASE_SPEED"])

    def test_light_high_grip_flow_prioritizes_speed_sustain(self) -> None:
        weights = position_ability_weights(
            "LOW_FRICTION_HIGH_GRIP_FLOWING",
            "FRONT",
        )
        self.assertGreater(weights["LONG_SPRINT"], weights["STAMINA"])
        self.assertGreater(weights["MAX_SPEED"], weights["GEAR_CHANGE"])

    def test_tough_low_grip_flow_prioritizes_resistance(self) -> None:
        weights = position_ability_weights(
            "HIGH_FRICTION_LOW_GRIP_FLOWING",
            "FRONT",
        )
        self.assertGreater(weights["STAMINA"], weights["MAX_SPEED"])
        self.assertGreater(weights["BASE_SPEED"], weights["GEAR_CHANGE"])

    def test_weights_are_normalized(self) -> None:
        weights = position_ability_weights(
            "HIGH_FRICTION_HIGH_GRIP_FLOWING",
            "REAR",
        )
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)


if __name__ == "__main__":
    unittest.main()
