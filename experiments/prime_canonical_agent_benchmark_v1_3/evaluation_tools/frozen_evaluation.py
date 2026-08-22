"""Frozen held-out evaluator for PRIME Canonical Agent Benchmark v1.3."""

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

from experiments.prime_canonical_agent_benchmark_v1_3.adaptive_runner import (
    run_adaptive_condition,
)
from experiments.prime_canonical_agent_benchmark_v1_3.manifest import (
    ADAPTIVE_CONDITIONS,
    EVALUATION_SEEDS,
)
from experiments.prime_canonical_agent_benchmark_v1_3.provenance import (
    frozen_identities,
    implementation_sha256,
)
from experiments.prime_canonical_agent_benchmark_v1_2.receipts import (
    verify_receipt_chain,
)


HERE = Path(__file__).resolve().parent
V13 = HERE.parent
REPO = V13.parent.parent

FROZEN_CORE_SHA256 = (
    "3f8082ad340af46f786a773922ec4a5a"
    "49d42fda01f77fe658b911d44afe957e"
)

FIXED_CONDITIONS = (
    "REACTIVE",
    "FIXED-H1",
    "FIXED-H2",
    "FIXED-H4",
)

ALL_CONDITIONS = (
    FIXED_CONDITIONS
    + ADAPTIVE_CONDITIONS
)

BOOTSTRAP_REPLICATES = 16384
BOOTSTRAP_SEED = 0x5052494D45563131
BOOTSTRAP_LOWER_INDEX = 409
BOOTSTRAP_UPPER_INDEX = 15974

UNLOCK = "RUN_FROZEN_EVALUATION_V1_3"


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


def mean_floor(values: list[int]) -> int | None:
    if not values:
        return None

    return sum(values) // len(values)


