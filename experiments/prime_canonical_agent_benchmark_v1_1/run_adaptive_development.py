"""Development-only adaptive diagnostic sweep for benchmark v1.1."""

import json

from experiments.prime_canonical_agent_benchmark_v1.manifest import (
    DEVELOPMENT_SEEDS,
)
from experiments.prime_canonical_agent_benchmark_v1.runner import (
    run_fixed_condition,
)

from .adaptive_runner import (
    ADAPTIVE_CONDITIONS,
    run_adaptive_condition,
)
from .provenance import (
    frozen_identities,
    implementation_sha256,
)


def mean_int(values: list[int]) -> int:
    return sum(values) // len(values)


def main() -> None:
    expected = tuple(range(0, 32))

    if DEVELOPMENT_SEEDS != expected:
        raise RuntimeError(
            "development seed set differs from frozen 0..31 range"
        )

    rows = []

    for seed in DEVELOPMENT_SEEDS:
        # This categorization is REPORTING ONLY.
        # Adaptive agents never receive this value.
        hidden_depth_for_diagnostics = (0, 1, 2, 4)[seed % 4]

        fixed_h4 = run_fixed_condition(
            seed,
            "FIXED-H4",
        ).payload

        for condition in ADAPTIVE_CONDITIONS:
            result = run_adaptive_condition(
                seed,
                condition,
            ).payload

            rows.append(
                {
                    "world_seed": seed,
                    "diagnostic_hidden_depth": (
                        hidden_depth_for_diagnostics
                    ),
                    "condition": condition,
                    "primary_aulc_ppm": (
                        result["primary_aulc_ppm"]
                    ),
                    "final_window_reward_ppm": (
                        result["final_window_reward_ppm"]
                    ),
                    "fixed_h4_primary_aulc_ppm": (
                        fixed_h4["primary_aulc_ppm"]
                    ),
                    "proposed_repairs": (
                        result["proposed_repairs"]
                    ),
                    "accepted_repairs": (
                        result["accepted_repairs"]
                    ),
                    "rejected_repairs": (
                        result["rejected_repairs"]
                    ),
                    "verifier_supported_repairs": (
                        result["verifier_supported_repairs"]
                    ),
                    "verifier_suppressed_repairs": (
                        result["verifier_suppressed_repairs"]
                    ),
                    "final_representation_depth": (
                        result["final_representation_depth"]
                    ),
                    "representation_change_episodes": (
                        result["representation_change_episodes"]
                    ),
                    "receipt_chain_valid": (
                        result["repair_receipt_chain_valid"]
                    ),
                }
            )

    summaries = []

    for condition in ADAPTIVE_CONDITIONS:
        condition_rows = [
            row
            for row in rows
            if row["condition"] == condition
        ]

        summaries.append(
            {
                "condition": condition,
                "mean_primary_aulc_ppm": mean_int(
                    [
                        row["primary_aulc_ppm"]
                        for row in condition_rows
                    ]
                ),
                "mean_final_window_reward_ppm": mean_int(
                    [
                        row["final_window_reward_ppm"]
                        for row in condition_rows
                    ]
                ),
                "total_proposed_repairs": sum(
                    row["proposed_repairs"]
                    for row in condition_rows
                ),
                "total_accepted_repairs": sum(
                    row["accepted_repairs"]
                    for row in condition_rows
                ),
                "total_rejected_repairs": sum(
                    row["rejected_repairs"]
                    for row in condition_rows
                ),
                "all_receipt_chains_valid": all(
                    row["receipt_chain_valid"]
                    for row in condition_rows
                ),
            }
        )

    by_depth = []

    for depth in (0, 1, 2, 4):
        for condition in ADAPTIVE_CONDITIONS:
            subset = [
                row
                for row in rows
                if (
                    row["diagnostic_hidden_depth"] == depth
                    and row["condition"] == condition
                )
            ]

            final_depth_counts = {}

            for row in subset:
                key = str(
                    row["final_representation_depth"]
                )
                final_depth_counts[key] = (
                    final_depth_counts.get(key, 0) + 1
                )

            by_depth.append(
                {
                    "diagnostic_hidden_depth": depth,
                    "condition": condition,
                    "world_count": len(subset),
                    "mean_primary_aulc_ppm": mean_int(
                        [
                            row["primary_aulc_ppm"]
                            for row in subset
                        ]
                    ),
                    "mean_final_window_reward_ppm": mean_int(
                        [
                            row["final_window_reward_ppm"]
                            for row in subset
                        ]
                    ),
                    "final_depth_counts": (
                        final_depth_counts
                    ),
                    "accepted_repairs": sum(
                        row["accepted_repairs"]
                        for row in subset
                    ),
                    "rejected_repairs": sum(
                        row["rejected_repairs"]
                        for row in subset
                    ),
                    "verifier_supported_repairs": sum(
                        row["verifier_supported_repairs"]
                        for row in subset
                    ),
                }
            )

    fixed_h4_metrics = [
        run_fixed_condition(seed, "FIXED-H4").payload[
            "primary_aulc_ppm"
        ]
        for seed in DEVELOPMENT_SEEDS
    ]

    report = {
        "status": "DEVELOPMENT_ONLY_NOT_EVALUATION",
        "evaluation_seeds_run": False,
        "frozen_identities": frozen_identities(),
        "implementation_sha256": implementation_sha256(),
        "development_seed_count": len(DEVELOPMENT_SEEDS),
        "fixed_h4_mean_primary_aulc_ppm": mean_int(
            fixed_h4_metrics
        ),
        "condition_summaries": summaries,
        "by_hidden_depth_diagnostic": by_depth,
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
