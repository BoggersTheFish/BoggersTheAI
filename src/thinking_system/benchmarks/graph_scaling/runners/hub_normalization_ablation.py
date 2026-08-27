"""Run v0.3 hub-normalized relaxation ablation.

This runner compares experimental hub-aware policies against the v0.1/v0.2
reference behavior. It does not declare a fix.
"""

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
from thinking_system.benchmarks.graph_scaling.runners.scale_graph import (
    build_parser as build_scale_parser,
)
from thinking_system.benchmarks.graph_scaling.runners.scale_graph import (
    run_one,
)

VARIANTS = ["reference", "degree_normalized", "hub_damping", "residual_redistribution"]


def _split_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _split_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_ablation(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    scale_parser = build_scale_parser()
    runs: list[dict[str, Any]] = []

    for graph in _split_strings(args.graphs):
        for nodes in _split_ints(args.sizes):
            for variant in VARIANTS:
                out_path = runs_dir / f"{graph}_{nodes}_{variant}_seed{args.seed}.json"
                scale_args = scale_parser.parse_args(
                    [
                        "--nodes",
                        str(nodes),
                        "--graph",
                        graph,
                        "--seed",
                        str(args.seed),
                        "--avg-degree",
                        str(args.avg_degree),
                        "--contradiction-rate",
                        str(args.contradiction_rate),
                        "--steps",
                        str(args.steps),
                        "--learning-rate",
                        str(args.learning_rate),
                        "--damping",
                        str(args.damping),
                        "--tolerance",
                        str(args.tolerance),
                        "--update-policy",
                        variant,
                        "--hub-percentile",
                        str(args.hub_percentile),
                        "--hub-damping-factor",
                        str(args.hub_damping_factor),
                        "--nonhub-frontier-fraction",
                        str(args.nonhub_frontier_fraction),
                        "--out",
                        str(out_path),
                    ]
                    + (["--no-frontier"] if args.no_frontier else [])
                    + (
                        ["--no-provenance-weighting"]
                        if args.no_provenance_weighting
                        else []
                    )
                )
                payload = run_one(scale_args, out_path)
                runs.append(payload)
                print(f"completed {payload['run_id']} -> {out_path}")

    aggregate = aggregate_results(runs)
    payload = {
        "task": "Hub-Normalized Relaxation Ablation",
        "version": "v0.3-experimental",
        "run_id": f"hub-normalization-ablation-seed{args.seed}",
        "hypothesis": "Scale-free failure is caused by hub nodes absorbing or emitting disproportionate residual tension.",
        "variants": VARIANTS,
        "runs": runs,
        "aggregate": aggregate,
    }
    json_path = out_dir / "hub_normalization_ablation.json"
    report_path = out_dir / "HUB_NORMALIZATION_ABLATION.md"
    write_json(json_path, payload)
    write_report(payload, report_path)

    repo_root = Path(__file__).resolve().parents[5]
    receipt = build_receipt(
        run_id=str(payload["run_id"]),
        repo_root=repo_root,
        command=" ".join(sys.argv),
        dataset={
            "name": "synthetic-hub-normalization-ablation",
            "version": "v0.3-experimental",
            "hash": stable_hash(
                {
                    "graphs": _split_strings(args.graphs),
                    "sizes": _split_ints(args.sizes),
                    "variants": VARIANTS,
                    "seed": args.seed,
                    "avg_degree": args.avg_degree,
                    "contradiction_rate": args.contradiction_rate,
                }
            ),
        },
        system={
            "name": "ts-core-reference-relaxation",
            "variant": "hub-normalization-ablation",
        },
        config={
            "seed": args.seed,
            "graphs": _split_strings(args.graphs),
            "sizes": _split_ints(args.sizes),
            "variants": VARIANTS,
            "avg_degree": args.avg_degree,
            "contradiction_rate": args.contradiction_rate,
            "steps": args.steps,
            "learning_rate": args.learning_rate,
            "damping": args.damping,
            "tolerance": args.tolerance,
            "frontier": not args.no_frontier,
            "provenance_weighting": not args.no_provenance_weighting,
            "hub_percentile": args.hub_percentile,
            "hub_damping_factor": args.hub_damping_factor,
            "nonhub_frontier_fraction": args.nonhub_frontier_fraction,
        },
        metrics=aggregate,
        graph_family="mixed",
        known_caveats=[
            "Experimental branch result; this is an ablation, not a fix.",
            "Synthetic graph families only; this is not real knowledge graph scalability evidence.",
            "Success requires improving scale-free behavior without hiding final tension or regressing random/small-world checks.",
        ],
        artifacts=[json_path, report_path],
    )
    receipt_path = out_dir / "hub_normalization_ablation.receipt.json"
    write_json(receipt_path, receipt)
    payload["receipt_path"] = str(receipt_path)
    write_json(json_path, payload)
    return payload


def aggregate_results(runs: list[dict[str, Any]]) -> dict[str, Any]:
    reference_by_case = {
        case_key(run): run
        for run in runs
        if run["config"]["update_policy"] == "reference"
    }
    comparisons: list[dict[str, Any]] = []
    for run in runs:
        variant = run["config"]["update_policy"]
        if variant == "reference":
            continue
        reference = reference_by_case[case_key(run)]
        comparisons.append(compare_to_reference(run, reference))

    scale_free = [row for row in comparisons if row["graph"] == "scale_free"]
    regressions = [
        row
        for row in comparisons
        if row["graph"] in {"random", "small_world"} and not row["no_regression"]
    ]
    best_scale_free = sorted(
        scale_free,
        key=lambda row: (
            row["f1_delta"],
            -row["final_tension_delta"],
            -row["hub_share_delta"],
        ),
        reverse=True,
    )
    return {
        "comparison_count": len(comparisons),
        "best_scale_free_variant": best_scale_free[0] if best_scale_free else None,
        "scale_free_comparisons": scale_free,
        "regression_count": len(regressions),
        "regressions": regressions,
        "success_criteria": evaluate_success(scale_free, regressions),
    }


def case_key(run: dict[str, Any]) -> tuple[str, int, int]:
    return (run["graph"]["type"], int(run["graph"]["nodes"]), int(run["graph"]["seed"]))


def compare_to_reference(
    run: dict[str, Any], reference: dict[str, Any]
) -> dict[str, Any]:
    metrics = run["metrics"]
    reference_metrics = reference["metrics"]
    graph = run["graph"]["type"]
    f1_delta = float(metrics["contradiction_localization_f1"]) - float(
        reference_metrics["contradiction_localization_f1"]
    )
    final_tension_delta = float(metrics["final_global_tension"]) - float(
        reference_metrics["final_global_tension"]
    )
    hub_share_delta = float(metrics["hub_residual_tension_share"]) - float(
        reference_metrics["hub_residual_tension_share"]
    )
    runtime_ratio = float(metrics["runtime_s"]) / max(
        1e-12, float(reference_metrics["runtime_s"])
    )
    no_regression = (
        float(metrics["contradiction_localization_f1"])
        >= float(reference_metrics["contradiction_localization_f1"]) - 0.05
        and float(metrics["final_global_tension"])
        <= max(0.01, float(reference_metrics["final_global_tension"]) * 1.10)
        and runtime_ratio <= 1.50
    )
    return {
        "graph": graph,
        "nodes": int(run["graph"]["nodes"]),
        "seed": int(run["graph"]["seed"]),
        "variant": run["config"]["update_policy"],
        "f1": float(metrics["contradiction_localization_f1"]),
        "reference_f1": float(reference_metrics["contradiction_localization_f1"]),
        "f1_delta": f1_delta,
        "final_tension": float(metrics["final_global_tension"]),
        "reference_final_tension": float(reference_metrics["final_global_tension"]),
        "final_tension_delta": final_tension_delta,
        "hub_residual_share": float(metrics["hub_residual_tension_share"]),
        "reference_hub_residual_share": float(
            reference_metrics["hub_residual_tension_share"]
        ),
        "hub_share_delta": hub_share_delta,
        "runtime_ratio": runtime_ratio,
        "no_regression": no_regression,
    }


def evaluate_success(
    scale_free: list[dict[str, Any]], regressions: list[dict[str, Any]]
) -> dict[str, Any]:
    improved = [
        row
        for row in scale_free
        if row["hub_share_delta"] < 0
        and row["f1_delta"] > 0
        and row["final_tension"] <= max(0.01, row["reference_final_tension"] * 1.10)
    ]
    return {
        "reduced_hub_share_and_improved_f1_cases": len(improved),
        "random_small_world_regressions": len(regressions),
        "passed": bool(improved) and not regressions,
    }


def write_report(payload: dict[str, Any], out_path: Path) -> None:
    aggregate = payload["aggregate"]
    lines = [
        "# Hub-Normalized Relaxation Ablation",
        "",
        "v0.3 is an experimental branch result. It tests hub-aware remedies against the reference config; it does not claim a fix.",
        "",
        f"Hypothesis: {payload['hypothesis']}",
        "",
        "## Success Criteria",
        "",
        f"- Reduced hub share and improved scale-free F1 cases: {aggregate['success_criteria']['reduced_hub_share_and_improved_f1_cases']}",
        f"- Random/small-world regression count: {aggregate['success_criteria']['random_small_world_regressions']}",
        f"- Passed strict criteria: `{aggregate['success_criteria']['passed']}`",
        "",
        "## Best Scale-Free Comparison",
        "",
    ]
    best = aggregate["best_scale_free_variant"]
    if best:
        lines.extend(
            [
                f"- Variant: `{best['variant']}`",
                f"- Nodes: `{best['nodes']}`",
                f"- F1 delta: `{best['f1_delta']:.3f}`",
                f"- Final tension delta: `{best['final_tension_delta']:.6f}`",
                f"- Hub residual share delta: `{best['hub_share_delta']:.3f}`",
                "",
            ]
        )
    else:
        lines.extend(["- No scale-free comparison rows.", ""])
    lines.extend(
        [
            "## Scale-Free Comparisons",
            "",
            "| Nodes | Variant | F1 | Ref F1 | F1 delta | Final tension | Ref tension | Hub share | Ref hub share | Runtime ratio |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in aggregate["scale_free_comparisons"]:
        lines.append(
            "| {nodes} | {variant} | {f1:.3f} | {reference_f1:.3f} | {f1_delta:.3f} | {final_tension:.6f} | {reference_final_tension:.6f} | {hub:.3f} | {ref_hub:.3f} | {runtime:.3f} |".format(
                nodes=row["nodes"],
                variant=row["variant"],
                f1=row["f1"],
                reference_f1=row["reference_f1"],
                f1_delta=row["f1_delta"],
                final_tension=row["final_tension"],
                reference_final_tension=row["reference_final_tension"],
                hub=row["hub_residual_share"],
                ref_hub=row["reference_hub_residual_share"],
                runtime=row["runtime_ratio"],
            )
        )
    lines.extend(
        [
            "",
            "## Regression Checks",
            "",
        ]
    )
    if aggregate["regressions"]:
        for row in aggregate["regressions"]:
            lines.append(
                f"- `{row['graph']}` `{row['nodes']}` `{row['variant']}` regressed: F1 delta `{row['f1_delta']:.3f}`, final tension delta `{row['final_tension_delta']:.6f}`, runtime ratio `{row['runtime_ratio']:.3f}`."
            )
    else:
        lines.append("- No random/small-world regression crossed the strict threshold.")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "> v0.3 is an experimental ablation. A positive result can support hub-aware relaxation on these seeded synthetic graphs only.",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="100,1000,10000")
    parser.add_argument("--graphs", default="scale_free,random,small_world")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--avg-degree", type=int, default=6)
    parser.add_argument("--contradiction-rate", type=float, default=0.01)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.12)
    parser.add_argument("--damping", type=float, default=0.85)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--no-frontier", action="store_true")
    parser.add_argument("--no-provenance-weighting", action="store_true")
    parser.add_argument("--hub-percentile", type=float, default=0.95)
    parser.add_argument("--hub-damping-factor", type=float, default=0.35)
    parser.add_argument("--nonhub-frontier-fraction", type=float, default=0.30)
    parser.add_argument("--out-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_ablation(args)
    print(
        json.dumps(
            {
                "run_id": payload["run_id"],
                "passed": payload["aggregate"]["success_criteria"]["passed"],
                "receipt_path": payload["receipt_path"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
