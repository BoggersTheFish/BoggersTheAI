"""Frozen-rule development diagnostic sweep for PRIME v1.3."""

import json

from experiments.prime_canonical_agent_benchmark_v1.runner import (
    run_fixed_condition,
)

from .adaptive_runner import (
    run_adaptive_condition,
)
from .manifest import (
    ADAPTIVE_CONDITIONS,
    DEVELOPMENT_SEEDS,
    EVALUATION_SEEDS,
)
from .provenance import (
    frozen_identities,
    implementation_sha256,
)


def mean_floor(values):
    if not values:
        return None

    return sum(values) // len(values)


def main() -> None:
    if DEVELOPMENT_SEEDS != tuple(
        range(300, 332)
    ):
        raise RuntimeError(
            "development seeds changed"
        )

    if EVALUATION_SEEDS != tuple(
        range(3000, 3128)
    ):
        raise RuntimeError(
            "evaluation seeds changed"
        )

    rows = []

    fixed_h4_values = []

    for seed in DEVELOPMENT_SEEDS:
        hidden_depth = (
            (0, 1, 2, 4)[
                seed % 4
            ]
        )

        fixed = run_fixed_condition(
            seed,
            "FIXED-H4",
        ).payload

        fixed_h4_values.append(
            fixed["primary_aulc_ppm"]
        )

        for condition in ADAPTIVE_CONDITIONS:
            result = run_adaptive_condition(
                seed,
                condition,
            ).payload

            if result["source_dirty"]:
                raise RuntimeError(
                    "development sweep requires "
                    "clean committed source"
                )

            rows.append(
                {
                    "world_seed": seed,
                    "diagnostic_hidden_depth": (
                        hidden_depth
                    ),
                    "condition": condition,
                    "primary_aulc_ppm": (
                        result[
                            "primary_aulc_ppm"
                        ]
                    ),
                    "final_window_reward_ppm": (
                        result[
                            "final_window_reward_ppm"
                        ]
                    ),
                    "cumulative_regret": (
                        result[
                            "cumulative_regret"
                        ]
                    ),
                    "proposed_repairs": (
                        result[
                            "proposed_repairs"
                        ]
                    ),
                    "accepted_repairs": (
                        result[
                            "accepted_repairs"
                        ]
                    ),
                    "rejected_repairs": (
                        result[
                            "rejected_repairs"
                        ]
                    ),
                    "final_representation_depth": (
                        result[
                            "final_representation_depth"
                        ]
                    ),
                    "authorization_latencies": (
                        result[
                            "authorization_latencies_scored_events"
                        ]
                    ),
                    "selected_witness_lags": (
                        result[
                            "selected_witness_lags"
                        ]
                    ),
                    "receipt_chain_valid": (
                        result[
                            "repair_receipt_chain_valid"
                        ]
                    ),
                    "source_dirty": (
                        result[
                            "source_dirty"
                        ]
                    ),
                }
            )

    summaries = {}

    for condition in ADAPTIVE_CONDITIONS:
        subset = [
            row
            for row in rows
            if row["condition"]
            == condition
        ]

        latencies = [
            latency
            for row in subset
            for latency in row[
                "authorization_latencies"
            ]
        ]

        summaries[condition] = {
            "world_count": len(subset),
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
            "mean_final_window_reward_ppm": (
                mean_floor(
                    [
                        row[
                            "final_window_reward_ppm"
                        ]
                        for row in subset
                    ]
                )
            ),
            "mean_cumulative_regret": (
                mean_floor(
                    [
                        row[
                            "cumulative_regret"
                        ]
                        for row in subset
                    ]
                )
            ),
            "total_proposed_repairs": sum(
                row["proposed_repairs"]
                for row in subset
            ),
            "total_accepted_repairs": sum(
                row["accepted_repairs"]
                for row in subset
            ),
            "total_rejected_repairs": sum(
                row["rejected_repairs"]
                for row in subset
            ),
            "mean_authorization_latency": (
                mean_floor(latencies)
            ),
            "max_authorization_latency": (
                max(latencies)
                if latencies
                else None
            ),
            "all_receipts_valid": all(
                row[
                    "receipt_chain_valid"
                ]
                for row in subset
            ),
        }

    by_depth = []

    for depth in (
        0,
        1,
        2,
        4,
    ):
        for condition in ADAPTIVE_CONDITIONS:
            subset = [
                row
                for row in rows
                if (
                    row[
                        "diagnostic_hidden_depth"
                    ] == depth
                    and row["condition"]
                    == condition
                )
            ]

            depth_counts = {}

            for row in subset:
                key = str(
                    row[
                        "final_representation_depth"
                    ]
                )

                depth_counts[key] = (
                    depth_counts.get(
                        key,
                        0,
                    )
                    + 1
                )

            latencies = [
                latency
                for row in subset
                for latency in row[
                    "authorization_latencies"
                ]
            ]

            witness_counts = {}

            for row in subset:
                for lag in row[
                    "selected_witness_lags"
                ]:
                    key = str(lag)

                    witness_counts[key] = (
                        witness_counts.get(
                            key,
                            0,
                        )
                        + 1
                    )

            by_depth.append(
                {
                    "hidden_depth": depth,
                    "condition": condition,
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
                    "mean_final_window_reward_ppm": (
                        mean_floor(
                            [
                                row[
                                    "final_window_reward_ppm"
                                ]
                                for row in subset
                            ]
                        )
                    ),
                    "final_depth_counts": (
                        depth_counts
                    ),
                    "accepted_repairs": sum(
                        row[
                            "accepted_repairs"
                        ]
                        for row in subset
                    ),
                    "rejected_repairs": sum(
                        row[
                            "rejected_repairs"
                        ]
                        for row in subset
                    ),
                    "mean_authorization_latency": (
                        mean_floor(
                            latencies
                        )
                    ),
                    "max_authorization_latency": (
                        max(latencies)
                        if latencies
                        else None
                    ),
                    "selected_witness_counts": (
                        witness_counts
                    ),
                }
            )

    by_condition_seed = {
        condition: {
            row["world_seed"]: row
            for row in rows
            if row["condition"]
            == condition
        }
        for condition
        in ADAPTIVE_CONDITIONS
    }

    def mean_pair_delta(
        left,
        right,
    ):
        values = [
            by_condition_seed[left][
                seed
            ]["primary_aulc_ppm"]
            - by_condition_seed[right][
                seed
            ]["primary_aulc_ppm"]
            for seed in DEVELOPMENT_SEEDS
        ]

        return mean_floor(
            values
        )

    full_rows = [
        row
        for row in rows
        if row["condition"]
        == "FULL-PRIME-V1.3"
    ]

    exact_recovery = sum(
        row[
            "final_representation_depth"
        ]
        == row[
            "diagnostic_hidden_depth"
        ]
        for row in full_rows
    )

    report = {
        "benchmark": (
            "prime-canonical-agent-benchmark-v1.3"
        ),
        "status": (
            "DEVELOPMENT_ONLY_NOT_EVALUATION"
        ),
        "development_seeds": list(
            DEVELOPMENT_SEEDS
        ),
        "evaluation_seeds_run": False,
        "implementation_sha256": (
            implementation_sha256()
        ),
        "frozen_identities": (
            frozen_identities()
        ),
        "fixed_h4_mean_primary_aulc_ppm": (
            mean_floor(
                fixed_h4_values
            )
        ),
        "condition_summaries": (
            summaries
        ),
        "paired_development_deltas": {
            "v13_minus_v12_reference_ppm": (
                mean_pair_delta(
                    "FULL-PRIME-V1.3",
                    "FULL-PRIME-V1.2-REFERENCE",
                )
            ),
            "factor_carrier_minus_v12_reference_ppm": (
                mean_pair_delta(
                    "FACTOR-WITNESS-CARRIER-COST",
                    "FULL-PRIME-V1.2-REFERENCE",
                )
            ),
            "v13_minus_factor_carrier_ppm": (
                mean_pair_delta(
                    "FULL-PRIME-V1.3",
                    "FACTOR-WITNESS-CARRIER-COST",
                )
            ),
        },
        "full_v13_exact_depth_recovery": (
            exact_recovery
        ),
        "full_v13_exact_depth_total": (
            len(full_rows)
        ),
        "by_hidden_depth": (
            by_depth
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
