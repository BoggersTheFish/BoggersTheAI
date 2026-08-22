"""Development-only diagnostic sweep for PRIME benchmark v1.2."""

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
)
from .provenance import (
    frozen_identities,
    implementation_sha256,
)
from .receipts import verify_receipt_chain


def mean_floor(values: list[int]) -> int | None:
    if not values:
        return None
    return sum(values) // len(values)


def main() -> None:
    if DEVELOPMENT_SEEDS != tuple(range(100, 132)):
        raise RuntimeError(
            "v1.2 development seed set changed"
        )

    rows = []

    for seed in DEVELOPMENT_SEEDS:
        diagnostic_depth = (0, 1, 2, 4)[seed % 4]

        fixed_h4 = run_fixed_condition(
            seed,
            "FIXED-H4",
        ).payload

        for condition in ADAPTIVE_CONDITIONS:
            result = run_adaptive_condition(
                seed,
                condition,
            ).payload

            receipt_ok = verify_receipt_chain(
                result["repair_receipts"],
                expected_count=(
                    result["canonical_receipt_count"]
                ),
                expected_tip=(
                    result["repair_receipt_chain_tip"]
                ),
            )

            receipt_latencies = []
            discordant_at_obstruction = []
            additional_discordant = []

            for record in result["repair_receipts"]:
                payload = record["payload"]

                latency = payload.get(
                    "authorization_latency_scored_events"
                )

                if latency is not None:
                    receipt_latencies.append(latency)

                before = payload.get(
                    "selected_discordant_at_obstruction"
                )

                after = payload.get(
                    "selected_additional_discordant_after_obstruction"
                )

                if before is not None:
                    discordant_at_obstruction.append(before)

                if after is not None:
                    additional_discordant.append(after)

            rows.append(
                {
                    "world_seed": seed,
                    "diagnostic_hidden_depth": diagnostic_depth,
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
                    "cumulative_regret": (
                        result["cumulative_regret"]
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
                    "authorization_latencies_scored_events": (
                        receipt_latencies
                    ),
                    "discordant_at_obstruction": (
                        discordant_at_obstruction
                    ),
                    "additional_discordant_after_obstruction": (
                        additional_discordant
                    ),
                    "canonical_receipt_count": (
                        result["canonical_receipt_count"]
                    ),
                    "receipt_chain_valid": receipt_ok,
                }
            )

    condition_summaries = []

    for condition in ADAPTIVE_CONDITIONS:
        subset = [
            row
            for row in rows
            if row["condition"] == condition
        ]

        latencies = [
            latency
            for row in subset
            for latency in row[
                "authorization_latencies_scored_events"
            ]
        ]

        before = [
            value
            for row in subset
            for value in row["discordant_at_obstruction"]
        ]

        additional = [
            value
            for row in subset
            for value in row[
                "additional_discordant_after_obstruction"
            ]
        ]

        condition_summaries.append(
            {
                "condition": condition,
                "world_count": len(subset),
                "mean_primary_aulc_ppm": mean_floor(
                    [
                        row["primary_aulc_ppm"]
                        for row in subset
                    ]
                ),
                "mean_final_window_reward_ppm": mean_floor(
                    [
                        row["final_window_reward_ppm"]
                        for row in subset
                    ]
                ),
                "mean_cumulative_regret": mean_floor(
                    [
                        row["cumulative_regret"]
                        for row in subset
                    ]
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
                "mean_authorization_latency_scored_events": (
                    mean_floor(latencies)
                ),
                "max_authorization_latency_scored_events": (
                    max(latencies)
                    if latencies
                    else None
                ),
                "immediate_authorizations": sum(
                    latency == 0
                    for latency in latencies
                ),
                "mean_discordant_at_obstruction": (
                    mean_floor(before)
                ),
                "mean_additional_discordant_after_obstruction": (
                    mean_floor(additional)
                ),
                "all_receipt_chains_valid": all(
                    row["receipt_chain_valid"]
                    for row in subset
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

            final_counts = {}

            for row in subset:
                key = str(
                    row["final_representation_depth"]
                )
                final_counts[key] = (
                    final_counts.get(key, 0) + 1
                )

            latencies = [
                latency
                for row in subset
                for latency in row[
                    "authorization_latencies_scored_events"
                ]
            ]

            additional = [
                value
                for row in subset
                for value in row[
                    "additional_discordant_after_obstruction"
                ]
            ]

            by_depth.append(
                {
                    "diagnostic_hidden_depth": depth,
                    "condition": condition,
                    "world_count": len(subset),
                    "mean_primary_aulc_ppm": mean_floor(
                        [
                            row["primary_aulc_ppm"]
                            for row in subset
                        ]
                    ),
                    "mean_final_window_reward_ppm": mean_floor(
                        [
                            row["final_window_reward_ppm"]
                            for row in subset
                        ]
                    ),
                    "final_depth_counts": final_counts,
                    "accepted_repairs": sum(
                        row["accepted_repairs"]
                        for row in subset
                    ),
                    "rejected_repairs": sum(
                        row["rejected_repairs"]
                        for row in subset
                    ),
                    "mean_authorization_latency_scored_events": (
                        mean_floor(latencies)
                    ),
                    "max_authorization_latency_scored_events": (
                        max(latencies)
                        if latencies
                        else None
                    ),
                    "mean_additional_discordant_after_obstruction": (
                        mean_floor(additional)
                    ),
                }
            )

    full_rows = [
        row
        for row in rows
        if row["condition"] == "FULL-PRIME-V1.2"
    ]

    exact_depth_recovery = sum(
        row["final_representation_depth"]
        == row["diagnostic_hidden_depth"]
        for row in full_rows
    )

    fixed_h4_metrics = [
        run_fixed_condition(
            seed,
            "FIXED-H4",
        ).payload["primary_aulc_ppm"]
        for seed in DEVELOPMENT_SEEDS
    ]

    report = {
        "benchmark": "prime-canonical-agent-benchmark-v1.2",
        "status": "DEVELOPMENT_ONLY_NOT_EVALUATION",
        "evaluation_seeds_run": False,
        "development_seeds": list(DEVELOPMENT_SEEDS),
        "implementation_sha256": implementation_sha256(),
        "frozen_identities": frozen_identities(),
        "fixed_h4_mean_primary_aulc_ppm": (
            mean_floor(fixed_h4_metrics)
        ),
        "full_prime_exact_depth_recovery": (
            exact_depth_recovery
        ),
        "full_prime_exact_depth_total": len(full_rows),
        "condition_summaries": condition_summaries,
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
