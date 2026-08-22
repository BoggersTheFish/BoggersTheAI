"""Select v1.3 fixed comparator using fresh development worlds only."""

import json

from experiments.prime_canonical_agent_benchmark_v1.runner import (
    run_fixed_condition,
)

from .manifest import (
    DEVELOPMENT_SEEDS,
    EVALUATION_SEEDS,
    FIXED_CONDITIONS,
)


DEPTH = {
    "FIXED-H1": 1,
    "FIXED-H2": 2,
    "FIXED-H4": 4,
}


def main() -> None:
    if DEVELOPMENT_SEEDS != tuple(range(300, 332)):
        raise RuntimeError("v1.3 development seeds changed")

    if EVALUATION_SEEDS != tuple(range(3000, 3128)):
        raise RuntimeError("v1.3 evaluation seeds changed")

    rows = []

    for condition in FIXED_CONDITIONS:
        values = []

        for seed in DEVELOPMENT_SEEDS:
            result = run_fixed_condition(
                seed,
                condition,
            ).payload

            values.append(
                result["primary_aulc_ppm"]
            )

        rows.append(
            {
                "condition": condition,
                "representation_depth": DEPTH[condition],
                "world_count": len(values),
                "mean_primary_aulc_ppm": (
                    sum(values) // len(values)
                ),
            }
        )

    best = max(
        row["mean_primary_aulc_ppm"]
        for row in rows
    )

    selected = min(
        (
            row
            for row in rows
            if row["mean_primary_aulc_ppm"] == best
        ),
        key=lambda row: row["representation_depth"],
    )

    report = {
        "benchmark": "prime-canonical-agent-benchmark-v1.3",
        "status": "DEVELOPMENT_FIXED_COMPARATOR_SELECTION",
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "evaluation_seeds_run": False,
        "evaluation_seed_range": "3000..3127",
        "selection_rule": (
            "highest mean primary_aulc_ppm; "
            "ties select smaller representation"
        ),
        "rows": rows,
        "selected_fixed_baseline": selected["condition"],
    }

    print(
        json.dumps(
            report,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
