"""Run v0.4 topology-aware relaxation policy selection."""

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
from thinking_system.benchmarks.graph_scaling.tasks.scaling import generate_graph
from thinking_system.benchmarks.graph_scaling.tasks.topology_policy import (
    select_policy,
    selection_payload,
)


def _split_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _split_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def run_selection(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    runs_dir = out_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    scale_parser = build_scale_parser()
    runs: list[dict[str, Any]] = []

    for graph_type in _split_strings(args.graphs):
        for nodes in _split_ints(args.sizes):
            graph = generate_graph(
                graph_type=graph_type,
                nodes=nodes,
                seed=args.seed,
                avg_degree=args.avg_degree,
                contradiction_rate=args.contradiction_rate,
            )
            selection = select_policy(graph)
            for role, policy in [
                ("reference_control", "reference"),
                ("selected_policy", selection.selected_policy),
            ]:
                if role == "reference_control":
                    out_name = f"{graph_type}_{nodes}_reference_seed{args.seed}.json"
                else:
                    out_name = (
                        f"{graph_type}_{nodes}_selected_{policy}_seed{args.seed}.json"
                    )
                scale_args = scale_parser.parse_args(
                    [
                        "--nodes",
                        str(nodes),
                        "--graph",
                        graph_type,
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
                        policy,
                        "--hub-percentile",
                        str(args.hub_percentile),
                        "--hub-damping-factor",
                        str(args.hub_damping_factor),
                        "--nonhub-frontier-fraction",
                        str(args.nonhub_frontier_fraction),
                        "--out",
                        str(runs_dir / out_name),
                    ]
                    + (["--no-frontier"] if args.no_frontier else [])
                    + (
                        ["--no-provenance-weighting"]
                        if args.no_provenance_weighting
                        else []
                    )
                )
                run = run_one(scale_args, runs_dir / out_name)
                run["policy_selection"] = selection_payload(selection)
                run["selection_role"] = role
                runs.append(run)
                print(
                    f"completed {run['run_id']} role={run['selection_role']} selected={selection.selected_policy}"
                )

    aggregate = aggregate_results(runs)
    payload = {
        "task": "Topology-Aware Relaxation Policy Selection",
        "version": "v0.4-experimental",
        "run_id": f"topology-policy-selection-seed{args.seed}",
        "hypothesis": (
            "Different graph topologies require different relaxation policies; "
            "hub-heavy graphs should use degree normalization while non-hub-heavy "
            "graphs should keep the reference policy."
        ),
        "selector_boundary": "pre-run graph topology diagnostics only; no outcome metrics used",
        "runs": runs,
        "aggregate": aggregate,
    }
    json_path = out_dir / "topology_policy_selection.json"
    report_path = out_dir / "TOPOLOGY_POLICY_SELECTION.md"
    write_json(json_path, payload)
    write_report(payload, report_path)

    repo_root = Path(__file__).resolve().parents[5]
    receipt = build_receipt(
        run_id=str(payload["run_id"]),
        repo_root=repo_root,
        command=" ".join(sys.argv),
        dataset={
            "name": "synthetic-topology-policy-selection",
            "version": "v0.4-experimental",
            "hash": stable_hash(
                {
                    "graphs": _split_strings(args.graphs),
                    "sizes": _split_ints(args.sizes),
                    "seed": args.seed,
                    "avg_degree": args.avg_degree,
                    "contradiction_rate": args.contradiction_rate,
                }
            ),
        },
        system={
            "name": "ts-core-reference-relaxation",
            "variant": "topology-policy-selection",
        },
        config={
            "seed": args.seed,
            "graphs": _split_strings(args.graphs),
            "sizes": _split_ints(args.sizes),
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
            "Experimental selector result on synthetic graph families only.",
            "Selector uses pre-run topology diagnostics, but thresholds are still hand-chosen.",
            "A pass supports this seeded harness only; it is not real-world knowledge graph scalability evidence.",
        ],
        artifacts=[json_path, report_path],
    )
    receipt_path = out_dir / "topology_policy_selection.receipt.json"
    write_json(receipt_path, receipt)
    payload["receipt_path"] = str(receipt_path)
    write_json(json_path, payload)
    return payload


def aggregate_results(runs: list[dict[str, Any]]) -> dict[str, Any]:
    reference_by_case = {
        case_key(run): run
        for run in runs
        if run["selection_role"] == "reference_control"
    }
    comparisons: list[dict[str, Any]] = []
    selected_policy_counts: dict[str, int] = {}
    for run in runs:
        if run["selection_role"] != "selected_policy":
            continue
        selected = run["policy_selection"]["selected_policy"]
        selected_policy_counts[selected] = selected_policy_counts.get(selected, 0) + 1
        comparisons.append(compare_to_reference(run, reference_by_case[case_key(run)]))

    scale_free = [row for row in comparisons if row["graph"] == "scale_free"]
    regressions = [
        row
        for row in comparisons
        if row["graph"] in {"random", "small_world"} and not row["no_regression"]
    ]
    scale_free_improvements = [
        row
        for row in scale_free
        if row["f1_delta"] >= 0
        and row["final_tension_delta"] <= 0
        and row["hub_share_delta"] <= 0
    ]
    passed = len(scale_free_improvements) == len(scale_free) and not regressions
    return {
        "comparison_count": len(comparisons),
        "selected_policy_counts": selected_policy_counts,
        "scale_free_comparisons": scale_free,
        "scale_free_improvement_count": len(scale_free_improvements),
        "regression_count": len(regressions),
        "regressions": regressions,
        "success_criteria": {
            "preserve_or_improve_scale_free": len(scale_free_improvements)
            == len(scale_free),
            "avoid_random_small_world_regressions": not regressions,
            "passed": passed,
        },
    }


def case_key(run: dict[str, Any]) -> tuple[str, int, int]:
    return (run["graph"]["type"], int(run["graph"]["nodes"]), int(run["graph"]["seed"]))


def compare_to_reference(
    run: dict[str, Any], reference: dict[str, Any]
) -> dict[str, Any]:
    metrics = run["metrics"]
    reference_metrics = reference["metrics"]
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
        f1_delta >= -0.05
        and final_tension_delta
        <= max(0.01, float(reference_metrics["final_global_tension"]) * 0.10)
        and runtime_ratio <= 1.50
    )
    return {
        "graph": run["graph"]["type"],
        "nodes": int(run["graph"]["nodes"]),
        "seed": int(run["graph"]["seed"]),
        "selected_policy": run["policy_selection"]["selected_policy"],
        "selection_reason": run["policy_selection"]["reason"],
        "topology_diagnostics": run["policy_selection"]["diagnostics"],
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


def write_report(payload: dict[str, Any], out_path: Path) -> None:
    aggregate = payload["aggregate"]
    lines = [
        "# Topology-Aware Relaxation Policy Selection",
        "",
        "v0.4 tests adaptive policy selection. The selector uses pre-run topology diagnostics only.",
        "",
        f"Hypothesis: {payload['hypothesis']}",
        "",
        "## Success Criteria",
        "",
        f"- Preserve or improve scale-free: `{aggregate['success_criteria']['preserve_or_improve_scale_free']}`",
        f"- Avoid random/small-world regressions: `{aggregate['success_criteria']['avoid_random_small_world_regressions']}`",
        f"- Passed strict criteria: `{aggregate['success_criteria']['passed']}`",
        f"- Selected policy counts: `{aggregate['selected_policy_counts']}`",
        "",
        "## Scale-Free Comparisons",
        "",
        "| Nodes | Selected policy | F1 | Ref F1 | F1 delta | Final tension | Ref tension | Hub share | Ref hub share | Runtime ratio |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in aggregate["scale_free_comparisons"]:
        lines.append(
            "| {nodes} | {policy} | {f1:.3f} | {reference_f1:.3f} | {f1_delta:.3f} | {final_tension:.6f} | {reference_final_tension:.6f} | {hub:.3f} | {ref_hub:.3f} | {runtime:.3f} |".format(
                nodes=row["nodes"],
                policy=row["selected_policy"],
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
    lines.extend(["", "## Selector Reasons", ""])
    for row in aggregate["scale_free_comparisons"]:
        diag = row["topology_diagnostics"]
        lines.append(
            "- `{graph}` `{nodes}` selected `{policy}` because {reason}. max/mean={ratio:.3f}, gini={gini:.3f}, hub_edge_touch={hub_touch:.3f}.".format(
                graph=row["graph"],
                nodes=row["nodes"],
                policy=row["selected_policy"],
                reason=row["selection_reason"],
                ratio=float(diag["max_to_mean_degree"]),
                gini=float(diag["degree_gini"]),
                hub_touch=float(diag["hub_edge_touch_share"]),
            )
        )
    lines.extend(["", "## Regression Checks", ""])
    if aggregate["regressions"]:
        for row in aggregate["regressions"]:
            lines.append(
                f"- `{row['graph']}` `{row['nodes']}` selected `{row['selected_policy']}` regressed: F1 delta `{row['f1_delta']:.3f}`, final tension delta `{row['final_tension_delta']:.6f}`, runtime ratio `{row['runtime_ratio']:.3f}`."
            )
    else:
        lines.append("- No random/small-world regression crossed the strict threshold.")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "> v0.4 tests topology-aware policy selection on seeded synthetic graph families. It does not prove TS-Core scales cleanly to real knowledge graphs.",
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
    payload = run_selection(args)
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
