"""Select v1.2 fixed comparator using development seeds only."""

import json

from experiments.prime_canonical_agent_benchmark_v1.runner import (
    run_fixed_condition,
)

from .manifest import (
    DEVELOPMENT_SEEDS,
    FIXED_CONDITIONS,
)


DEPTH = {
    "FIXED-H1": 1,
    "FIXED-H2": 2,
    "FIXED-H4": 4,
}


def main() -> None:
    if DEVELOPMENT_SEEDS != tuple(range(100, 132)):
        raise RuntimeError(
            "v1.2 development seed set is not frozen 100..131"
        )

    rows = []

    for condition in FIXED_CONDITIONS:
        metrics = []

        for seed in DEVELOPMENT_SEEDS:
            result = run_fixed_condition(
                seed,
                condition,
            ).payload

            metrics.append(
                result["primary_aulc_ppm"]
            )

        rows.append(
            {
                "condition": condition,
                "representation_depth": DEPTH[condition],
                "world_count": len(metrics),
                "mean_primary_aulc_ppm": (
                    sum(metrics) // len(metrics)
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
        "benchmark": "prime-canonical-agent-benchmark-v1.2",
        "status": "DEVELOPMENT_FIXED_COMPARATOR_SELECTION",
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "evaluation_seeds_run": False,
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
