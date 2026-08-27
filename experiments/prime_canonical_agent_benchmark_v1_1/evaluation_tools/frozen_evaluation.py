"""One-shot frozen evaluation harness for PRIME benchmark v1.1."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

from experiments.prime_canonical_agent_benchmark_v1.deterministic import (
    splitmix64,
)
from experiments.prime_canonical_agent_benchmark_v1.manifest import (
    EVALUATION_SEEDS,
)
from experiments.prime_canonical_agent_benchmark_v1.runner import (
    run_fixed_condition,
)
from experiments.prime_canonical_agent_benchmark_v1_1.adaptive_runner import (
    ADAPTIVE_CONDITIONS,
    run_adaptive_condition,
)
from experiments.prime_canonical_agent_benchmark_v1_1.provenance import (
    frozen_identities,
    implementation_sha256,
)
from experiments.prime_canonical_agent_benchmark_v1_1.receipts import (
    verify_receipt_chain,
)


HERE = Path(__file__).resolve().parent
V11 = HERE.parent
REPO = V11.parent.parent

FROZEN_CORE_IMPLEMENTATION_SHA256 = (
    "b98a84c501979eb05d221bdfb603dfb68895ee541696d7a7c80045feb7a8bb6f"
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

UNLOCK_PHRASE = "RUN_FROZEN_EVALUATION_V1_1"


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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_checksum(
    target: Path,
    checksum_file: Path,
) -> str:
    expected = checksum_file.read_text(
        encoding="utf-8"
    ).split()[0]

    actual = sha256_file(target)

    if actual != expected:
        raise RuntimeError(
            f"checksum mismatch: {target}"
        )

    return actual


def git_status_clean() -> bool:
    result = subprocess.run(
        ["git", "-C", str(REPO), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == ""


def git_commit() -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def mean_floor(values: list[int]) -> int:
    return sum(values) // len(values)


def paired_bootstrap(deltas: list[int]) -> dict:
    n = len(deltas)

    if n != 128:
        raise RuntimeError(
            f"expected 128 paired deltas, got {n}"
        )

    replicate_sums = []

    for replicate in range(BOOTSTRAP_REPLICATES):
        total = 0

        for draw in range(n):
            value = splitmix64(
                BOOTSTRAP_SEED
                ^ splitmix64(replicate)
                ^ splitmix64(draw)
            )

            total += deltas[value % n]

        replicate_sums.append(total)

    replicate_sums.sort()

    lower_sum = replicate_sums[
        BOOTSTRAP_LOWER_INDEX
    ]
    upper_sum = replicate_sums[
        BOOTSTRAP_UPPER_INDEX
    ]

    return {
        "replicates": BOOTSTRAP_REPLICATES,
        "sample_size": n,
        "seed_hex": hex(BOOTSTRAP_SEED),
        "lower_index": BOOTSTRAP_LOWER_INDEX,
        "upper_index": BOOTSTRAP_UPPER_INDEX,
        "observed_sum_delta": sum(deltas),
        "observed_mean_delta_ppm": (
            sum(deltas) // n
        ),
        "lower_sum_delta": lower_sum,
        "lower_mean_delta_ppm": (
            lower_sum // n
        ),
        "upper_sum_delta": upper_sum,
        "upper_mean_delta_ppm": (
            upper_sum // n
        ),
    }


def preflight() -> dict:
    expected_seeds = tuple(range(1000, 1128))

    if EVALUATION_SEEDS != expected_seeds:
        raise RuntimeError(
            "frozen evaluation seed set mismatch"
        )

    if not git_status_clean():
        raise RuntimeError(
            "Git worktree must be clean before evaluation"
        )

    identities = frozen_identities()

    verify_checksum(
        V11 / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.json",
        V11 / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.sha256",
    )

    verify_checksum(
        V11 / "EVALUATION_ANALYSIS_PLAN.md",
        V11 / "EVALUATION_ANALYSIS_PLAN.sha256",
    )

    verify_checksum(
        HERE / "frozen_evaluation.py",
        HERE / "frozen_evaluation.sha256",
    )

    core_hash = implementation_sha256()

    if core_hash != FROZEN_CORE_IMPLEMENTATION_SHA256:
        raise RuntimeError(
            "core implementation differs from development freeze: "
            f"{core_hash}"
        )

    return {
        "source_commit": git_commit(),
        "core_implementation_sha256": core_hash,
        "frozen_identities": identities,
        "analysis_plan_sha256": sha256_file(
            V11 / "EVALUATION_ANALYSIS_PLAN.md"
        ),
        "evaluation_harness_sha256": sha256_file(
            HERE / "frozen_evaluation.py"
        ),
    }


def build_report() -> dict:
    preflight_record = preflight()
    rows = []

    for seed in EVALUATION_SEEDS:
        diagnostic_depth = (0, 1, 2, 4)[seed % 4]

        for condition in FIXED_CONDITIONS:
            result = run_fixed_condition(
                seed,
                condition,
            ).payload

            if result["source_dirty"]:
                raise RuntimeError(
                    "fixed result reports dirty source"
                )

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
                    "deterministic_run_identity": (
                        result["implementation_sha256"]
                        + ":"
                        + str(seed)
                        + ":"
                        + condition
                    ),
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
                    "adaptive result reports dirty source"
                )

            if not verify_receipt_chain(
                result["repair_receipts"]
            ):
                raise RuntimeError(
                    "adaptive receipt chain failed"
                )

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
                    "cumulative_regret": (
                        result["cumulative_regret"]
                    ),
                    "final_representation_depth": (
                        result["final_representation_depth"]
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
                    "canonical_receipt_count": (
                        result["canonical_receipt_count"]
                    ),
                    "receipt_chain_valid": (
                        result["repair_receipt_chain_valid"]
                    ),
                    "adaptation_latencies_episodes": (
                        result["adaptation_latencies_episodes"]
                    ),
                    "deterministic_run_identity": (
                        result["deterministic_run_identity"]
                    ),
                }
            )

    by_condition = {}

    conditions = FIXED_CONDITIONS + ADAPTIVE_CONDITIONS

    for condition in conditions:
        subset = [
            row
            for row in rows
            if row["condition"] == condition
        ]

        by_condition[condition] = {
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
        "FULL-PRIME",
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
        "FULL-PRIME",
        "final_window_reward_ppm",
    )
    fixed_final = metric_map(
        "FIXED-H4",
        "final_window_reward_ppm",
    )

    primary_deltas = [
        full_primary[seed] - fixed_primary[seed]
        for seed in EVALUATION_SEEDS
    ]

    verifier_deltas = [
        full_primary[seed] - ungated_primary[seed]
        for seed in EVALUATION_SEEDS
    ]

    final_deltas = [
        full_final[seed] - fixed_final[seed]
        for seed in EVALUATION_SEEDS
    ]

    primary_bootstrap = paired_bootstrap(
        primary_deltas
    )
    verifier_bootstrap = paired_bootstrap(
        verifier_deltas
    )

    primary_mean_positive = (
        sum(primary_deltas) > 0
    )

    primary_ci_positive = (
        primary_bootstrap["lower_sum_delta"] > 0
    )

    final_not_degraded = (
        sum(final_deltas) >= 0
    )

    integrity_pass = (
        all(
            summary["all_receipt_chains_valid"]
            for summary in by_condition.values()
        )
        and git_status_clean()
    )

    primary_supported = all(
        (
            primary_mean_positive,
            primary_ci_positive,
            final_not_degraded,
            integrity_pass,
        )
    )

    verifier_specific_supported = (
        sum(verifier_deltas) > 0
        and verifier_bootstrap["lower_sum_delta"] > 0
    )

    depth_diagnostics = []

    for depth in (0, 1, 2, 4):
        subset = [
            row
            for row in rows
            if (
                row["condition"] == "FULL-PRIME"
                and row["diagnostic_hidden_depth"] == depth
            )
        ]

        counts = {}

        for row in subset:
            key = str(
                row["final_representation_depth"]
            )
            counts[key] = counts.get(key, 0) + 1

        depth_diagnostics.append(
            {
                "hidden_depth": depth,
                "world_count": len(subset),
                "final_depth_counts": counts,
                "mean_primary_aulc_ppm": mean_floor(
                    [
                        row["primary_aulc_ppm"]
                        for row in subset
                    ]
                ),
            }
        )

    report = {
        "benchmark": (
            "prime-canonical-agent-benchmark-v1.1"
        ),
        "status": "FROZEN_EVALUATION_COMPLETE",
        "evaluation_seed_count": len(
            EVALUATION_SEEDS
        ),
        "evaluation_seeds": list(
            EVALUATION_SEEDS
        ),
        "preflight": preflight_record,
        "condition_summaries": by_condition,
        "primary_comparison_full_vs_fixed_h4": {
            "bootstrap": primary_bootstrap,
            "mean_delta_positive": (
                primary_mean_positive
            ),
            "bootstrap_lower_positive": (
                primary_ci_positive
            ),
            "mean_final_delta_ppm": (
                sum(final_deltas)
                // len(final_deltas)
            ),
            "final_not_degraded": (
                final_not_degraded
            ),
            "integrity_pass": integrity_pass,
            "claim": (
                "SUPPORTED"
                if primary_supported
                else "NOT SUPPORTED"
            ),
        },
        "verifier_specific_full_vs_adaptive_no_verifier": {
            "bootstrap": verifier_bootstrap,
            "claim": (
                "SUPPORTED"
                if verifier_specific_supported
                else "NOT SUPPORTED"
            ),
        },
        "full_prime_depth_diagnostics": (
            depth_diagnostics
        ),
        "rows": rows,
    }

    return report


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--unlock",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    args = parser.parse_args()

    if args.unlock != UNLOCK_PHRASE:
        raise SystemExit(
            "frozen evaluation remains locked"
        )

    output = Path(args.output).resolve()

    try:
        output.relative_to(REPO.resolve())
    except ValueError:
        pass
    else:
        raise SystemExit(
            "evaluation output must be outside Git worktree"
        )

    if output.exists():
        raise SystemExit(
            f"refusing to overwrite existing output: {output}"
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
                "claim": report[
                    "primary_comparison_full_vs_fixed_h4"
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
