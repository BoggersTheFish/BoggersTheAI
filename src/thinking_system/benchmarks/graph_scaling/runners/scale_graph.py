"""Run one synthetic TS-Core scaling benchmark."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from thinking_system.benchmarks.graph_scaling.baselines.graph_baselines import (
    degree_baseline,
    pagerank_like_baseline,
    random_residual_baseline,
)
from thinking_system.benchmarks.graph_scaling.receipts import (
    build_receipt,
    stable_hash,
    write_json,
)
from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    RelaxationConfig,
    generate_graph,
    run_relaxation,
)


def run_one(args: argparse.Namespace, out_path: Path) -> dict[str, object]:
    update_policy = getattr(args, "update_policy", "reference")
    hub_percentile = getattr(args, "hub_percentile", 0.95)
    hub_damping_factor = getattr(args, "hub_damping_factor", 0.35)
    nonhub_frontier_fraction = getattr(args, "nonhub_frontier_fraction", 0.30)
    graph = generate_graph(
        graph_type=args.graph,
        nodes=args.nodes,
        seed=args.seed,
        avg_degree=args.avg_degree,
        contradiction_rate=args.contradiction_rate,
    )
    config = RelaxationConfig(
        steps=args.steps,
        learning_rate=args.learning_rate,
        damping=args.damping,
        tolerance=args.tolerance,
        frontier=not args.no_frontier,
        provenance_weighting=not args.no_provenance_weighting,
        update_policy=update_policy,
        hub_percentile=hub_percentile,
        hub_damping_factor=hub_damping_factor,
        nonhub_frontier_fraction=nonhub_frontier_fraction,
    )
    result = run_relaxation(graph, config)
    baselines = {
        "degree": degree_baseline(graph),
        "pagerank_like": pagerank_like_baseline(graph),
        "random_residual": random_residual_baseline(graph),
    }
    graph_payload = {
        "type": graph.spec.graph_type,
        "nodes": graph.spec.nodes,
        "edges": graph.spec.edges,
        "seed": graph.spec.seed,
        "contradiction_pairs": graph.spec.contradiction_pairs,
    }
    config_payload = {
        "seed": args.seed,
        "avg_degree": args.avg_degree,
        "contradiction_rate": args.contradiction_rate,
        "steps": config.steps,
        "learning_rate": config.learning_rate,
        "damping": config.damping,
        "tolerance": config.tolerance,
        "frontier": config.frontier,
        "provenance_weighting": config.provenance_weighting,
        "update_policy": update_policy,
        "hub_percentile": hub_percentile,
        "hub_damping_factor": hub_damping_factor,
        "nonhub_frontier_fraction": nonhub_frontier_fraction,
    }
    baseline_comparison = compare_systems(
        ts_metrics={
            "precision": result.metrics["contradiction_localization_precision"],
            "recall": result.metrics["contradiction_localization_recall"],
            "f1": result.metrics["contradiction_localization_f1"],
        },
        baselines=baselines,
    )
    payload: dict[str, object] = {
        "run_id": run_id(args.graph, args.nodes, args.seed, update_policy),
        "graph": graph_payload,
        "config": config_payload,
        "metrics": result.metrics,
        "baselines": baselines,
        "baseline_comparison": baseline_comparison,
        "tension_history": result.tension_history,
        "active_frontier_history": result.active_frontier_history,
        "top_tension_nodes": result.top_tension_nodes,
        "diagnostics": result.diagnostics,
    }
    write_json(out_path, payload)

    repo_root = Path(__file__).resolve().parents[5]
    dataset = {
        "name": f"synthetic-{args.graph}",
        "version": "v0.1.0",
        "hash": stable_hash(graph_payload),
    }
    receipt = build_receipt(
        run_id=str(payload["run_id"]),
        repo_root=repo_root,
        command=" ".join(sys.argv),
        dataset=dataset,
        system={"name": "ts-core-reference-relaxation", "variant": "sparse-frontier"},
        config=config_payload,
        metrics={
            **result.metrics,
            "baselines": baselines,
            "baseline_comparison": baseline_comparison,
        },
        graph_family=args.graph,
        known_caveats=known_caveats(args.graph, result.metrics),
        artifacts=[out_path],
    )
    receipt_path = (
        Path(args.receipt) if args.receipt else out_path.with_suffix(".receipt.json")
    )
    write_json(receipt_path, receipt)
    payload["receipt_path"] = str(receipt_path)
    write_json(out_path, payload)
    return payload


def run_id(graph: str, nodes: int, seed: int, update_policy: str) -> str:
    if update_policy == "reference":
        return f"scale-{graph}-{nodes}-seed{seed}"
    return f"scale-{graph}-{nodes}-{update_policy}-seed{seed}"


def compare_systems(
    *,
    ts_metrics: dict[str, float | int | bool],
    baselines: dict[str, dict[str, float]],
) -> dict[str, object]:
    ts_f1 = float(ts_metrics["f1"])
    systems: dict[str, dict[str, object]] = {
        "ts_active_frontier_relaxation": {
            "precision": float(ts_metrics["precision"]),
            "recall": float(ts_metrics["recall"]),
            "f1": ts_f1,
            "role": "candidate",
        }
    }
    deltas: dict[str, dict[str, object]] = {}
    for name, metrics in baselines.items():
        baseline_f1 = float(metrics["f1"])
        delta = ts_f1 - baseline_f1
        if abs(delta) < 1e-9:
            verdict = "equivalent"
        elif delta > 0:
            verdict = "ts_wins"
        else:
            verdict = "ts_loses"
        systems[name] = {
            "precision": float(metrics["precision"]),
            "recall": float(metrics["recall"]),
            "f1": baseline_f1,
            "role": "baseline",
        }
        deltas[name] = {"f1_delta": delta, "verdict": verdict}
    return {"systems": systems, "ts_vs_baselines": deltas}


def known_caveats(graph_family: str, metrics: dict[str, object]) -> list[str]:
    caveats = [
        "Synthetic graph benchmark only; this is not a real-world knowledge graph result.",
        "Reference implementation is dependency-light Python, not the final sparse/GPU runtime.",
        "Contradiction localization is measured against injected synthetic contradictions.",
    ]
    final_tension = float(metrics["final_global_tension"])
    f1 = float(metrics["contradiction_localization_f1"])
    if graph_family == "scale_free" and (final_tension > 0.05 or f1 == 0.0):
        caveats.append(
            "Scale-free graph failed this reference config: residual tension stayed high or localization failed."
        )
    return caveats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nodes", type=int, required=True)
    parser.add_argument(
        "--graph",
        required=True,
        choices=[
            "random",
            "scale_free",
            "small_world",
            "knowledge",
            "provenance",
            "temporal",
            "multi_context",
        ],
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--avg-degree", type=int, default=6)
    parser.add_argument("--contradiction-rate", type=float, default=0.01)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.12)
    parser.add_argument("--damping", type=float, default=0.85)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--no-frontier", action="store_true")
    parser.add_argument("--no-provenance-weighting", action="store_true")
    parser.add_argument(
        "--update-policy",
        default="reference",
        choices=[
            "reference",
            "degree_normalized",
            "hub_damping",
            "residual_redistribution",
        ],
    )
    parser.add_argument("--hub-percentile", type=float, default=0.95)
    parser.add_argument("--hub-damping-factor", type=float, default=0.35)
    parser.add_argument("--nonhub-frontier-fraction", type=float, default=0.30)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    payload = run_one(args, Path(args.out))
    metrics = payload["metrics"]
    print(
        json.dumps(
            {
                "run_id": payload["run_id"],
                "final_global_tension": metrics["final_global_tension"],
                "f1": metrics["contradiction_localization_f1"],
                "runtime_s": metrics["runtime_s"],
                "receipt_path": payload["receipt_path"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
