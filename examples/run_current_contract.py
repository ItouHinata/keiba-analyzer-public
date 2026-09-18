"""Synthetic, offline demo of the deployed phase and lap-clock contracts."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keiba_analyzer.prediction.lap_checkpoint import checkpoint_clock
from keiba_analyzer.prediction.phase_contract import canonical_pace_path, phase_distances


def build_demo():
    # A course prior suggests 5F, but the decided forecast is a 3F finish.
    path = canonical_pace_path({
        "late_phase_furlongs": 5.0,
        "phase_transition": {"late_start_furlongs": 3.0},
    }, 1700)
    # Synthetic 100 m + 200 m + 200 m sections, not collected race records.
    laps = [(1, 7.0, 100), (2, 12.0, 300), (3, 11.8, 500)]
    return {
        "synthetic": True,
        "scope": "PHASE_AND_CLOCK_CONTRACT_ONLY_NOT_A_FULL_PREDICTION",
        "pace_path": path,
        "before_straight_m": phase_distances(path, 1700, end=1300),
        "straight_m": phase_distances(path, 1700, start=1300),
        "clock_200m": checkpoint_clock(laps, 200, 1700),
        "clock_300m": checkpoint_clock(laps, 300, 1700),
        "clock_400m": checkpoint_clock(laps, 400, 1700),
    }


if __name__ == "__main__":
    print(json.dumps(build_demo(), ensure_ascii=False, indent=2))
