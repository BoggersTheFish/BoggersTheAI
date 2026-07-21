"""Scale-free failure decomposition metrics.

This task does not fix scale-free failures. It sharpens the failure by asking
whether the observed residual tension is dominated by hubs, damping/plateau
behavior, localization failure, or active-frontier policy.
"""

from __future__ import annotations

from statistics import mean
from typing import Any

from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    CONTRADICTS,
    RelaxationConfig,
    RelaxationResult,
    SyntheticGraph,
    compute_tension,
    node_degrees,
    residual_edge_tensions,
)


def decompose_scale_free_failure(
    graph: SyntheticGraph,
    result: RelaxationResult,
    config: RelaxationConfig,
) -> dict[str, Any]:
    if graph.spec.graph_type != "scale_free":
        raise ValueError(
            "failure decomposition v0.2 is currently scoped to scale_free graphs"
        )

    _global_tension, node_tension = compute_tension(graph, result.final_values, config)
    degrees = node_degrees(graph)
    residual_edges = residual_edge_tensions(graph, result.final_values, config)
    hub_share = float(result.diagnostics["hub_dominance"]["hub_residual_tension_share"])
    nonhub_share = max(0.0, 1.0 - hub_share)
    ratio = hub_share / nonhub_share if nonhub_share > 0 else 1_000_000_000.0
    contradiction_rank = contradiction_rank_of_planted_edge(residual_edges)
    metrics = {
        "hub_residual_share": hub_share,
        "nonhub_residual_share": nonhub_share,
        "hub_to_nonhub_residual_ratio": ratio,
        "mean_residual_by_degree_decile": mean_residual_by_degree_decile(
            degrees, node_tension
        ),
        "max_residual_edge_degree_product": max_residual_edge_degree_product(
            residual_edges
        ),
        "frontier_churn_rate": frontier_churn_rate(
            result.active_frontier_history, graph.spec.nodes
        ),
        "plateau_residual_slope": plateau_residual_slope(result.tension_history),
        "contradiction_rank_of_planted_edge": contradiction_rank,
    }
    return {
        "task": "Scale-Free Failure Decomposition",
        "version": "v0.2",
        "central_question": (
            "Is scale-free failure caused by hub dominance, bad relaxation damping, "
            "poor contradiction scoring, or active-frontier policy starving low-degree regions?"
        ),
        "metrics": metrics,
        "diagnosis": diagnose_failure(metrics, result),
    }


def mean_residual_by_degree_decile(
    degrees: list[int],
    node_tension: list[float],
) -> list[dict[str, float | int]]:
    if not degrees:
        return []
    ordered = sorted(range(len(degrees)), key=lambda idx: degrees[idx])
    rows: list[dict[str, float | int]] = []
    for decile in range(10):
        start = decile * len(ordered) // 10
        end = (decile + 1) * len(ordered) // 10
        indexes = ordered[start:end]
        if not indexes:
            rows.append(
                {
                    "decile": decile + 1,
                    "nodes": 0,
                    "min_degree": 0,
                    "max_degree": 0,
                    "mean_residual": 0.0,
                }
            )
            continue
        rows.append(
            {
                "decile": decile + 1,
                "nodes": len(indexes),
                "min_degree": min(degrees[idx] for idx in indexes),
                "max_degree": max(degrees[idx] for idx in indexes),
                "mean_residual": mean(node_tension[idx] for idx in indexes),
            }
        )
    return rows


def max_residual_edge_degree_product(
    residual_edges: list[dict[str, float | int | str]],
) -> dict[str, float | int | str]:
    if not residual_edges:
        return {
            "edge_index": -1,
            "degree_product": 0,
            "tension": 0.0,
            "relation": "",
        }
    rows = []
    for edge in residual_edges:
        degree_product = int(edge["src_degree"]) * int(edge["dst_degree"])
        rows.append(
            {
                "edge_index": int(edge["edge_index"]),
                "degree_product": degree_product,
                "tension": float(edge["tension"]),
                "relation": str(edge["relation"]),
                "src_degree": int(edge["src_degree"]),
                "dst_degree": int(edge["dst_degree"]),
                "tension_degree_product": float(edge["tension"]) * degree_product,
            }
        )
    return max(rows, key=lambda row: float(row["tension_degree_product"]))


def frontier_churn_rate(active_frontier_history: list[int], nodes: int) -> float:
    if len(active_frontier_history) < 2 or nodes <= 0:
        return 0.0
    churn = [
        abs(active_frontier_history[idx] - active_frontier_history[idx - 1]) / nodes
        for idx in range(1, len(active_frontier_history))
    ]
    return mean(churn)


def plateau_residual_slope(tension_history: list[float], window: int = 10) -> float:
    if len(tension_history) < 2:
        return 0.0
    recent = tension_history[-min(window, len(tension_history)) :]
    if len(recent) < 2:
        return 0.0
    return (recent[-1] - recent[0]) / (len(recent) - 1)


def contradiction_rank_of_planted_edge(
    residual_edges: list[dict[str, float | int | str]],
) -> dict[str, float | int | list[int]]:
    ranks: list[int] = []
    for rank, edge in enumerate(residual_edges, start=1):
        if (
            edge["relation"] == CONTRADICTS
            and edge["provenance"] == "synthetic_injected_contradiction"
        ):
            ranks.append(rank)
    if not ranks:
        return {"best_rank": -1, "worst_rank": -1, "mean_rank": -1.0, "ranks": []}
    return {
        "best_rank": min(ranks),
        "worst_rank": max(ranks),
        "mean_rank": mean(ranks),
        "ranks": ranks,
    }


def diagnose_failure(
    metrics: dict[str, Any], result: RelaxationResult
) -> dict[str, str | list[str]]:
    labels: list[str] = []
    hub_share = float(metrics["hub_residual_share"])
    hub_ratio = float(metrics["hub_to_nonhub_residual_ratio"])
    frontier_churn = float(metrics["frontier_churn_rate"])
    slope = float(metrics["plateau_residual_slope"])
    contradiction_rank = metrics["contradiction_rank_of_planted_edge"]
    best_rank = int(contradiction_rank["best_rank"])
    planted_count = len(contradiction_rank["ranks"])
    f1 = float(result.metrics["contradiction_localization_f1"])

    if hub_share >= 0.60 and hub_ratio >= 2.0:
        labels.append("hub_dominance_problem")
    if abs(slope) <= 1e-4 and float(result.metrics["final_global_tension"]) > 0.05:
        labels.append("damping_or_plateau_problem")
    if f1 == 0.0 and (best_rank < 0 or best_rank > max(10, planted_count * 5)):
        labels.append("localization_problem")
    if frontier_churn <= 0.01 and len(set(result.active_frontier_history[-10:])) <= 1:
        labels.append("frontier_policy_problem")

    primary = labels[0] if labels else "inconclusive"
    explanations = {
        "hub_dominance_problem": "High-degree nodes account for most residual tension.",
        "damping_or_plateau_problem": "Residual tension is no longer moving materially despite high final tension.",
        "localization_problem": "Planted contradiction edges are not ranked near the top of residual tension.",
        "frontier_policy_problem": "The active frontier is effectively static, so update policy is not focusing useful work.",
        "inconclusive": "No single failure mode crossed the current heuristic threshold.",
    }
    return {
        "primary": primary,
        "labels": labels,
        "summary": explanations[primary],
    }
