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
from keiba_analyzer.scoring.race_context import (  # noqa: E402
    classify_surface_flow,
    position_ability_weights,
)
from keiba_analyzer.scoring.max_speed_expression import (  # noqa: E402
    ReserveObservation,
    express_max_speed,
    fit_max_speed_profile,
)
from keiba_analyzer.scoring.lap_based_leader import (  # noqa: E402
    LeaderCandidate,
    classify_leader,
    evaluate_vacancy_pressure,
    no_clear_leader_probability,
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
    regime = classify_surface_flow(
        friction=0.20,
        grip=0.82,
        middle_relief=0.25,
        continuous_flow=0.70,
        pace_consumption=0.55,
    )
    max_speed_profile = fit_max_speed_profile(
        [
            ReserveObservation(0.82, 18.20, 0.92),
            ReserveObservation(0.48, 17.78, 0.86),
            ReserveObservation(0.24, 17.31, 0.80),
        ],
        population_slope=0.90,
    )
    max_speed = express_max_speed(max_speed_profile, remaining_energy=0.41)
    leader_candidates = [
        LeaderCandidate("sample-horse-a", 0.86, 0.68, 0.20, 0.91),
        LeaderCandidate("sample-horse-b", 0.88, 0.18, 0.72, 0.88),
    ]
    vacancy = evaluate_vacancy_pressure(
        field_pace_pressure=0.44,
        leader_battle=0.32,
        front_mass=0.46,
        stalking_pressure=0.41,
        makuri_pressure=0.20,
    )
    output = {
        "base_speed": result.to_dict(),
        "race_context": {
            "regime": regime.to_dict(),
            "position_ability_weights": {
                position: position_ability_weights(regime, position)
                for position in ("FRONT", "MIDDLE", "REAR")
            },
        },
        "max_speed_expression": {
            "profile": max_speed_profile.to_dict(),
            "target_race": max_speed.to_dict(),
        },
        "leader_forecast": {
            "candidates": [
                classify_leader(candidate).to_dict()
                for candidate in leader_candidates
            ],
            "no_clear_leader_probability": no_clear_leader_probability(
                leader_candidates
            ),
            "vacancy_pressure": vacancy.to_dict(),
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
