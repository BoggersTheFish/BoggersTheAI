"""Run v0.2 Scale-Free Failure Decomposition."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from thinking_system.benchmarks.graph_scaling.receipts import (
    build_receipt,
    stable_hash,
    write_json,
)
from thinking_system.benchmarks.graph_scaling.tasks.failure_decomposition import (
    decompose_scale_free_failure,
)
from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    RelaxationConfig,
    generate_graph,
    run_relaxation,
)


def _split_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def run_decomposition(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    config = RelaxationConfig(
        steps=args.steps,
        learning_rate=args.learning_rate,
        damping=args.damping,
        tolerance=args.tolerance,
        frontier=not args.no_frontier,
        provenance_weighting=not args.no_provenance_weighting,
    )
    runs: list[dict[str, Any]] = []
    for nodes in _split_ints(args.sizes):
        graph = generate_graph(
            graph_type="scale_free",
            nodes=nodes,
            seed=args.seed,
            avg_degree=args.avg_degree,
            contradiction_rate=args.contradiction_rate,
        )
        result = run_relaxation(graph, config)
        decomposition = decompose_scale_free_failure(graph, result, config)
        runs.append(
            {
                "run_id": f"scale-free-decomposition-{nodes}-seed{args.seed}",
                "graph": {
                    "type": graph.spec.graph_type,
                    "nodes": graph.spec.nodes,
                    "edges": graph.spec.edges,
                    "seed": graph.spec.seed,
                    "contradiction_pairs": graph.spec.contradiction_pairs,
                },
                "config": config_payload(args, config),
                "metrics": result.metrics,
                "decomposition": decomposition,
            }
        )

    aggregate = aggregate_decompositions(runs)
    payload = {
        "task": "Scale-Free Failure Decomposition",
        "version": "v0.2",
        "run_id": f"scale-free-decomposition-seed{args.seed}",
        "central_question": (
            "Is scale-free failure caused by hub dominance, bad relaxation damping, "
            "poor contradiction scoring, or the active-frontier policy starving low-degree regions?"
        ),
        "runs": runs,
        "aggregate": aggregate,
    }
    json_path = out_dir / "scale_free_failure_decomposition.json"
    report_path = out_dir / "SCALE_FREE_FAILURE_DECOMPOSITION.md"
    write_json(json_path, payload)
    write_report(payload, report_path)

    repo_root = Path(__file__).resolve().parents[5]
    receipt = build_receipt(
        run_id=str(payload["run_id"]),
        repo_root=repo_root,
        command=" ".join(sys.argv),
        dataset={
            "name": "synthetic-scale_free-failure-decomposition",
            "version": "v0.2",
            "hash": stable_hash(
                {
                    "sizes": _split_ints(args.sizes),
                    "seed": args.seed,
                    "avg_degree": args.avg_degree,
                    "contradiction_rate": args.contradiction_rate,
                }
            ),
        },
        system={
            "name": "ts-core-reference-relaxation",
            "variant": "scale-free-failure-decomposition",
        },
        config=config_payload(args, config),
        metrics=aggregate,
        graph_family="scale_free",
        known_caveats=[
            "Synthetic scale-free decomposition only; this does not test real knowledge graphs.",
            "This task diagnoses failure modes and intentionally does not change relaxation behavior.",
            "Failure labels are heuristic and should guide experiments, not serve as proof.",
        ],
        artifacts=[json_path, report_path],
    )
    receipt_path = out_dir / "scale_free_failure_decomposition.receipt.json"
    write_json(receipt_path, receipt)
    payload["receipt_path"] = str(receipt_path)
    write_json(json_path, payload)
    return payload


def config_payload(
    args: argparse.Namespace, config: RelaxationConfig
) -> dict[str, Any]:
    return {
        "seed": args.seed,
        "avg_degree": args.avg_degree,
        "contradiction_rate": args.contradiction_rate,
        "steps": config.steps,
        "learning_rate": config.learning_rate,
        "damping": config.damping,
        "tolerance": config.tolerance,
        "frontier": config.frontier,
        "provenance_weighting": config.provenance_weighting,
    }


def aggregate_decompositions(runs: list[dict[str, Any]]) -> dict[str, Any]:
    primary_counts: dict[str, int] = {}
    hub_shares: list[float] = []
    frontier_churn_rates: list[float] = []
    plateau_slopes: list[float] = []
    best_ranks: list[int] = []
    for run in runs:
        metrics = run["decomposition"]["metrics"]
        diagnosis = run["decomposition"]["diagnosis"]
        primary = diagnosis["primary"]
        primary_counts[primary] = primary_counts.get(primary, 0) + 1
        hub_shares.append(float(metrics["hub_residual_share"]))
        frontier_churn_rates.append(float(metrics["frontier_churn_rate"]))
        plateau_slopes.append(float(metrics["plateau_residual_slope"]))
        best_ranks.append(
            int(metrics["contradiction_rank_of_planted_edge"]["best_rank"])
        )
    dominant = (
        max(primary_counts.items(), key=lambda item: item[1])[0]
        if primary_counts
        else "none"
    )
    return {
        "run_count": len(runs),
        "primary_failure_counts": primary_counts,
        "dominant_failure_mode": dominant,
        "mean_hub_residual_share": (
            sum(hub_shares) / len(hub_shares) if hub_shares else 0.0
        ),
        "mean_frontier_churn_rate": (
            sum(frontier_churn_rates) / len(frontier_churn_rates)
            if frontier_churn_rates
            else 0.0
        ),
        "mean_plateau_residual_slope": (
            sum(plateau_slopes) / len(plateau_slopes) if plateau_slopes else 0.0
        ),
        "best_planted_contradiction_ranks": best_ranks,
    }


def write_report(payload: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# Scale-Free Failure Decomposition",
        "",
        "v0.2 does not fix the scale-free failure. It makes the failure sharper.",
        "",
        f"Central question: {payload['central_question']}",
        "",
        "## Aggregate Diagnosis",
        "",
        f"- Dominant failure mode: `{payload['aggregate']['dominant_failure_mode']}`",
        f"- Mean hub residual share: {payload['aggregate']['mean_hub_residual_share']:.3f}",
        f"- Mean frontier churn rate: {payload['aggregate']['mean_frontier_churn_rate']:.6f}",
        f"- Mean plateau residual slope: {payload['aggregate']['mean_plateau_residual_slope']:.8f}",
        "",
        "## Run Metrics",
        "",
        "| Run | Nodes | Final tension | F1 | Hub share | Hub/nonhub ratio | Frontier churn | Plateau slope | Best planted rank | Primary |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for run in payload["runs"]:
        metrics = run["decomposition"]["metrics"]
        diagnosis = run["decomposition"]["diagnosis"]
        rank = metrics["contradiction_rank_of_planted_edge"]
        lines.append(
            "| {run_id} | {nodes} | {final_tension:.6f} | {f1:.3f} | {hub:.3f} | {ratio:.3f} | {churn:.6f} | {slope:.8f} | {rank} | {primary} |".format(
                run_id=run["run_id"],
                nodes=run["graph"]["nodes"],
                final_tension=float(run["metrics"]["final_global_tension"]),
                f1=float(run["metrics"]["contradiction_localization_f1"]),
                hub=float(metrics["hub_residual_share"]),
                ratio=float(metrics["hub_to_nonhub_residual_ratio"]),
                churn=float(metrics["frontier_churn_rate"]),
                slope=float(metrics["plateau_residual_slope"]),
                rank=rank["best_rank"],
                primary=diagnosis["primary"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- `hub_dominance_problem`: high-degree nodes account for most residual tension.",
            "- `damping_or_plateau_problem`: high residual tension remains while the residual slope is effectively flat.",
            "- `localization_problem`: planted contradiction edges are not ranked near the top of residual tension.",
            "- `frontier_policy_problem`: active frontier size is effectively static, so update policy is not focusing work.",
            "",
            "## Claim Boundary",
            "",
            "> v0.2 diagnoses failure modes. It does not claim TS-Core scales cleanly and does not introduce a fix.",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="100,1000,10000")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--avg-degree", type=int, default=6)
    parser.add_argument("--contradiction-rate", type=float, default=0.01)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.12)
    parser.add_argument("--damping", type=float, default=0.85)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--no-frontier", action="store_true")
    parser.add_argument("--no-provenance-weighting", action="store_true")
    parser.add_argument("--out-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_decomposition(args)
    print(
        json.dumps(
            {
                "run_id": payload["run_id"],
                "dominant_failure_mode": payload["aggregate"]["dominant_failure_mode"],
                "receipt_path": payload["receipt_path"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
