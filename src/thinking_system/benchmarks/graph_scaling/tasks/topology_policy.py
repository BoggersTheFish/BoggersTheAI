"""Topology-aware relaxation policy selection.

The selector uses graph structure only. It must not inspect final tension,
localization scores, labels derived from benchmark outcomes, or any post-run
relaxation result.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    SyntheticGraph,
    node_degrees,
)


@dataclass(frozen=True)
class PolicySelection:
    selected_policy: str
    reason: str
    diagnostics: dict[str, float | int]


def topology_diagnostics(graph: SyntheticGraph) -> dict[str, float | int]:
    degrees = node_degrees(graph)
    if not degrees:
        return {
            "nodes": graph.spec.nodes,
            "edges": graph.spec.edges,
            "mean_degree": 0.0,
            "max_degree": 0,
            "max_to_mean_degree": 0.0,
            "degree_variance": 0.0,
            "degree_gini": 0.0,
            "hub_degree_threshold": 0,
            "hub_node_share": 0.0,
            "hub_edge_touch_share": 0.0,
            "clustering_coefficient_approx": 0.0,
        }
    mean_degree = mean(degrees)
    max_degree = max(degrees)
    hub_threshold = percentile(degrees, 0.95)
    hub_nodes = {idx for idx, degree in enumerate(degrees) if degree >= hub_threshold}
    hub_touch_edges = [
        edge for edge in graph.edges if edge.src in hub_nodes or edge.dst in hub_nodes
    ]
    return {
        "nodes": graph.spec.nodes,
        "edges": graph.spec.edges,
        "mean_degree": mean_degree,
        "max_degree": max_degree,
        "max_to_mean_degree": max_degree / mean_degree if mean_degree else 0.0,
        "degree_variance": mean((degree - mean_degree) ** 2 for degree in degrees),
        "degree_gini": degree_gini(degrees),
        "hub_degree_threshold": hub_threshold,
        "hub_node_share": len(hub_nodes) / len(degrees),
        "hub_edge_touch_share": len(hub_touch_edges) / max(1, len(graph.edges)),
        "clustering_coefficient_approx": clustering_coefficient_approx(graph),
    }


def select_policy(graph: SyntheticGraph) -> PolicySelection:
    diagnostics = topology_diagnostics(graph)
    hub_concentration = float(diagnostics["hub_edge_touch_share"])
    max_to_mean = float(diagnostics["max_to_mean_degree"])
    gini = float(diagnostics["degree_gini"])
    variance = float(diagnostics["degree_variance"])

    if hub_concentration >= 0.35 and (
        max_to_mean >= 6.0 or gini >= 0.30 or variance >= 20.0
    ):
        return PolicySelection(
            selected_policy="degree_normalized",
            reason=(
                "hub concentration is high: "
                f"hub_edge_touch_share={hub_concentration:.3f}, "
                f"max_to_mean_degree={max_to_mean:.3f}, degree_gini={gini:.3f}"
            ),
            diagnostics=diagnostics,
        )
    return PolicySelection(
        selected_policy="reference",
        reason=(
            "hub concentration below selector threshold: "
            f"hub_edge_touch_share={hub_concentration:.3f}, "
            f"max_to_mean_degree={max_to_mean:.3f}, degree_gini={gini:.3f}"
        ),
        diagnostics=diagnostics,
    )


def degree_gini(degrees: list[int]) -> float:
    if not degrees:
        return 0.0
    sorted_degrees = sorted(degrees)
    total = sum(sorted_degrees)
    if total == 0:
        return 0.0
    weighted_sum = sum((idx + 1) * degree for idx, degree in enumerate(sorted_degrees))
    n = len(sorted_degrees)
    return (2 * weighted_sum) / (n * total) - (n + 1) / n


def percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * p)))
    return ordered[idx]


def clustering_coefficient_approx(
    graph: SyntheticGraph, sample_limit: int = 256
) -> float:
    adjacency_sets: list[set[int]] = [set() for _ in range(graph.spec.nodes)]
    for edge in graph.edges:
        adjacency_sets[edge.src].add(edge.dst)
        adjacency_sets[edge.dst].add(edge.src)
    candidate_nodes = [
        idx for idx, neighbors in enumerate(adjacency_sets) if len(neighbors) >= 2
    ][:sample_limit]
    if not candidate_nodes:
        return 0.0
    coefficients: list[float] = []
    for node in candidate_nodes:
        neighbors = list(adjacency_sets[node])
        possible = len(neighbors) * (len(neighbors) - 1) / 2
        if possible <= 0:
            continue
        links = 0
        for left_idx, left in enumerate(neighbors):
            for right in neighbors[left_idx + 1 :]:
                if right in adjacency_sets[left]:
                    links += 1
        coefficients.append(links / possible)
    return mean(coefficients) if coefficients else 0.0


def selection_payload(selection: PolicySelection) -> dict[str, Any]:
    return {
        "selected_policy": selection.selected_policy,
        "reason": selection.reason,
        "diagnostics": selection.diagnostics,
        "input_boundary": "pre-run graph topology only; no outcome metrics used",
    }
