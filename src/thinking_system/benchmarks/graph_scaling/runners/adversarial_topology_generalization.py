"""Run v0.5 adversarial topology generalization."""

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
from thinking_system.benchmarks.graph_scaling.tasks.adversarial_topology import (
    FAMILIES,
    PLACEMENTS,
    AdversarialSpec,
    generate_adversarial_graph,
)
from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    RelaxationConfig,
    run_relaxation,
)
from thinking_system.benchmarks.graph_scaling.tasks.topology_policy import (
    select_policy,
    selection_payload,
)

POLICIES = ["reference", "degree_normalized"]


def _split_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _split_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _split_floats(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def run_generalization(args: argparse.Namespace) -> dict[str, Any]:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for family in _split_strings(args.families):
        for nodes in _split_ints(args.sizes):
            for hub_strength in _split_floats(args.hub_strengths):
                for placement in _split_strings(args.placements):
                    spec = AdversarialSpec(
                        family=family,
                        placement=placement,
                        nodes=nodes,
                        seed=args.seed,
                        hub_strength=hub_strength,
                        noise_rate=args.noise_rate,
                    )
                    graph = generate_adversarial_graph(spec)
                    selection = select_policy(graph)
                    policy_results = {
                        policy: run_policy(graph, args, policy) for policy in POLICIES
                    }
                    oracle = choose_oracle(policy_results)
                    selected = selection.selected_policy
                    selected_result = policy_results[selected]
                    reference_result = policy_results["reference"]
                    degree_result = policy_results["degree_normalized"]
                    rows.append(
                        {
                            "topology_family": family,
                            "nodes": nodes,
                            "seed": args.seed,
                            "hub_strength": hub_strength,
                            "boundary_case": is_boundary_case(selection),
                            "contradiction_placement": placement,
                            "selector_policy": selected,
                            "selector_reason": selection.reason,
                            "selector_diagnostics": selection_payload(selection),
                            "oracle_best_policy": oracle["policy"],
                            "selector_matches_oracle": selected == oracle["policy"],
                            "selector_regret_final_tension": (
                                float(selected_result.metrics["final_global_tension"])
                                - float(oracle["metrics"]["final_global_tension"])
                            ),
                            "selector_regret_f1": (
                                float(
                                    oracle["metrics"]["contradiction_localization_f1"]
                                )
                                - float(
                                    selected_result.metrics[
                                        "contradiction_localization_f1"
                                    ]
                                )
                            ),
                            "catastrophic_regression": catastrophic_regression(
                                selected_result.metrics, oracle["metrics"]
                            ),
                            "selector_metrics": selected_result.metrics,
                            "reference_metrics": reference_result.metrics,
                            "degree_normalized_metrics": degree_result.metrics,
                            "oracle_metrics": oracle["metrics"],
                        }
                    )

    aggregate = aggregate_rows(rows)
    payload = {
        "task": "Adversarial Topology Generalization",
        "version": "v0.5-experimental",
        "run_id": f"adversarial-topology-generalization-seed{args.seed}",
        "framing": (
            "v0.4 passed on known graph families. v0.5 tries to falsify that result "
            "by testing mixed, near-boundary, and contradiction-placement-stressed graphs."
        ),
        "selector_boundary": "selector uses pre-run topology diagnostics only; oracle labels are post-run audit fields",
        "rows": rows,
        "aggregate": aggregate,
    }
    json_path = out_dir / "adversarial_topology_generalization.json"
    report_path = out_dir / "ADVERSARIAL_TOPOLOGY_GENERALIZATION.md"
    write_json(json_path, payload)
    write_report(payload, report_path)

    repo_root = Path(__file__).resolve().parents[5]
    receipt = build_receipt(
        run_id=str(payload["run_id"]),
        repo_root=repo_root,
        command=" ".join(sys.argv),
        dataset={
            "name": "synthetic-adversarial-topology-generalization",
            "version": "v0.5-experimental",
            "hash": stable_hash(
                {
                    "families": _split_strings(args.families),
                    "placements": _split_strings(args.placements),
                    "sizes": _split_ints(args.sizes),
                    "hub_strengths": _split_floats(args.hub_strengths),
                    "seed": args.seed,
                    "noise_rate": args.noise_rate,
                }
            ),
        },
        system={
            "name": "ts-core-reference-relaxation",
            "variant": "adversarial-topology-generalization",
        },
        config={
            "seed": args.seed,
            "families": _split_strings(args.families),
            "placements": _split_strings(args.placements),
            "sizes": _split_ints(args.sizes),
            "hub_strengths": _split_floats(args.hub_strengths),
            "noise_rate": args.noise_rate,
            "steps": args.steps,
            "learning_rate": args.learning_rate,
            "damping": args.damping,
            "tolerance": args.tolerance,
        },
        metrics=aggregate,
        graph_family="adversarial_mixed",
        known_caveats=[
            "Synthetic adversarial topology stress test only.",
            "Oracle-best-policy is computed after outcomes and is not available to the selector.",
            "A pass supports robustness on this adversarial harness only, not real knowledge graph scalability.",
        ],
        artifacts=[json_path, report_path],
    )
    receipt_path = out_dir / "adversarial_topology_generalization.receipt.json"
    write_json(receipt_path, receipt)
    payload["receipt_path"] = str(receipt_path)
    write_json(json_path, payload)
    return payload


def run_policy(graph: Any, args: argparse.Namespace, policy: str) -> Any:
    return run_relaxation(
        graph,
        RelaxationConfig(
            steps=args.steps,
            learning_rate=args.learning_rate,
            damping=args.damping,
            tolerance=args.tolerance,
            update_policy=policy,
        ),
    )


def choose_oracle(policy_results: dict[str, Any]) -> dict[str, Any]:
    def score(item: tuple[str, Any]) -> tuple[float, float]:
        _policy, result = item
        return (
            float(result.metrics["contradiction_localization_f1"]),
            -float(result.metrics["final_global_tension"]),
        )

    policy, result = max(policy_results.items(), key=score)
    return {"policy": policy, "metrics": result.metrics}


def is_boundary_case(selection: Any) -> bool:
    diagnostics = selection.diagnostics
    hub_touch = float(diagnostics["hub_edge_touch_share"])
    gini = float(diagnostics["degree_gini"])
    max_to_mean = float(diagnostics["max_to_mean_degree"])
    return (
        abs(hub_touch - 0.35) <= 0.08
        or abs(gini - 0.30) <= 0.06
        or abs(max_to_mean - 6.0) <= 1.5
    )


def catastrophic_regression(
    selected_metrics: dict[str, Any], oracle_metrics: dict[str, Any]
) -> bool:
    f1_regret = float(oracle_metrics["contradiction_localization_f1"]) - float(
        selected_metrics["contradiction_localization_f1"]
    )
    tension_regret = float(selected_metrics["final_global_tension"]) - float(
        oracle_metrics["final_global_tension"]
    )
    return f1_regret > 0.50 or tension_regret > 0.10


def aggregate_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    selector_wins = sum(1 for row in rows if row["selector_matches_oracle"])
    catastrophic = [row for row in rows if row["catastrophic_regression"]]
    boundary_failures = [
        row
        for row in rows
        if row["boundary_case"] and not row["selector_matches_oracle"]
    ]
    selector_f1 = sum(
        float(row["selector_metrics"]["contradiction_localization_f1"]) for row in rows
    )
    reference_f1 = sum(
        float(row["reference_metrics"]["contradiction_localization_f1"]) for row in rows
    )
    degree_f1 = sum(
        float(row["degree_normalized_metrics"]["contradiction_localization_f1"])
        for row in rows
    )
    selector_tension = sum(
        float(row["selector_metrics"]["final_global_tension"]) for row in rows
    )
    reference_tension = sum(
        float(row["reference_metrics"]["final_global_tension"]) for row in rows
    )
    degree_tension = sum(
        float(row["degree_normalized_metrics"]["final_global_tension"]) for row in rows
    )
    family_summary: dict[str, dict[str, Any]] = {}
    for row in rows:
        summary = family_summary.setdefault(
            row["topology_family"],
            {"count": 0, "catastrophic": 0, "selector_oracle_matches": 0},
        )
        summary["count"] += 1
        summary["catastrophic"] += int(row["catastrophic_regression"])
        summary["selector_oracle_matches"] += int(row["selector_matches_oracle"])

    success = {
        "beats_or_matches_always_reference_on_f1": selector_f1 >= reference_f1,
        "beats_or_matches_always_degree_normalized_on_f1": selector_f1 >= degree_f1,
        "beats_or_matches_always_reference_on_tension": selector_tension
        <= reference_tension,
        "beats_or_matches_always_degree_normalized_on_tension": selector_tension
        <= degree_tension,
        "no_catastrophic_family_regression": not catastrophic,
        "boundary_cases_documented": True,
    }
    success["passed"] = all(success.values())
    return {
        "row_count": len(rows),
        "selector_oracle_match_rate": selector_wins / len(rows),
        "catastrophic_regression_count": len(catastrophic),
        "boundary_failure_count": len(boundary_failures),
        "selector_total_f1": selector_f1,
        "always_reference_total_f1": reference_f1,
        "always_degree_normalized_total_f1": degree_f1,
        "selector_total_final_tension": selector_tension,
        "always_reference_total_final_tension": reference_tension,
        "always_degree_normalized_total_final_tension": degree_tension,
        "family_summary": family_summary,
        "success_criteria": success,
    }


def write_report(payload: dict[str, Any], out_path: Path) -> None:
    aggregate = payload["aggregate"]
    lines = [
        "# Adversarial Topology Generalization",
        "",
        payload["framing"],
        "",
        "The goal is not to prove universal scaling; the goal is to measure where topology-aware policy selection generalizes and where it fails.",
        "",
        "## Success Criteria",
        "",
    ]
    for key, value in aggregate["success_criteria"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(
        [
            "",
            "## Aggregate Metrics",
            "",
            f"- Rows: `{aggregate['row_count']}`",
            f"- Selector/oracle match rate: `{aggregate['selector_oracle_match_rate']:.3f}`",
            f"- Catastrophic regressions: `{aggregate['catastrophic_regression_count']}`",
            f"- Boundary failures: `{aggregate['boundary_failure_count']}`",
            f"- Selector total F1: `{aggregate['selector_total_f1']:.3f}`",
            f"- Always-reference total F1: `{aggregate['always_reference_total_f1']:.3f}`",
            f"- Always-degree-normalized total F1: `{aggregate['always_degree_normalized_total_f1']:.3f}`",
            f"- Selector total final tension: `{aggregate['selector_total_final_tension']:.6f}`",
            f"- Always-reference total final tension: `{aggregate['always_reference_total_final_tension']:.6f}`",
            f"- Always-degree-normalized total final tension: `{aggregate['always_degree_normalized_total_final_tension']:.6f}`",
            "",
            "## Selector Confusion Rows",
            "",
            "| Family | Nodes | Hub strength | Placement | Boundary | Selector | Oracle | F1 regret | Tension regret | Catastrophic |",
            "| --- | ---: | ---: | --- | --- | --- | --- | ---: | ---: | --- |",
        ]
    )
    for row in payload["rows"]:
        if row["selector_matches_oracle"] and not row["boundary_case"]:
            continue
        lines.append(
            "| {family} | {nodes} | {hub:.2f} | {placement} | {boundary} | {selector} | {oracle} | {f1:.3f} | {tension:.6f} | {cat} |".format(
                family=row["topology_family"],
                nodes=row["nodes"],
                hub=row["hub_strength"],
                placement=row["contradiction_placement"],
                boundary=row["boundary_case"],
                selector=row["selector_policy"],
                oracle=row["oracle_best_policy"],
                f1=row["selector_regret_f1"],
                tension=row["selector_regret_final_tension"],
                cat=row["catastrophic_regression"],
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "> v0.5 is an adversarial synthetic selector stress test. It does not prove TS-Core scales to real knowledge/provenance graphs.",
        ]
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", default="100,1000")
    parser.add_argument("--families", default=",".join(FAMILIES))
    parser.add_argument("--placements", default=",".join(PLACEMENTS))
    parser.add_argument("--hub-strengths", default="0.25,0.35,0.45,0.60,0.75")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--noise-rate", type=float, default=0.10)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.12)
    parser.add_argument("--damping", type=float, default=0.85)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--out-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = run_generalization(args)
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
