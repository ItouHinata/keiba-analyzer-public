from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from keiba_analyzer.scoring.base_speed import (  # noqa: E402
    RunEvaluation,
    aggregate_horse_scores,
    classify_pace,
    distance_transfer_factor,
    score_non_deceleration,
    score_position_maintenance,
    score_tracking_speed,
)


def build_synthetic_run(
    label: str,
    current_early_time: float,
    baseline_early_time: float,
    early_position: int,
    late_position: int,
    field_size: int,
    max_deceleration: float,
    source_distance: int,
    target_distance: int,
    confidence: float,
    recency_rank: int,
) -> RunEvaluation:
    pace = classify_pace(current_early_time, baseline_early_time, confidence)
    transfer = distance_transfer_factor(source_distance, target_distance)
    tracking = score_tracking_speed(
        pace.pace_class,
        early_position=early_position,
        field_size=field_size,
        transfer_factor=transfer,
    )
    maintenance = score_position_maintenance(
        early_position=early_position,
        late_position=late_position,
        field_size=field_size,
    )
    non_deceleration = score_non_deceleration(
        max_deceleration=max_deceleration,
        base_threshold=0.7,
        position_ratio=late_position / field_size,
    )

    score = min(10.0, tracking + maintenance + non_deceleration + 1.0)
    return RunEvaluation(
        label=label,
        score=round(score, 3),
        confidence=confidence,
        recency_rank=recency_rank,
        status="MEASURED" if confidence >= 0.8 else "ESTIMATED",
    )


def main() -> None:
    runs = [
        build_synthetic_run("sample-run-1", 34.3, 35.0, 2, 3, 16, 0.4, 1600, 1600, 0.91, 1),
        build_synthetic_run("sample-run-2", 34.8, 35.0, 4, 4, 15, 0.6, 1800, 1600, 0.86, 2),
        build_synthetic_run("sample-run-3", 35.1, 35.0, 5, 6, 16, 0.7, 1600, 1600, 0.82, 3),
        build_synthetic_run("sample-run-4", 34.6, 35.0, 7, 7, 14, 0.5, 1400, 1600, 0.80, 4),
        build_synthetic_run("sample-run-5", 35.4, 35.0, 3, 5, 13, 0.8, 2000, 1600, 0.76, 5),
        RunEvaluation("sample-missing", None, 0.0, 6, "NOT_TESTED"),
    ]

    result = aggregate_horse_scores(runs)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
