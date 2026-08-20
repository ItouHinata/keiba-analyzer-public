from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keiba_analyzer.scoring.lap_based_leader import (  # noqa: E402
    LeaderCandidate,
    classify_leader,
    evaluate_vacancy_pressure,
    leader_settlement_distance,
    no_clear_leader_probability,
)


class LeaderClassificationTests(unittest.TestCase):
    def test_natural_leader_requires_reach_and_conversion(self) -> None:
        result = classify_leader(LeaderCandidate("A", 0.85, 0.72, 0.15, 0.90))
        self.assertEqual(result.role, "NATURAL_LEADER")

    def test_fast_stalker_is_not_misclassified_as_natural_leader(self) -> None:
        result = classify_leader(LeaderCandidate("B", 0.88, 0.18, 0.74, 0.90))
        self.assertEqual(result.role, "FAST_STALKER")

    def test_missing_conversion_evidence_is_unmeasured(self) -> None:
        result = classify_leader(LeaderCandidate("C", 0.92, None, None, 0.0))
        self.assertEqual(result.role, "UNMEASURED")
        self.assertEqual(result.selection_probability, 0.0)

    def test_no_clear_leader_is_high_for_weak_candidates(self) -> None:
        candidates = [
            LeaderCandidate("A", 0.55, 0.12, 0.60, 0.80),
            LeaderCandidate("B", 0.48, 0.10, 0.50, 0.70),
        ]
        self.assertGreater(no_clear_leader_probability(candidates), 0.85)


class VacancyFlowTests(unittest.TestCase):
    def test_vacancy_keeps_lull_under_moderate_pressure(self) -> None:
        result = evaluate_vacancy_pressure(
            field_pace_pressure=0.42,
            leader_battle=0.30,
            front_mass=0.45,
            stalking_pressure=0.40,
            makuri_pressure=0.25,
        )
        self.assertEqual(result.middle_lull_probability, 1.0)

    def test_substantial_lap_pressure_can_remove_lull(self) -> None:
        result = evaluate_vacancy_pressure(
            field_pace_pressure=0.88,
            leader_battle=0.70,
            front_mass=0.75,
            stalking_pressure=0.72,
            makuri_pressure=0.40,
        )
        self.assertLess(result.middle_lull_probability, 0.1)

    def test_settlement_horizon_changes_with_distance(self) -> None:
        self.assertEqual(leader_settlement_distance(1200), 400)
        self.assertEqual(leader_settlement_distance(1600), 600)
        self.assertEqual(leader_settlement_distance(2200), 800)
        self.assertEqual(leader_settlement_distance(3000), 1000)


if __name__ == "__main__":
    unittest.main()

