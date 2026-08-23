"""Frozen held-out evaluator for PRIME M20 Universal Arena v0.3."""

from __future__ import annotations

import json

from .runner_v0_3 import (
    CONDITIONS,
    DEVELOPMENT_SEEDS,
    EVALUATION_SEEDS,
    splitmix64,
    run_world,
)
from .tasks import (
    TASKS,
)


BOOTSTRAP_REPLICATES = 16384
BOOTSTRAP_SEED = (
    0x4D3230563033434C
)

LOWER_INDEX = 409
UPPER_INDEX = 15974


def mean_floor(values):
    if not values:
        return None

    return (
        sum(values)
        // len(values)
    )


def paired_delta_rows(
    lookup,
    left,
    right,
    metric,
):
    values = []

    for seed in EVALUATION_SEEDS:
        for task in TASKS:
            values.append(
                {
                    "seed": seed,
                    "task": task.name,
                    "delta": (
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
                    ),
                }
            )

    return values


def cluster_bootstrap(
    paired_rows,
):
    by_seed = {
        seed: []
        for seed
        in EVALUATION_SEEDS
    }

    for row in paired_rows:
        by_seed[
            row["seed"]
        ].append(
            row["delta"]
        )

    task_count = len(
        TASKS
    )

    for seed, values in (
        by_seed.items()
    ):
        if (
            len(values)
            != task_count
        ):
            raise RuntimeError(
                "cluster task count mismatch"
            )

    cluster_sums = [
        sum(
            by_seed[seed]
        )
        for seed
        in EVALUATION_SEEDS
    ]

    cluster_count = len(
        cluster_sums
    )

    denominator = (
        cluster_count
        * task_count
    )

    bootstrap_means = []

    for replicate in range(
        BOOTSTRAP_REPLICATES
    ):
        total = 0

        for draw in range(
            cluster_count
        ):
            index = (
                splitmix64(
                    BOOTSTRAP_SEED
                    ^ splitmix64(
                        replicate
                    )
                    ^ splitmix64(
                        draw
                    )
                )
                % cluster_count
            )

            total += (
                cluster_sums[
                    index
                ]
            )

        bootstrap_means.append(
            total
            // denominator
        )

    bootstrap_means.sort()

    return {
        "method": (
            "deterministic-seed-cluster-bootstrap"
        ),
        "replicates": (
            BOOTSTRAP_REPLICATES
        ),
        "cluster_count": (
            cluster_count
        ),
        "tasks_per_cluster": (
            task_count
        ),
        "bootstrap_seed": (
            BOOTSTRAP_SEED
        ),
        "lower_index": (
            LOWER_INDEX
        ),
        "upper_index": (
            UPPER_INDEX
        ),
        "lower_ppm": (
            bootstrap_means[
                LOWER_INDEX
            ]
        ),
        "upper_ppm": (
            bootstrap_means[
                UPPER_INDEX
            ]
        ),
    }


