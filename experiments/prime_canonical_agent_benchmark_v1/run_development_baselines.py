"""Run and freeze development-only fixed baseline selection.

This script MUST NOT run evaluation seeds.
"""

import json

from .manifest import DEVELOPMENT_SEEDS
from .provenance import contract_sha256, implementation_sha256
from .runner import run_fixed_condition

CONDITIONS = ("FIXED-H1", "FIXED-H2", "FIXED-H4")


def main() -> None:
    rows = []

    for condition in CONDITIONS:
        metrics = []

        for seed in DEVELOPMENT_SEEDS:
            result = run_fixed_condition(seed, condition)
            metrics.append(result.payload["primary_aulc_ppm"])

        rows.append(
            {
                "condition": condition,
                "mean_primary_aulc_ppm": sum(metrics) // len(metrics),
            }
        )

    best_score = max(row["mean_primary_aulc_ppm"] for row in rows)

    winners = [
        row
        for row in rows
        if row["mean_primary_aulc_ppm"] == best_score
    ]

    depth_order = {
        "FIXED-H1": 1,
        "FIXED-H2": 2,
        "FIXED-H4": 4,
    }

    selected = min(
        winners,
        key=lambda row: depth_order[row["condition"]],
    )["condition"]

    report = {
        "contract_sha256": contract_sha256(),
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "implementation_sha256": implementation_sha256(),
        "selection_rule": (
            "highest mean primary_aulc_ppm; ties select smaller depth"
        ),
        "rows": rows,
        "selected_fixed_baseline": selected,
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
