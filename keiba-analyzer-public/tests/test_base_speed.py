from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keiba_analyzer.scoring.base_speed import (  # noqa: E402
    RunEvaluation,
    aggregate_horse_scores,
    apply_position_threshold_correction,
    classify_pace,
    distance_transfer_factor,
    score_non_deceleration,
    score_position_maintenance,
    score_tracking_speed,
)


class PaceTests(unittest.TestCase):
    def test_fast_pace(self) -> None:
        result = classify_pace(34.2, 35.0, 0.8)
        self.assertEqual(result.pace_class, "FAST")
        self.assertEqual(result.delta_seconds, 0.8)

    def test_missing_baseline_is_estimated(self) -> None:
        result = classify_pace(34.2, None, 0.4)
        self.assertEqual(result.pace_class, "STANDARD_ESTIMATED")
        self.assertIsNone(result.delta_seconds)


class ComponentScoreTests(unittest.TestCase):
    def test_distance_transfer_factor(self) -> None:
        self.assertEqual(distance_transfer_factor(1600, 1600), 1.0)
        self.assertEqual(distance_transfer_factor(2000, 1600), 0.8)
        self.assertEqual(distance_transfer_factor(3000, 1200), 0.5)

    def test_tracking_score_rewards_forward_fast_pace(self) -> None:
        score = score_tracking_speed("FAST", early_position=2, field_size=16)
        self.assertEqual(score, 4.0)

    def test_position_maintenance(self) -> None:
        self.assertEqual(score_position_maintenance(3, 3, 16), 2.5)
        self.assertLess(score_position_maintenance(3, 13, 16), 1.0)

    def test_position_adjusts_deceleration_threshold(self) -> None:
        self.assertEqual(apply_position_threshold_correction(0.7, 0.08), 1.0)
        self.assertEqual(apply_position_threshold_correction(0.7, 0.70), 0.7)
        self.assertEqual(score_non_deceleration(0.6, 0.7, 0.08), 2.5)


class AggregationTests(unittest.TestCase):
    def test_selects_five_strongest_runs_and_returns_range(self) -> None:
        runs = [
            RunEvaluation("run-1", 8.8, 0.90, 1, "MEASURED"),
            RunEvaluation("run-2", 8.1, 0.88, 2, "MEASURED"),
            RunEvaluation("run-3", 7.9, 0.82, 3, "MEASURED"),
            RunEvaluation("run-4", 7.6, 0.80, 4, "MEASURED"),
            RunEvaluation("run-5", 7.3, 0.78, 5, "MEASURED"),
            RunEvaluation("weak", 9.0, 0.20, 6, "ESTIMATED"),
            RunEvaluation("missing", None, 0.0, 7, "NOT_TESTED"),
        ]

        result = aggregate_horse_scores(runs)

        self.assertEqual(result.runs_used, 5)
        self.assertNotIn("weak", [item.label for item in result.selected_runs])
        self.assertIsNotNone(result.central_score)
        self.assertLessEqual(result.lower_score, result.central_score)
        self.assertGreaterEqual(result.upper_score, result.central_score)
        self.assertGreater(result.confidence, 0.7)

    def test_no_usable_runs(self) -> None:
        result = aggregate_horse_scores(
            [RunEvaluation("missing", None, 0.0, 1, "NOT_TESTED")]
        )
        self.assertEqual(result.status, "NOT_TESTED")
        self.assertIsNone(result.central_score)


if __name__ == "__main__":
    unittest.main()
