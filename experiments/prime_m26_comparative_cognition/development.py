"""Development analysis for PRIME M26 comparative cognition."""

from __future__ import annotations

import json

from .runner import (
    CONDITIONS,
    DEVELOPMENT_SEEDS,
    run_world,
)
from .tasks import (
    tasks,
)


def mean_floor(
    values,
):
    values = list(values)

    if not values:
        return None

    return (
        sum(values)
        // len(values)
    )


def main():
    rows = []

    for task in tasks():
        for seed in DEVELOPMENT_SEEDS:
            for condition in CONDITIONS:
                rows.append(
                    run_world(
                        task,
                        seed,
                        condition,
                    ).payload
                )

    by_condition = {}

    for condition in CONDITIONS:
        subset = [
            row
            for row in rows
            if row["condition"]
            == condition
        ]

        by_condition[
            condition
        ] = {
            "world_count": (
                len(subset)
            ),
            "mean_aulc_ppm": (
                mean_floor(
                    row["aulc_ppm"]
                    for row in subset
                )
            ),
            "mean_accuracy_ppm": (
                mean_floor(
                    row["accuracy_ppm"]
                    for row in subset
                )
            ),
            "mean_final_accuracy_ppm": (
                mean_floor(
                    row[
                        "final_accuracy_ppm"
                    ]
                    for row in subset
                )
            ),
            "mean_mistakes": (
                mean_floor(
                    row["mistakes"]
                    for row in subset
                )
            ),
        }

    families = sorted(
        {
            task.family
            for task in tasks()
        }
    )

    by_family = {}

    for family in families:
        by_family[family] = {}

        for condition in CONDITIONS:
            subset = [
                row
                for row in rows
                if (
                    row["family"]
                    == family
                    and row["condition"]
                    == condition
                )
            ]

            by_family[
                family
            ][
                condition
            ] = {
                "aulc_ppm": (
                    mean_floor(
                        row["aulc_ppm"]
                        for row in subset
                    )
                ),
                "final_accuracy_ppm": (
                    mean_floor(
                        row[
                            "final_accuracy_ppm"
                        ]
                        for row in subset
                    )
                ),
            }

    by_task = []

    for task in tasks():
        output = {
            "task": task.name,
            "family": task.family,
        }

        for condition in CONDITIONS:
            subset = [
                candidate
                for candidate in rows
                if (
                    candidate["task"]
                    == task.name
                    and candidate[
                        "condition"
                    ]
                    == condition
                )
            ]

            output[
                condition
            ] = {
                "aulc_ppm": (
                    mean_floor(
                        candidate[
                            "aulc_ppm"
                        ]
                        for candidate
                        in subset
                    )
                ),
                "final_accuracy_ppm": (
                    mean_floor(
                        candidate[
                            "final_accuracy_ppm"
                        ]
                        for candidate
                        in subset
                    )
                ),
            }

        prime_rows = [
            candidate
            for candidate in rows
            if (
                candidate["task"]
                == task.name
                and candidate[
                    "condition"
                ]
                == "PRIME"
            )
        ]

        recoveries = [
            candidate[
                "prime_explicit_recovery"
            ]
            for candidate
            in prime_rows
            if candidate[
                "prime_explicit_recovery"
            ]
            is not None
        ]

        output[
            "prime_explicit_recovery"
        ] = (
            None
            if not recoveries
            else (
                f"{sum(recoveries)}/"
                f"{len(recoveries)}"
            )
        )

        output[
            "prime_mean_first_authorization"
        ] = mean_floor(
            candidate[
                "prime_first_authorization"
            ]
            for candidate
            in prime_rows
            if candidate[
                "prime_first_authorization"
            ]
            is not None
        )

        by_task.append(
            output
        )

    prime_integrity = all(
        row["prime_receipts_valid"]
        for row in rows
        if row["condition"]
        == "PRIME"
    )

    gru_rows = [
        row
        for row in rows
        if row["condition"]
        == "GRU32"
    ]

    report = {
        "benchmark": (
            "prime-m26-comparative-cognition-v0.1"
        ),
        "status": (
            "DEVELOPMENT_ONLY"
        ),
        "task_count": (
            len(tasks())
        ),
        "development_seed_count": (
            len(
                DEVELOPMENT_SEEDS
            )
        ),
        "worlds_per_condition": (
            len(tasks())
            * len(
                DEVELOPMENT_SEEDS
            )
        ),
        "row_count": (
            len(rows)
        ),
        "condition_summaries": (
            by_condition
        ),
        "family_summaries": (
            by_family
        ),
        "task_summaries": (
            by_task
        ),
        "prime_receipt_integrity": (
            prime_integrity
        ),
        "gru_parameter_count": (
            gru_rows[0][
                "gru_parameter_count"
            ]
        ),
        "rows": rows,
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