def summarize_condition(
    rows,
    condition,
):
    subset = [
        row
        for row in rows
        if (
            row["condition"]
            == condition
        )
    ]

    return {
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


def main():
    if DEVELOPMENT_SEEDS != tuple(
        range(
            600,
            608,
        )
    ):
        raise RuntimeError(
            "development seed contract changed"
        )

    if EVALUATION_SEEDS != tuple(
        range(
            6000,
            6032,
        )
    ):
        raise RuntimeError(
            "evaluation seed contract changed"
        )

    if len(TASKS) != 12:
        raise RuntimeError(
            "task contract changed"
        )

    if len(CONDITIONS) != 4:
        raise RuntimeError(
            "condition contract changed"
        )

    rows = []

    for task in TASKS:
        for seed in EVALUATION_SEEDS:
            for condition in CONDITIONS:
                result = run_world(
                    task=task,
                    stream_seed=seed,
                    condition=condition,
                    permit_evaluation=True,
                ).payload

                rows.append(
                    result
                )

    expected_rows = (
        len(TASKS)
        * len(EVALUATION_SEEDS)
        * len(CONDITIONS)
    )

    if (
        len(rows)
        != expected_rows
        or expected_rows
        != 1536
    ):
        raise RuntimeError(
            "held-out row count mismatch"
        )

    expected_keys = {
        (
            task.name,
            seed,
            condition,
        )
        for task in TASKS
        for seed in EVALUATION_SEEDS
        for condition in CONDITIONS
    }

    observed_keys = {
        (
            row["task"],
            row["stream_seed"],
            row["condition"],
        )
        for row in rows
    }

    integrity_unique = (
        observed_keys
        == expected_keys
        and len(observed_keys)
        == expected_rows
    )

    integrity_version = all(
        row[
            "arena_version"
        ] == "v0.3"
        and row[
            "global_alpha_spending"
        ] is True
        for row in rows
    )

    lookup = {
        (
            row["task"],
            row["stream_seed"],
            row["condition"],
        ): row
        for row in rows
    }

    condition_summaries = {
        condition: (
            summarize_condition(
                rows,
                condition,
            )
        )
        for condition in CONDITIONS
    }

    aulc_rows = (
        paired_delta_rows(
            lookup,
            "M20-CONSTRUCTION",
            "FIXED-H8",
            "primary_aulc_ppm",
        )
    )

    final_rows = (
        paired_delta_rows(
            lookup,
            "M20-CONSTRUCTION",
            "FIXED-H8",
            "final_window_accuracy_ppm",
        )
    )

    final_balanced_rows = (
        paired_delta_rows(
            lookup,
            "M20-CONSTRUCTION",
            "FIXED-H8",
            "final_window_balanced_accuracy_ppm",
        )
    )

    oracle_rows = (
        paired_delta_rows(
            lookup,
            "M20-CONSTRUCTION",
            "ORACLE-FEATURE",
            "primary_aulc_ppm",
        )
    )

    observed_aulc_delta = (
        mean_floor(
            [
                row["delta"]
                for row
                in aulc_rows
            ]
        )
    )

    observed_final_delta = (
        mean_floor(
            [
                row["delta"]
                for row
                in final_rows
            ]
        )
    )

    observed_final_balanced_delta = (
        mean_floor(
            [
                row["delta"]
                for row
                in final_balanced_rows
            ]
        )
    )

    observed_oracle_delta = (
        mean_floor(
            [
                row["delta"]
                for row
                in oracle_rows
            ]
        )
    )

    bootstrap = (
        cluster_bootstrap(
            aulc_rows
        )
    )

    m20_rows = [
        row
        for row in rows
        if (
            row["condition"]
            == "M20-CONSTRUCTION"
        )
    ]

    quotient_recovery = sum(
        row[
            "predictive_partition_recovered"
        ]
        is True
        for row in m20_rows
    )

    exact_recovery = sum(
        row[
            "exact_target_construction_active"
        ]
        is True
        for row in m20_rows
    )

    exact_relations = sum(
        any(
            match["relation"]
            == "exact"
            for match in row[
                "partition_matches"
            ]
        )
        for row in m20_rows
    )

    complement_relations = sum(
        any(
            match["relation"]
            == "complement"
            for match in row[
                "partition_matches"
            ]
        )
        for row in m20_rows
    )

    current_rows = [
        row
        for row in m20_rows
        if row[
            "task"
        ] == "CURRENT"
    ]

    current_unnecessary = sum(
        row[
            "authorized_construction_count"
        ] != 0
        for row in current_rows
    )

    receipts_valid = all(
        row[
            "receipt_chain_valid"
        ]
        for row in m20_rows
    )

    positive_worlds = sum(
        row["delta"] > 0
        for row in aulc_rows
    )

    tied_worlds = sum(
        row["delta"] == 0
        for row in aulc_rows
    )

    negative_worlds = sum(
        row["delta"] < 0
        for row in aulc_rows
    )

    gates = {
        "observed_mean_positive": (
            observed_aulc_delta
            is not None
            and observed_aulc_delta
            > 0
        ),
        "cluster_bootstrap_lower_positive": (
            bootstrap[
                "lower_ppm"
            ]
            > 0
        ),
        "final_accuracy_noninferior": (
            observed_final_delta
            is not None
            and observed_final_delta
            >= 0
        ),
        "final_balanced_accuracy_noninferior": (
            observed_final_balanced_delta
            is not None
            and observed_final_balanced_delta
            >= 0
        ),
        "predictive_partition_recovery_complete": (
            quotient_recovery
            == 384
        ),
        "current_no_unnecessary_construction": (
            len(current_rows)
            == 32
            and current_unnecessary
            == 0
        ),
        "receipt_integrity": (
            receipts_valid
        ),
        "row_integrity": (
            integrity_unique
            and integrity_version
        ),
    }

    supported = all(
        gates.values()
    )

    by_task = []

    for task in TASKS:
        task_aulc = [
            row["delta"]
            for row in aulc_rows
            if row[
                "task"
            ] == task.name
        ]

        task_m20 = [
            row
            for row in m20_rows
            if row[
                "task"
            ] == task.name
        ]

        auth_events = [
            row[
                "authorization_events"
            ][0]
            for row in task_m20
            if row[
                "authorization_events"
            ]
        ]

        by_task.append(
            {
                "task": task.name,
                "world_count": len(
                    task_aulc
                ),
                "mean_m20_minus_h8_aulc_ppm": (
                    mean_floor(
                        task_aulc
                    )
                ),
                "positive_worlds": sum(
                    x > 0
                    for x in task_aulc
                ),
                "ties": sum(
                    x == 0
                    for x in task_aulc
                ),
                "negative_worlds": sum(
                    x < 0
                    for x in task_aulc
                ),
                "predictive_recovery": sum(
                    row[
                        "predictive_partition_recovered"
                    ]
                    is True
                    for row in task_m20
                ),
                "exact_recovery": sum(
                    row[
                        "exact_target_construction_active"
                    ]
                    is True
                    for row in task_m20
                ),
                "mean_first_authorization_event": (
                    mean_floor(
                        auth_events
                    )
                ),
            }
        )

    report = {
        "benchmark": (
            "prime-m20-universal-arena-v0.3"
        ),
        "status": (
            "FROZEN_HELD_OUT_EVALUATION"
        ),
        "development_seeds_run": (
            False
        ),
        "evaluation_seeds": list(
            EVALUATION_SEEDS
        ),
        "task_count": len(
            TASKS
        ),
        "seed_cluster_count": len(
            EVALUATION_SEEDS
        ),
        "paired_world_count": (
            384
        ),
        "row_count": (
            len(rows)
        ),
        "condition_summaries": (
            condition_summaries
        ),
        "primary": {
            "comparison": (
                "M20-CONSTRUCTION minus FIXED-H8"
            ),
            "observed_mean_aulc_delta_ppm": (
                observed_aulc_delta
            ),
            "positive_worlds": (
                positive_worlds
            ),
            "ties": (
                tied_worlds
            ),
            "negative_worlds": (
                negative_worlds
            ),
            "cluster_bootstrap": (
                bootstrap
            ),
            "mean_final_window_accuracy_delta_ppm": (
                observed_final_delta
            ),
            "mean_final_window_balanced_accuracy_delta_ppm": (
                observed_final_balanced_delta
            ),
        },
        "oracle_diagnostic": {
            "mean_m20_minus_oracle_aulc_ppm": (
                observed_oracle_delta
            ),
        },
        "representation": {
            "exact_recovery": (
                exact_recovery
            ),
            "predictive_partition_recovery": (
                quotient_recovery
            ),
            "exact_relation_worlds": (
                exact_relations
            ),
            "complement_relation_worlds": (
                complement_relations
            ),
            "current_world_count": (
                len(current_rows)
            ),
            "current_unnecessary_construction_count": (
                current_unnecessary
            ),
        },
        "integrity": {
            "receipt_chains_valid": (
                receipts_valid
            ),
            "unique_complete_row_set": (
                integrity_unique
            ),
            "v03_global_alpha_flags_valid": (
                integrity_version
            ),
        },
        "claim_gates": (
            gates
        ),
        "claim_supported": (
            supported
        ),
        "by_task": (
            by_task
        ),
        "rows": (
            rows
        ),
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
