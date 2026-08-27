"""Development-only analysis for PRIME M20 Universal Arena v0.2."""

from __future__ import annotations

import json

from .runner_v0_2 import (
    CONDITIONS,
    DEVELOPMENT_SEEDS,
    EVALUATION_SEEDS,
    run_world,
)
from .tasks import (
    TASKS,
)


def mean_floor(values):
    if not values:
        return None

    return (
        sum(values)
        // len(values)
    )


def main() -> None:
    if DEVELOPMENT_SEEDS != tuple(
        range(600, 608)
    ):
        raise RuntimeError(
            "development seeds changed"
        )

    if EVALUATION_SEEDS != tuple(
        range(6000, 6032)
    ):
        raise RuntimeError(
            "evaluation seeds changed"
        )

    rows = []

    for task in TASKS:
        for seed in DEVELOPMENT_SEEDS:
            for condition in CONDITIONS:
                result = run_world(
                    task=task,
                    stream_seed=seed,
                    condition=condition,
                ).payload

                rows.append(
                    result
                )

    expected_rows = (
        len(TASKS)
        * len(DEVELOPMENT_SEEDS)
        * len(CONDITIONS)
    )

    if len(rows) != expected_rows:
        raise RuntimeError(
            "unexpected development row count"
        )

    summaries = {}

    for condition in CONDITIONS:
        subset = [
            row
            for row in rows
            if (
                row["condition"]
                == condition
            )
        ]

        summaries[
            condition
        ] = {
            "world_count": len(
                subset
            ),
            "mean_primary_aulc_ppm": (
                mean_floor(
                    [
                        row[
                            "primary_aulc_ppm"
                        ]
                        for row in subset
                    ]
                )
            ),
            "mean_accuracy_ppm": (
                mean_floor(
                    [
                        row[
                            "accuracy_ppm"
                        ]
                        for row in subset
                    ]
                )
            ),
            "mean_final_window_accuracy_ppm": (
                mean_floor(
                    [
                        row[
                            "final_window_accuracy_ppm"
                        ]
                        for row in subset
                    ]
                )
            ),
            "mean_balanced_accuracy_ppm": (
                mean_floor(
                    [
                        row[
                            "balanced_accuracy_ppm"
                        ]
                        for row in subset
                        if row[
                            "balanced_accuracy_ppm"
                        ]
                        is not None
                    ]
                )
            ),
            "mean_final_window_balanced_accuracy_ppm": (
                mean_floor(
                    [
                        row[
                            "final_window_balanced_accuracy_ppm"
                        ]
                        for row in subset
                        if row[
                            "final_window_balanced_accuracy_ppm"
                        ]
                        is not None
                    ]
                )
            ),
            "mean_best_constant_accuracy_ppm": (
                mean_floor(
                    [
                        row[
                            "best_constant_accuracy_ppm"
                        ]
                        for row in subset
                    ]
                )
            ),
            "mean_excess_over_constant_ppm": (
                mean_floor(
                    [
                        row[
                            "excess_over_constant_ppm"
                        ]
                        for row in subset
                    ]
                )
            ),
            "mean_cumulative_mistakes": (
                mean_floor(
                    [
                        row[
                            "cumulative_mistakes"
                        ]
                        for row in subset
                    ]
                )
            ),
        }

    by_task = []

    for task in TASKS:
        for condition in CONDITIONS:
            subset = [
                row
                for row in rows
                if (
                    row["task"]
                    == task.name
                    and row["condition"]
                    == condition
                )
            ]

            exact = None
            quotient = None
            receipt_integrity = None
            auth_events = []
            relation_counts = {}

            if condition == "M20-CONSTRUCTION":
                exact = sum(
                    row[
                        "exact_target_construction_active"
                    ]
                    is True
                    for row in subset
                )

                quotient = sum(
                    row[
                        "predictive_partition_recovered"
                    ]
                    is True
                    for row in subset
                )

                receipt_integrity = all(
                    row[
                        "receipt_chain_valid"
                    ]
                    for row in subset
                )

                auth_events = [
                    row[
                        "authorization_events"
                    ][0]
                    for row in subset
                    if row[
                        "authorization_events"
                    ]
                ]

                for row in subset:
                    for match in row[
                        "partition_matches"
                    ]:
                        relation = match[
                            "relation"
                        ]

                        relation_counts[
                            relation
                        ] = (
                            relation_counts.get(
                                relation,
                                0,
                            )
                            + 1
                        )

            by_task.append(
                {
                    "task": (
                        task.name
                    ),
                    "condition": (
                        condition
                    ),
                    "world_count": (
                        len(subset)
                    ),
                    "mean_primary_aulc_ppm": (
                        mean_floor(
                            [
                                row[
                                    "primary_aulc_ppm"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "mean_accuracy_ppm": (
                        mean_floor(
                            [
                                row[
                                    "accuracy_ppm"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "mean_final_window_accuracy_ppm": (
                        mean_floor(
                            [
                                row[
                                    "final_window_accuracy_ppm"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "mean_balanced_accuracy_ppm": (
                        mean_floor(
                            [
                                row[
                                    "balanced_accuracy_ppm"
                                ]
                                for row in subset
                                if row[
                                    "balanced_accuracy_ppm"
                                ]
                                is not None
                            ]
                        )
                    ),
                    "mean_final_window_balanced_accuracy_ppm": (
                        mean_floor(
                            [
                                row[
                                    "final_window_balanced_accuracy_ppm"
                                ]
                                for row in subset
                                if row[
                                    "final_window_balanced_accuracy_ppm"
                                ]
                                is not None
                            ]
                        )
                    ),
                    "mean_target_prevalence_ppm": (
                        mean_floor(
                            [
                                row[
                                    "target_prevalence_ppm"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "mean_best_constant_accuracy_ppm": (
                        mean_floor(
                            [
                                row[
                                    "best_constant_accuracy_ppm"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "mean_excess_over_constant_ppm": (
                        mean_floor(
                            [
                                row[
                                    "excess_over_constant_ppm"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "mean_cumulative_mistakes": (
                        mean_floor(
                            [
                                row[
                                    "cumulative_mistakes"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "exact_expression_recovery": (
                        exact
                    ),
                    "predictive_partition_recovery": (
                        quotient
                    ),
                    "mean_first_authorization_event": (
                        mean_floor(
                            auth_events
                        )
                    ),
                    "partition_relation_counts": (
                        relation_counts
                    ),
                    "all_receipts_valid": (
                        receipt_integrity
                    ),
                }
            )

    lookup = {
        (
            row["task"],
            row["stream_seed"],
            row["condition"],
        ): row
        for row in rows
    }

    def paired_delta(
        left,
        right,
        metric,
    ):
        values = []

        for task in TASKS:
            for seed in DEVELOPMENT_SEEDS:
                values.append(
                    lookup[
                        (
                            task.name,
                            seed,
                            left,
                        )
                    ][metric]
                    -
                    lookup[
                        (
                            task.name,
                            seed,
                            right,
                        )
                    ][metric]
                )

        return {
            "world_count": (
                len(values)
            ),
            "mean_delta": (
                mean_floor(
                    values
                )
            ),
            "positive_worlds": sum(
                value > 0
                for value in values
            ),
            "ties": sum(
                value == 0
                for value in values
            ),
            "negative_worlds": sum(
                value < 0
                for value in values
            ),
        }

    m20_rows = [
        row
        for row in rows
        if (
            row["condition"]
            == "M20-CONSTRUCTION"
        )
    ]

    exact_total = sum(
        row[
            "exact_target_construction_active"
        ]
        is True
        for row in m20_rows
    )

    quotient_total = sum(
        row[
            "predictive_partition_recovered"
        ]
        is True
        for row in m20_rows
    )

    complement_worlds = sum(
        any(
            match["relation"]
            == "complement"
            for match in row[
                "partition_matches"
            ]
        )
        for row in m20_rows
    )

    exact_relation_worlds = sum(
        any(
            match["relation"]
            == "exact"
            for match in row[
                "partition_matches"
            ]
        )
        for row in m20_rows
    )

    report = {
        "benchmark": (
            "prime-m20-universal-arena-v0.2"
        ),
        "status": (
            "DEVELOPMENT_ONLY"
        ),
        "development_seeds": list(
            DEVELOPMENT_SEEDS
        ),
        "evaluation_seeds_run": (
            False
        ),
        "task_count": len(
            TASKS
        ),
        "condition_count": len(
            CONDITIONS
        ),
        "row_count": len(
            rows
        ),
        "condition_summaries": (
            summaries
        ),
        "m20_exact_expression_recovery": (
            exact_total
        ),
        "m20_predictive_partition_recovery": (
            quotient_total
        ),
        "m20_world_count": len(
            m20_rows
        ),
        "m20_exact_relation_worlds": (
            exact_relation_worlds
        ),
        "m20_complement_relation_worlds": (
            complement_worlds
        ),
        "m20_receipts_all_valid": all(
            row[
                "receipt_chain_valid"
            ]
            for row in m20_rows
        ),
        "paired_development": {
            "m20_minus_h8_aulc_ppm": (
                paired_delta(
                    "M20-CONSTRUCTION",
                    "FIXED-H8",
                    "primary_aulc_ppm",
                )
            ),
            "m20_minus_h8_balanced_accuracy_ppm": (
                paired_delta(
                    "M20-CONSTRUCTION",
                    "FIXED-H8",
                    "balanced_accuracy_ppm",
                )
            ),
            "m20_minus_oracle_aulc_ppm": (
                paired_delta(
                    "M20-CONSTRUCTION",
                    "ORACLE-FEATURE",
                    "primary_aulc_ppm",
                )
            ),
        },
        "by_task": (
            by_task
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
