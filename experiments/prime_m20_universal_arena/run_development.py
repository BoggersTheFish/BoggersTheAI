"""Development-only sweep for PRIME M20 Universal Arena."""

import json

from .runner import (
    CONDITIONS,
    DEVELOPMENT_SEEDS,
    EVALUATION_SEEDS,
    run_world,
)
from .tasks import (
    TASKS,
)


def mean_floor(
    values,
):
    if not values:
        return None

    return (
        sum(values)
        // len(values)
    )


def main():
    if DEVELOPMENT_SEEDS != tuple(
        range(
            600,
            608,
        )
    ):
        raise RuntimeError(
            "development seeds changed"
        )

    if EVALUATION_SEEDS != tuple(
        range(
            6000,
            6032,
        )
    ):
        raise RuntimeError(
            "evaluation seeds changed"
        )

    rows = []

    for task in TASKS:
        for seed in DEVELOPMENT_SEEDS:
            for condition in CONDITIONS:
                rows.append(
                    run_world(
                        task=task,
                        stream_seed=seed,
                        condition=condition,
                    ).payload
                )

    summaries = {}

    for condition in CONDITIONS:
        subset = [
            row
            for row in rows
            if row[
                "condition"
            ] == condition
        ]

        summaries[
            condition
        ] = {
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
                    and row[
                        "condition"
                    ]
                    == condition
                )
            ]

            m20_rows = [
                row
                for row in subset
                if condition
                == "M20-CONSTRUCTION"
            ]

            auth_events = [
                event
                for row in m20_rows
                for event in row[
                    "authorization_events"
                ]
            ]

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
                                for row
                                in subset
                            ]
                        )
                    ),
                    "mean_final_window_accuracy_ppm": (
                        mean_floor(
                            [
                                row[
                                    "final_window_accuracy_ppm"
                                ]
                                for row
                                in subset
                            ]
                        )
                    ),
                    "mean_cumulative_mistakes": (
                        mean_floor(
                            [
                                row[
                                    "cumulative_mistakes"
                                ]
                                for row
                                in subset
                            ]
                        )
                    ),
                    "exact_target_recovery": (
                        sum(
                            row[
                                "exact_target_construction_active"
                            ]
                            is True
                            for row
                            in m20_rows
                        )
                        if m20_rows
                        else None
                    ),
                    "mean_first_authorization_event": (
                        mean_floor(
                            [
                                row[
                                    "authorization_events"
                                ][0]
                                for row
                                in m20_rows
                                if row[
                                    "authorization_events"
                                ]
                            ]
                        )
                        if m20_rows
                        else None
                    ),
                    "all_receipts_valid": (
                        all(
                            row[
                                "receipt_chain_valid"
                            ]
                            for row
                            in m20_rows
                        )
                        if m20_rows
                        else None
                    ),
                }
            )

    m20_rows = [
        row
        for row in rows
        if row[
            "condition"
        ] == "M20-CONSTRUCTION"
    ]

    report = {
        "benchmark": (
            "prime-m20-universal-adaptive-state-arena"
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
        "task_count": (
            len(TASKS)
        ),
        "condition_count": (
            len(CONDITIONS)
        ),
        "row_count": (
            len(rows)
        ),
        "condition_summaries": (
            summaries
        ),
        "m20_exact_target_recovery": (
            sum(
                row[
                    "exact_target_construction_active"
                ]
                is True
                for row
                in m20_rows
            )
        ),
        "m20_world_count": (
            len(m20_rows)
        ),
        "m20_receipts_all_valid": (
            all(
                row[
                    "receipt_chain_valid"
                ]
                for row
                in m20_rows
            )
        ),
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
