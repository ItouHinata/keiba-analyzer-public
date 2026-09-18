"""Regression checks with synthetic laps only; no database or network."""

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from keiba_analyzer.prediction.lap_checkpoint import checkpoint_clock
from keiba_analyzer.prediction.phase_contract import canonical_pace_path, phase_distances


class PhaseContractTests(unittest.TestCase):
    def test_forecast_overrides_longer_course_prior_without_mutation(self):
        source = {"late_phase_furlongs": 5,
                  "phase_transition": {"late_start_furlongs": 3}}
        original = copy.deepcopy(source)
        result = canonical_pace_path(source, 1600)
        self.assertEqual(result["late_phase_furlongs"], 3)
        self.assertEqual(result["phase_transition"]["late_start_furlongs"], 3)
        self.assertEqual(source, original)

    def test_straight_does_not_reapply_pre_straight_distance(self):
        path = canonical_pace_path({"late_phase_furlongs": 4}, 1700)
        all_phases = phase_distances(path, 1700)
        before = phase_distances(path, 1700, end=1300)
        after = phase_distances(path, 1700, start=1300)
        self.assertEqual(sum(before.values()), 1300)
        self.assertEqual(sum(after.values()), 400)
        for name in all_phases:
            self.assertEqual(before[name] + after[name], all_phases[name])

    def test_partial_furlong_and_short_race_are_bounded(self):
        self.assertEqual(phase_distances({"late_phase_furlongs": 3.5}, 1500)["late"], 700)
        self.assertEqual(sum(phase_distances({"late_phase_furlongs": 8}, 1200).values()), 1200)

    def test_invalid_transition_uses_valid_prior(self):
        path = canonical_pace_path({"late_phase_furlongs": 4,
                                   "phase_transition": {"late_start_furlongs": float("nan")}}, 1600)
        self.assertEqual(path["late_phase_furlongs"], 4)


class LapCheckpointTests(unittest.TestCase):
    def test_starting_100m_uses_next_interval_not_doubled_start(self):
        for distance in (1500, 1700, 1900):
            with self.subTest(distance=distance):
                result = checkpoint_clock([(1, 7, 100), (2, 12, 300)], 200, distance)
                self.assertEqual(result["seconds"], 13)
                self.assertEqual(result["measurement_kind"], "INTERPOLATED")

    def test_exact_endpoint_is_measured(self):
        result = checkpoint_clock([(1, 12.5, 200), (2, 11.5, 400)], 400, 1600)
        self.assertEqual(result["seconds"], 24)
        self.assertEqual(result["measurement_kind"], "MEASURED")

    def test_missing_prefix_is_not_shifted_forward(self):
        for rows in ([(2, 12, 400)], [(1, None, 200)], [(1, 12, 200), (3, 12, 600)]):
            self.assertEqual(checkpoint_clock(rows, 400, 1600)["measurement_kind"], "UNAVAILABLE")

    def test_invalid_time_or_distance_is_unavailable(self):
        for rows in ([(1, float("nan"), 200)], [(1, 0, 200)], [(1, 12, 300)]):
            self.assertEqual(checkpoint_clock(rows, 200, 1600)["measurement_kind"], "UNAVAILABLE")

    def test_endpoint_can_be_inferred_from_race_distance(self):
        self.assertEqual(checkpoint_clock([(1, 7, None), (2, 12, None)], 200, 1700)["seconds"], 13)

    def test_uncovered_distance_is_unavailable(self):
        self.assertEqual(checkpoint_clock([(1, 12, 200)], 400, 1600)["measurement_kind"], "UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
