"""Frozen held-out evaluator for PRIME Canonical Agent Benchmark v1.2."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from experiments.prime_canonical_agent_benchmark_v1.deterministic import (
    splitmix64,
)
from experiments.prime_canonical_agent_benchmark_v1.runner import (
    run_fixed_condition,
)

from experiments.prime_canonical_agent_benchmark_v1_2.adaptive_runner import (
    run_adaptive_condition,
)
from experiments.prime_canonical_agent_benchmark_v1_2.manifest import (
    ADAPTIVE_CONDITIONS,
    EVALUATION_SEEDS,
)
from experiments.prime_canonical_agent_benchmark_v1_2.provenance import (
    frozen_identities,
    implementation_sha256,
)
from experiments.prime_canonical_agent_benchmark_v1_2.receipts import (
    verify_receipt_chain,
)


HERE = Path(__file__).resolve().parent
V12 = HERE.parent
REPO = V12.parent.parent

FROZEN_CORE_SHA256 = (
    "bed64cbe558c928d3793c915e34260638c9c0ed3f7061c350695e769b5c3efc9"
)

FIXED_CONDITIONS = (
    "REACTIVE",
    "FIXED-H1",
    "FIXED-H2",
    "FIXED-H4",
)

BOOTSTRAP_REPLICATES = 16384
BOOTSTRAP_SEED = 0x5052494D45563131
BOOTSTRAP_LOWER_INDEX = 409
BOOTSTRAP_UPPER_INDEX = 15974

UNLOCK = "RUN_FROZEN_EVALUATION_V1_2"


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def verify_checksum(
    target: Path,
    checksum: Path,
) -> str:
    expected = checksum.read_text(
        encoding="utf-8"
    ).split()[0]

    actual = sha256_file(target)

    if actual != expected:
        raise RuntimeError(
            f"checksum mismatch: {target}"
        )

    return actual


def git_clean() -> bool:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO),
            "status",
            "--porcelain",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip() == ""


def git_commit() -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(REPO),
            "rev-parse",
            "HEAD",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    return result.stdout.strip()


def mean_floor(values: list[int]) -> int:
    return sum(values) // len(values)


def paired_bootstrap(
    deltas: list[int],
) -> dict:
    if len(deltas) != 128:
        raise RuntimeError(
            "paired bootstrap requires exactly 128 worlds"
        )

    sums = []

    for replicate in range(
        BOOTSTRAP_REPLICATES
    ):
        total = 0

        for draw in range(128):
            value = splitmix64(
                BOOTSTRAP_SEED
                ^ splitmix64(replicate)
                ^ splitmix64(draw)
            )

            total += deltas[value % 128]

        sums.append(total)

    sums.sort()

    lower = sums[BOOTSTRAP_LOWER_INDEX]
    upper = sums[BOOTSTRAP_UPPER_INDEX]

    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "sample_size": 128,
        "seed_hex": hex(BOOTSTRAP_SEED),
        "lower_index": BOOTSTRAP_LOWER_INDEX,
        "upper_index": BOOTSTRAP_UPPER_INDEX,
        "observed_sum_delta": sum(deltas),
        "observed_mean_delta_ppm": (
            sum(deltas) // 128
        ),
        "lower_sum_delta": lower,
        "lower_mean_delta_ppm": (
            lower // 128
        ),
        "upper_sum_delta": upper,
        "upper_mean_delta_ppm": (
            upper // 128
        ),
    }


def preflight() -> dict:
    if EVALUATION_SEEDS != tuple(
        range(2000, 2128)
    ):
        raise RuntimeError(
            "frozen v1.2 evaluation seed set mismatch"
        )

    if not git_clean():
        raise RuntimeError(
            "Git worktree must be clean"
        )

    identities = frozen_identities()

    verify_checksum(
        V12 / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.json",
        V12 / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.sha256",
    )

    verify_checksum(
        V12 / "EVALUATION_ANALYSIS_PLAN.md",
        V12 / "EVALUATION_ANALYSIS_PLAN.sha256",
    )

    verify_checksum(
        HERE / "frozen_evaluation.py",
        HERE / "frozen_evaluation.sha256",
    )

    comparator = json.loads(
        (
            V12 / "DEVELOPMENT_FIXED_COMPARATOR.json"
        ).read_text()
    )

    if (
        comparator["selected_fixed_baseline"]
        != "FIXED-H4"
    ):
        raise RuntimeError(
            "frozen comparator is not FIXED-H4"
        )

    core_hash = implementation_sha256()

    if core_hash != FROZEN_CORE_SHA256:
        raise RuntimeError(
            "v1.2 core implementation hash mismatch: "
            + core_hash
        )

    return {
        "source_commit": git_commit(),
        "core_implementation_sha256": (
            core_hash
        ),
        "frozen_identities": identities,
        "selected_fixed_comparator": (
            "FIXED-H4"
        ),
        "analysis_plan_sha256": sha256_file(
            V12 / "EVALUATION_ANALYSIS_PLAN.md"
        ),
        "evaluation_harness_sha256": sha256_file(
            HERE / "frozen_evaluation.py"
        ),
    }


def receipt_diagnostics(
    result: dict,
) -> dict:
    latencies = []
    at_obstruction = []
    additional = []

    for record in result["repair_receipts"]:
        payload = record["payload"]

        latency = payload.get(
            "authorization_latency_scored_events"
        )

        if latency is not None:
            latencies.append(latency)

        before = payload.get(
            "selected_discordant_at_obstruction"
        )

        after = payload.get(
            "selected_additional_discordant_after_obstruction"
        )

        if before is not None:
            at_obstruction.append(before)

        if after is not None:
            additional.append(after)

    return {
        "latencies": latencies,
        "discordant_at_obstruction": (
            at_obstruction
        ),
        "additional_discordant": additional,
    }


def build_report() -> dict:
    preflight_record = preflight()

    rows = []

    for seed in EVALUATION_SEEDS:
        hidden_depth = (
            (0, 1, 2, 4)[seed % 4]
        )

        for condition in FIXED_CONDITIONS:
            result = run_fixed_condition(
                seed,
                condition,
            ).payload

            if result["source_dirty"]:
                raise RuntimeError(
                    "fixed condition reported dirty source"
                )

            rows.append(
                {
                    "world_seed": seed,
                    "diagnostic_hidden_depth": (
                        hidden_depth
                    ),
                    "condition": condition,
                    "primary_aulc_ppm": (
                        result["primary_aulc_ppm"]
                    ),
                    "final_window_reward_ppm": (
                        result[
                            "final_window_reward_ppm"
                        ]
                    ),
                    "cumulative_regret": (
                        result["cumulative_regret"]
                    ),
                    "final_representation_depth": (
                        result["representation_depth"]
                    ),
                    "proposed_repairs": 0,
                    "accepted_repairs": 0,
                    "rejected_repairs": 0,
                    "verifier_supported_repairs": 0,
                    "canonical_receipt_count": 0,
                    "receipt_chain_valid": True,
                    "authorization_latencies_scored_events": [],
                    "discordant_at_obstruction": [],
                    "additional_discordant_after_obstruction": [],
                }
            )

        for condition in ADAPTIVE_CONDITIONS:
            result = run_adaptive_condition(
                seed,
                condition,
                permit_evaluation=True,
            ).payload

            if result["source_dirty"]:
                raise RuntimeError(
                    "adaptive condition reported dirty source"
                )

            if (
                result["implementation_sha256"]
                != FROZEN_CORE_SHA256
            ):
                raise RuntimeError(
                    "adaptive result core hash mismatch"
                )

            receipt_ok = verify_receipt_chain(
                result["repair_receipts"],
                expected_count=(
                    result["canonical_receipt_count"]
                ),
                expected_tip=(
                    result["repair_receipt_chain_tip"]
                ),
            )

            if not receipt_ok:
                raise RuntimeError(
                    "adaptive receipt-chain failure"
                )

            diag = receipt_diagnostics(
                result
            )

            rows.append(
                {
                    "world_seed": seed,
                    "diagnostic_hidden_depth": (
                        hidden_depth
                    ),
                    "condition": condition,
                    "primary_aulc_ppm": (
                        result["primary_aulc_ppm"]
                    ),
                    "final_window_reward_ppm": (
                        result[
                            "final_window_reward_ppm"
                        ]
                    ),
                    "cumulative_regret": (
                        result["cumulative_regret"]
                    ),
                    "final_representation_depth": (
                        result[
                            "final_representation_depth"
                        ]
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
                        result[
                            "verifier_supported_repairs"
                        ]
                    ),
                    "canonical_receipt_count": (
                        result[
                            "canonical_receipt_count"
                        ]
                    ),
                    "receipt_chain_valid": receipt_ok,
                    "authorization_latencies_scored_events": (
                        diag["latencies"]
                    ),
                    "discordant_at_obstruction": (
                        diag[
                            "discordant_at_obstruction"
                        ]
                    ),
                    "additional_discordant_after_obstruction": (
                        diag["additional_discordant"]
                    ),
                }
            )

    conditions = (
        FIXED_CONDITIONS
        + ADAPTIVE_CONDITIONS
    )

    summaries = {}

    for condition in conditions:
        subset = [
            row
            for row in rows
            if row["condition"] == condition
        ]

        summaries[condition] = {
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
            "all_receipt_chains_valid": all(
                row["receipt_chain_valid"]
                for row in subset
            ),
        }

    def metric_map(
        condition: str,
        metric: str,
    ) -> dict[int, int]:
        return {
            row["world_seed"]: row[metric]
            for row in rows
            if row["condition"] == condition
        }

    full_primary = metric_map(
        "FULL-PRIME-V1.2",
        "primary_aulc_ppm",
    )

    fixed_primary = metric_map(
        "FIXED-H4",
        "primary_aulc_ppm",
    )

    ungated_primary = metric_map(
        "ADAPTIVE-NO-VERIFIER",
        "primary_aulc_ppm",
    )

    full_final = metric_map(
        "FULL-PRIME-V1.2",
        "final_window_reward_ppm",
    )

    fixed_final = metric_map(
        "FIXED-H4",
        "final_window_reward_ppm",
    )

    primary_deltas = [
        full_primary[seed]
        - fixed_primary[seed]
        for seed in EVALUATION_SEEDS
    ]

    verifier_deltas = [
        full_primary[seed]
        - ungated_primary[seed]
        for seed in EVALUATION_SEEDS
    ]

    final_deltas = [
        full_final[seed]
        - fixed_final[seed]
        for seed in EVALUATION_SEEDS
    ]

    primary_bootstrap = paired_bootstrap(
        primary_deltas
    )

    verifier_bootstrap = paired_bootstrap(
        verifier_deltas
    )

    integrity_pass = (
        git_clean()
        and all(
            summary[
                "all_receipt_chains_valid"
            ]
            for summary in summaries.values()
        )
        and all(
            summary["world_count"] == 128
            for summary in summaries.values()
        )
    )

    primary_mean_positive = (
        sum(primary_deltas) > 0
    )

    primary_lower_positive = (
        primary_bootstrap[
            "lower_sum_delta"
        ] > 0
    )

    final_not_degraded = (
        sum(final_deltas) >= 0
    )

    primary_supported = all(
        (
            primary_mean_positive,
            primary_lower_positive,
            final_not_degraded,
            integrity_pass,
        )
    )

    verifier_supported = (
        sum(verifier_deltas) > 0
        and verifier_bootstrap[
            "lower_sum_delta"
        ] > 0
        and integrity_pass
    )

    depth_diagnostics = []

    for depth in (0, 1, 2, 4):
        subset = [
            row
            for row in rows
            if (
                row["condition"]
                == "FULL-PRIME-V1.2"
                and row[
                    "diagnostic_hidden_depth"
                ] == depth
            )
        ]

        counts = {}

        for row in subset:
            key = str(
                row[
                    "final_representation_depth"
                ]
            )

            counts[key] = (
                counts.get(key, 0) + 1
            )

        latencies = [
            value
            for row in subset
            for value in row[
                "authorization_latencies_scored_events"
            ]
        ]

        extra = [
            value
            for row in subset
            for value in row[
                "additional_discordant_after_obstruction"
            ]
        ]

        depth_diagnostics.append(
            {
                "hidden_depth": depth,
                "world_count": len(subset),
                "final_depth_counts": counts,
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
                "mean_authorization_latency_scored_events": (
                    mean_floor(latencies)
                    if latencies
                    else None
                ),
                "max_authorization_latency_scored_events": (
                    max(latencies)
                    if latencies
                    else None
                ),
                "mean_additional_discordant_after_obstruction": (
                    mean_floor(extra)
                    if extra
                    else None
                ),
            }
        )

    full_rows = [
        row
        for row in rows
        if row["condition"]
        == "FULL-PRIME-V1.2"
    ]

    full_latencies = [
        value
        for row in full_rows
        for value in row[
            "authorization_latencies_scored_events"
        ]
    ]

    full_before = [
        value
        for row in full_rows
        for value in row[
            "discordant_at_obstruction"
        ]
    ]

    full_extra = [
        value
        for row in full_rows
        for value in row[
            "additional_discordant_after_obstruction"
        ]
    ]

    exact_depth = sum(
        row["final_representation_depth"]
        == row["diagnostic_hidden_depth"]
        for row in full_rows
    )

    return {
        "benchmark": (
            "prime-canonical-agent-benchmark-v1.2"
        ),
        "status": (
            "FROZEN_EVALUATION_COMPLETE"
        ),
        "evaluation_seed_count": 128,
        "evaluation_seeds": list(
            EVALUATION_SEEDS
        ),
        "preflight": preflight_record,
        "condition_summaries": summaries,
        "primary_full_vs_fixed_h4": {
            "bootstrap": primary_bootstrap,
            "mean_delta_positive": (
                primary_mean_positive
            ),
            "bootstrap_lower_positive": (
                primary_lower_positive
            ),
            "mean_final_delta_ppm": (
                sum(final_deltas) // 128
            ),
            "final_not_degraded": (
                final_not_degraded
            ),
            "integrity_pass": (
                integrity_pass
            ),
            "claim": (
                "SUPPORTED"
                if primary_supported
                else "NOT SUPPORTED"
            ),
        },
        "verifier_specific_full_vs_ungated": {
            "bootstrap": verifier_bootstrap,
            "integrity_pass": (
                integrity_pass
            ),
            "claim": (
                "SUPPORTED"
                if verifier_supported
                else "NOT SUPPORTED"
            ),
        },
        "full_prime_exact_depth_recovery": (
            exact_depth
        ),
        "full_prime_exact_depth_total": (
            len(full_rows)
        ),
        "full_prime_latency": {
            "accepted_repairs": (
                len(full_latencies)
            ),
            "mean_authorization_latency_scored_events": (
                mean_floor(full_latencies)
                if full_latencies
                else None
            ),
            "max_authorization_latency_scored_events": (
                max(full_latencies)
                if full_latencies
                else None
            ),
            "immediate_authorizations": sum(
                value == 0
                for value in full_latencies
            ),
            "mean_discordant_at_obstruction": (
                mean_floor(full_before)
                if full_before
                else None
            ),
            "mean_additional_discordant_after_obstruction": (
                mean_floor(full_extra)
                if full_extra
                else None
            ),
            "v1_1_historical_fixed_prospective_scored_events": (
                256
            ),
        },
        "full_prime_depth_diagnostics": (
            depth_diagnostics
        ),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--preflight-only",
        action="store_true",
    )

    parser.add_argument(
        "--unlock",
    )

    parser.add_argument(
        "--output",
    )

    args = parser.parse_args()

    if args.preflight_only:
        print(
            json.dumps(
                preflight(),
                sort_keys=True,
                indent=2,
            )
        )
        return

    if args.unlock != UNLOCK:
        raise SystemExit(
            "v1.2 held-out evaluation remains locked"
        )

    if not args.output:
        raise SystemExit(
            "--output is required"
        )

    output = Path(
        args.output
    ).expanduser().resolve()

    try:
        output.relative_to(
            REPO.resolve()
        )
    except ValueError:
        pass
    else:
        raise SystemExit(
            "evaluation output must be outside Git worktree"
        )

    if output.exists():
        raise SystemExit(
            "refusing to overwrite existing evaluation output"
        )

    report = build_report()

    temporary = output.with_name(
        output.name + ".partial"
    )

    temporary.write_bytes(
        canonical_bytes(report)
    )

    os.replace(
        temporary,
        output,
    )

    print(
        json.dumps(
            {
                "status": report["status"],
                "primary_claim": report[
                    "primary_full_vs_fixed_h4"
                ]["claim"],
                "verifier_specific_claim": report[
                    "verifier_specific_full_vs_ungated"
                ]["claim"],
                "output": str(output),
                "sha256": sha256_file(output),
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