def paired_bootstrap(
    deltas: list[int],
) -> dict:
    if len(deltas) != 128:
        raise RuntimeError(
            "paired bootstrap requires 128 worlds"
        )

    sums = []

    for replicate in range(
        BOOTSTRAP_REPLICATES
    ):
        total = 0

        for draw in range(128):
            index = (
                splitmix64(
                    BOOTSTRAP_SEED
                    ^ splitmix64(replicate)
                    ^ splitmix64(draw)
                )
                % 128
            )

            total += deltas[index]

        sums.append(total)

    sums.sort()

    lower = sums[
        BOOTSTRAP_LOWER_INDEX
    ]

    upper = sums[
        BOOTSTRAP_UPPER_INDEX
    ]

    observed = sum(deltas)

    return {
        "replicates": (
            BOOTSTRAP_REPLICATES
        ),
        "sample_size": 128,
        "seed_hex": hex(
            BOOTSTRAP_SEED
        ),
        "lower_index": (
            BOOTSTRAP_LOWER_INDEX
        ),
        "upper_index": (
            BOOTSTRAP_UPPER_INDEX
        ),
        "observed_sum_delta": observed,
        "observed_mean_delta_ppm": (
            observed // 128
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
        range(3000, 3128)
    ):
        raise RuntimeError(
            "v1.3 evaluation seeds changed"
        )

    if not git_clean():
        raise RuntimeError(
            "Git worktree must be clean"
        )

    identities = frozen_identities()

    verify_checksum(
        V13 / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.json",
        V13 / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.sha256",
    )

    verify_checksum(
        V13 / "EVALUATION_ANALYSIS_PLAN.md",
        V13 / "EVALUATION_ANALYSIS_PLAN.sha256",
    )

    verify_checksum(
        HERE / "frozen_evaluation.py",
        HERE / "frozen_evaluation.sha256",
    )

    diagnostic = json.loads(
        (
            V13
            / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.json"
        ).read_text()
    )

    if diagnostic[
        "evaluation_seeds_run"
    ] is not False:
        raise RuntimeError(
            "development diagnostic reports "
            "evaluation execution"
        )

    if (
        diagnostic[
            "implementation_sha256"
        ]
        != FROZEN_CORE_SHA256
    ):
        raise RuntimeError(
            "development diagnostic core mismatch"
        )

    comparator = json.loads(
        (
            V13
            / "DEVELOPMENT_FIXED_COMPARATOR.json"
        ).read_text()
    )

    if (
        comparator[
            "selected_fixed_baseline"
        ]
        != "FIXED-H4"
    ):
        raise RuntimeError(
            "frozen comparator is not FIXED-H4"
        )

    core = implementation_sha256()

    if core != FROZEN_CORE_SHA256:
        raise RuntimeError(
            "v1.3 core implementation hash mismatch: "
            + core
        )

    return {
        "source_commit": git_commit(),
        "core_implementation_sha256": (
            core
        ),
        "selected_fixed_comparator": (
            "FIXED-H4"
        ),
        "frozen_identities": (
            identities
        ),
        "development_diagnostic_sha256": (
            sha256_file(
                V13
                / "DEVELOPMENT_ADAPTIVE_DIAGNOSTIC.json"
            )
        ),
        "analysis_plan_sha256": (
            sha256_file(
                V13
                / "EVALUATION_ANALYSIS_PLAN.md"
            )
        ),
        "evaluation_harness_sha256": (
            sha256_file(
                HERE
                / "frozen_evaluation.py"
            )
        ),
    }


def receipt_diagnostics(
    result: dict,
) -> dict:
    latencies = []
    witness_lags = []

    for record in result[
        "repair_receipts"
    ]:
        payload = record[
            "payload"
        ]

        latency = payload.get(
            "authorization_latency_scored_events"
        )

        if latency is not None:
            latencies.append(
                latency
            )

        witness = payload.get(
            "selected_witness_lag"
        )

        if witness is not None:
            witness_lags.append(
                witness
            )

    return {
        "latencies": latencies,
        "selected_witness_lags": (
            witness_lags
        ),
    }


def metric_map(
    rows: list[dict],
    condition: str,
    metric: str,
) -> dict[int, int]:
    return {
        row["world_seed"]: row[
            metric
        ]
        for row in rows
        if row["condition"]
        == condition
    }


def exact_recovery_count(
    rows: list[dict],
    condition: str,
) -> int:
    return sum(
        row[
            "final_representation_depth"
        ]
        == row[
            "diagnostic_hidden_depth"
        ]
        for row in rows
        if row["condition"]
        == condition
    )


def paired_comparison(
    *,
    rows: list[dict],
    left: str,
    right: str,
    integrity_pass: bool,
    require_recovery_preservation: bool,
) -> dict:
    left_primary = metric_map(
        rows,
        left,
        "primary_aulc_ppm",
    )

    right_primary = metric_map(
        rows,
        right,
        "primary_aulc_ppm",
    )

    left_final = metric_map(
        rows,
        left,
        "final_window_reward_ppm",
    )

    right_final = metric_map(
        rows,
        right,
        "final_window_reward_ppm",
    )

    deltas = [
        left_primary[seed]
        - right_primary[seed]
        for seed in EVALUATION_SEEDS
    ]

    final_deltas = [
        left_final[seed]
        - right_final[seed]
        for seed in EVALUATION_SEEDS
    ]

    bootstrap = paired_bootstrap(
        deltas
    )

    mean_positive = (
        sum(deltas) > 0
    )

    lower_positive = (
        bootstrap[
            "lower_sum_delta"
        ] > 0
    )

    final_not_degraded = (
        sum(final_deltas) >= 0
    )

    left_recovery = (
        exact_recovery_count(
            rows,
            left,
        )
    )

    right_recovery = (
        exact_recovery_count(
            rows,
            right,
        )
    )

    recovery_preserved = (
        left_recovery
        >= right_recovery
    )

    criteria = [
        mean_positive,
        lower_positive,
        final_not_degraded,
        integrity_pass,
    ]

    if require_recovery_preservation:
        criteria.append(
            recovery_preserved
        )

    supported = all(
        criteria
    )

    return {
        "left_condition": left,
        "right_condition": right,
        "bootstrap": bootstrap,
        "mean_delta_positive": (
            mean_positive
        ),
        "bootstrap_lower_positive": (
            lower_positive
        ),
        "mean_final_delta_ppm": (
            sum(final_deltas) // 128
        ),
        "final_not_degraded": (
            final_not_degraded
        ),
        "left_exact_depth_recovery": (
            left_recovery
        ),
        "right_exact_depth_recovery": (
            right_recovery
        ),
        "recovery_preserved": (
            recovery_preserved
        ),
        "recovery_preservation_required": (
            require_recovery_preservation
        ),
        "integrity_pass": (
            integrity_pass
        ),
        "claim": (
            "SUPPORTED"
            if supported
            else "NOT SUPPORTED"
        ),
    }


def diagnostic_comparison(
    rows: list[dict],
    left: str,
    right: str,
) -> dict:
    left_primary = metric_map(
        rows,
        left,
        "primary_aulc_ppm",
    )

    right_primary = metric_map(
        rows,
        right,
        "primary_aulc_ppm",
    )

    deltas = [
        left_primary[seed]
        - right_primary[seed]
        for seed in EVALUATION_SEEDS
    ]

    return {
        "left_condition": left,
        "right_condition": right,
        "bootstrap": paired_bootstrap(
            deltas
        ),
        "status": "DIAGNOSTIC_ONLY",
    }


def build_report() -> dict:
    preflight_record = preflight()

    rows = []

    for seed in EVALUATION_SEEDS:
        hidden_depth = (
            (0, 1, 2, 4)[
                seed % 4
            ]
        )

        for condition in FIXED_CONDITIONS:
            result = run_fixed_condition(
                seed,
                condition,
            ).payload

            if result[
                "source_dirty"
            ]:
                raise RuntimeError(
                    "fixed result reports dirty source"
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
                    "final_representation_depth": (
                        result[
                            "representation_depth"
                        ]
                    ),
                    "proposed_repairs": 0,
                    "accepted_repairs": 0,
                    "rejected_repairs": 0,
                    "verifier_supported_repairs": 0,
                    "receipt_chain_valid": True,
                    "authorization_latencies": [],
                    "selected_witness_lags": [],
                }
            )

        for condition in ADAPTIVE_CONDITIONS:
            result = run_adaptive_condition(
                seed,
                condition,
                permit_evaluation=True,
            ).payload

            if result[
                "source_dirty"
            ]:
                raise RuntimeError(
                    "adaptive result reports dirty source"
                )

            if (
                result[
                    "source_commit"
                ]
                != preflight_record[
                    "source_commit"
                ]
            ):
                raise RuntimeError(
                    "adaptive source commit mismatch"
                )

            if (
                result[
                    "implementation_sha256"
                ]
                != FROZEN_CORE_SHA256
            ):
                raise RuntimeError(
                    "adaptive core hash mismatch"
                )

            receipt_ok = (
                verify_receipt_chain(
                    result[
                        "repair_receipts"
                    ],
                    expected_count=(
                        result[
                            "canonical_receipt_count"
                        ]
                    ),
                    expected_tip=(
                        result[
                            "repair_receipt_chain_tip"
                        ]
                    ),
                )
            )

            if not receipt_ok:
                raise RuntimeError(
                    "receipt-chain failure"
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
                    "final_representation_depth": (
                        result[
                            "final_representation_depth"
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
                    "verifier_supported_repairs": (
                        result[
                            "verifier_supported_repairs"
                        ]
                    ),
                    "receipt_chain_valid": (
                        receipt_ok
                    ),
                    "authorization_latencies": (
                        diag[
                            "latencies"
                        ]
                    ),
                    "selected_witness_lags": (
                        diag[
                            "selected_witness_lags"
                        ]
                    ),
                }
            )

    summaries = {}

    for condition in ALL_CONDITIONS:
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
                row[
                    "proposed_repairs"
                ]
                for row in subset
            ),
            "total_accepted_repairs": sum(
                row[
                    "accepted_repairs"
                ]
                for row in subset
            ),
            "total_rejected_repairs": sum(
                row[
                    "rejected_repairs"
                ]
                for row in subset
            ),
            "total_verifier_supported_repairs": sum(
                row[
                    "verifier_supported_repairs"
                ]
                for row in subset
            ),
            "exact_depth_recovery": (
                exact_recovery_count(
                    rows,
                    condition,
                )
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
            "immediate_authorizations": sum(
                latency == 0
                for latency in latencies
            ),
            "all_receipt_chains_valid": all(
                row[
                    "receipt_chain_valid"
                ]
                for row in subset
            ),
        }

    integrity_pass = (
        git_clean()
        and len(rows)
        == 128 * len(
            ALL_CONDITIONS
        )
        and all(
            summary[
                "world_count"
            ] == 128
            for summary
            in summaries.values()
        )
        and all(
            summary[
                "all_receipt_chains_valid"
            ]
            for summary
            in summaries.values()
        )
    )

    primary_upgrade = (
        paired_comparison(
            rows=rows,
            left="FULL-PRIME-V1.3",
            right=(
                "FULL-PRIME-V1.2-REFERENCE"
            ),
            integrity_pass=(
                integrity_pass
            ),
            require_recovery_preservation=True,
        )
    )

    fixed_h4 = paired_comparison(
        rows=rows,
        left="FULL-PRIME-V1.3",
        right="FIXED-H4",
        integrity_pass=(
            integrity_pass
        ),
        require_recovery_preservation=False,
    )

    factorization = (
        paired_comparison(
            rows=rows,
            left=(
                "FACTOR-WITNESS-CARRIER-COST"
            ),
            right=(
                "FULL-PRIME-V1.2-REFERENCE"
            ),
            integrity_pass=(
                integrity_pass
            ),
            require_recovery_preservation=True,
        )
    )

    repricing = (
        diagnostic_comparison(
            rows,
            "FULL-PRIME-V1.3",
            "FACTOR-WITNESS-CARRIER-COST",
        )
    )

    adaptive_diagnostics = {}

    diagnostic_conditions = (
        "FULL-PRIME-V1.2-REFERENCE",
        "FACTOR-WITNESS-CARRIER-COST",
        "FULL-PRIME-V1.3",
    )

    for condition in diagnostic_conditions:
        entries = []

        for depth in (
            0,
            1,
            2,
            4,
        ):
            subset = [
                row
                for row in rows
                if (
                    row[
                        "condition"
                    ] == condition
                    and row[
                        "diagnostic_hidden_depth"
                    ] == depth
                )
            ]

            depth_counts = {}

            witness_counts = {}

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

                for lag in row[
                    "selected_witness_lags"
                ]:
                    lag_key = str(
                        lag
                    )

                    witness_counts[
                        lag_key
                    ] = (
                        witness_counts.get(
                            lag_key,
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

            entries.append(
                {
                    "hidden_depth": depth,
                    "world_count": len(
                        subset
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
                    "mean_final_window_reward_ppm": (
                        mean_floor(
                            [
                                row[
                                    "final_window_reward_ppm"
                                ]
                                for row
                                in subset
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
                        max(
                            latencies
                        )
                        if latencies
                        else None
                    ),
                    "immediate_authorizations": sum(
                        latency == 0
                        for latency
                        in latencies
                    ),
                    "selected_witness_counts": (
                        witness_counts
                    ),
                }
            )

        adaptive_diagnostics[
            condition
        ] = entries

    return {
        "benchmark": (
            "prime-canonical-agent-benchmark-v1.3"
        ),
        "status": (
            "FROZEN_EVALUATION_COMPLETE"
        ),
        "evaluation_seed_count": 128,
        "evaluation_seeds": list(
            EVALUATION_SEEDS
        ),
        "condition_count": len(
            ALL_CONDITIONS
        ),
        "row_count": len(rows),
        "preflight": (
            preflight_record
        ),
        "condition_summaries": (
            summaries
        ),
        "primary_upgrade_v13_vs_v12_reference": (
            primary_upgrade
        ),
        "fixed_h4_comparison": (
            fixed_h4
        ),
        "factorization_only_comparison": (
            factorization
        ),
        "repricing_diagnostic": (
            repricing
        ),
        "adaptive_depth_diagnostics": (
            adaptive_diagnostics
        ),
        "integrity_pass": (
            integrity_pass
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
            "v1.3 held-out evaluation remains locked"
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
        canonical_bytes(
            report
        )
    )

    os.replace(
        temporary,
        output,
    )

    print(
        json.dumps(
            {
                "status": (
                    report[
                        "status"
                    ]
                ),
                "primary_upgrade_claim": (
                    report[
                        "primary_upgrade_v13_vs_v12_reference"
                    ]["claim"]
                ),
                "fixed_h4_claim": (
                    report[
                        "fixed_h4_comparison"
                    ]["claim"]
                ),
                "factorization_claim": (
                    report[
                        "factorization_only_comparison"
                    ]["claim"]
                ),
                "output": str(
                    output
                ),
                "sha256": (
                    sha256_file(
                        output
                    )
                ),
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
