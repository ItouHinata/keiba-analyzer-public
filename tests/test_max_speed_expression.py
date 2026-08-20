from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keiba_analyzer.scoring.max_speed_expression import (  # noqa: E402
    ReserveObservation,
    express_max_speed,
    fit_max_speed_profile,
)


class MaxSpeedExpressionTests(unittest.TestCase):
    def test_absolute_peak_is_not_shrunk_by_confidence(self) -> None:
        profile = fit_max_speed_profile(
            [
                ReserveObservation(0.82, 18.20, 0.25),
                ReserveObservation(0.35, 17.40, 0.95),
            ]
        )
        self.assertEqual(profile.absolute_speed_mps, 18.20)

    def test_lower_remaining_energy_reduces_expression(self) -> None:
        profile = fit_max_speed_profile(
            [
                ReserveObservation(0.80, 18.00),
                ReserveObservation(0.25, 17.20),
            ]
        )
        high = express_max_speed(profile, 0.80)
        low = express_max_speed(profile, 0.20)
        self.assertEqual(high.effective_speed_mps, profile.absolute_speed_mps)
        self.assertLess(low.effective_speed_mps, high.effective_speed_mps)

    def test_effective_speed_never_exceeds_absolute_peak(self) -> None:
        profile = fit_max_speed_profile(
            [ReserveObservation(0.50, 17.50)], population_slope=1.2
        )
        result = express_max_speed(profile, 1.0)
        self.assertEqual(result.effective_speed_mps, 17.50)
        self.assertEqual(result.expression_ratio, 1.0)

    def test_sparse_evidence_borrows_population_slope(self) -> None:
        profile = fit_max_speed_profile(
            [ReserveObservation(0.62, 17.80)], population_slope=0.85
        )
        self.assertEqual(profile.reserve_speed_slope, 0.85)


if __name__ == "__main__":
    unittest.main()

