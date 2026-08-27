"""Synthetic graph scaling task for TS-Core-style tension relaxation.

This module is deliberately dependency-light. The goal is to establish a
deterministic reference path before adding NetworkX, PyTorch, sparse tensors, or
GPU kernels.
"""

from __future__ import annotations

import random
import time
import tracemalloc
from dataclasses import dataclass
from math import sqrt
from typing import Iterable

SUPPORT = "support"
CONTRADICTS = "contradicts"
TEMPORAL = "temporal"
CONTEXT = "context"
PROVENANCE = "provenance"


@dataclass(frozen=True)
class Edge:
    src: int
    dst: int
    relation: str
    weight: float = 1.0
    context: str = "default"
    provenance: str = "synthetic"
    timestamp: int = 0


@dataclass
class GraphSpec:
    graph_type: str
    nodes: int
    edges: int
    seed: int
    contradiction_pairs: list[tuple[int, int]]


@dataclass
class SyntheticGraph:
    spec: GraphSpec
    values: list[float]
    edges: list[Edge]
    adjacency: list[list[int]]


@dataclass
class RelaxationConfig:
    steps: int = 64
    learning_rate: float = 0.12
    damping: float = 0.85
    tolerance: float = 1e-4
    frontier: bool = True
    provenance_weighting: bool = True
    oscillation_window: int = 8
    update_policy: str = "reference"
    hub_percentile: float = 0.95
    hub_damping_factor: float = 0.35
    nonhub_frontier_fraction: float = 0.30


@dataclass
class RelaxationResult:
    metrics: dict[str, float | int | bool]
    tension_history: list[float]
    active_frontier_history: list[int]
    top_tension_nodes: list[dict[str, float | int]]
    diagnostics: dict[str, object]
    final_values: list[float]


def generate_graph(
    graph_type: str,
    nodes: int,
    seed: int,
    avg_degree: int = 6,
    contradiction_rate: float = 0.01,
) -> SyntheticGraph:
    """Create a deterministic synthetic graph with injected contradictions."""

    if nodes < 2:
        raise ValueError("nodes must be at least 2")
    if avg_degree < 1:
        raise ValueError("avg_degree must be positive")

    rng = random.Random(seed)
    values = [rng.uniform(-0.25, 0.25) for _ in range(nodes)]

    if graph_type == "random":
        edges = _random_edges(rng, nodes, avg_degree)
    elif graph_type == "scale_free":
        edges = _scale_free_edges(rng, nodes, avg_degree)
    elif graph_type == "small_world":
        edges = _small_world_edges(rng, nodes, avg_degree)
    elif graph_type == "knowledge":
        edges = _knowledge_edges(rng, nodes, avg_degree)
    elif graph_type == "provenance":
        edges = _provenance_edges(rng, nodes, avg_degree)
    elif graph_type == "temporal":
        edges = _temporal_edges(rng, nodes, avg_degree)
    elif graph_type == "multi_context":
        edges = _multi_context_edges(rng, nodes, avg_degree)
    else:
        raise ValueError(f"unknown graph_type: {graph_type}")

    edges, contradiction_pairs = _inject_contradictions(
        rng=rng,
        nodes=nodes,
        edges=edges,
        contradiction_rate=contradiction_rate,
    )
    for src, dst in contradiction_pairs:
        sign = 1.0 if rng.random() >= 0.5 else -1.0
        values[src] = sign * rng.uniform(0.65, 0.95)
        values[dst] = sign * rng.uniform(0.65, 0.95)
    adjacency = build_adjacency(nodes, edges)
    spec = GraphSpec(
        graph_type=graph_type,
        nodes=nodes,
        edges=len(edges),
        seed=seed,
        contradiction_pairs=contradiction_pairs,
    )
    return SyntheticGraph(spec=spec, values=values, edges=edges, adjacency=adjacency)


def build_adjacency(nodes: int, edges: Iterable[Edge]) -> list[list[int]]:
    adjacency: list[list[int]] = [[] for _ in range(nodes)]
    for idx, edge in enumerate(edges):
        adjacency[edge.src].append(idx)
        adjacency[edge.dst].append(idx)
    return adjacency


def run_relaxation(graph: SyntheticGraph, config: RelaxationConfig) -> RelaxationResult:
    """Run a sparse TS-style relaxation loop over graph tension."""

    values = list(graph.values)
    active_nodes = set(range(graph.spec.nodes))
    tension_history: list[float] = []
    active_frontier_history: list[int] = []
    peak_node_tension = [0.0 for _ in values]
    degrees = node_degrees(graph)
    hub_threshold = degree_percentile(degrees, config.hub_percentile)
    oscillation_detected = False

    tracemalloc.start()
    start = time.perf_counter()
    edges_relaxed = 0
    converged = False

    for _step in range(config.steps):
        active_frontier_history.append(len(active_nodes))
        if config.frontier:
            active_edges = _active_edges(graph, active_nodes)
            if config.update_policy == "residual_redistribution":
                active_edges = redistributed_active_edges(
                    graph=graph,
                    edge_indexes=active_edges,
                    degrees=degrees,
                    hub_threshold=hub_threshold,
                    nonhub_fraction=config.nonhub_frontier_fraction,
                )
        else:
            active_edges = range(len(graph.edges))
        deltas: dict[int, float] = {}
        relaxed_this_step = 0

        for edge_idx in active_edges:
            edge = graph.edges[edge_idx]
            weight = _effective_weight(edge, config)
            src_value = values[edge.src]
            dst_value = values[edge.dst]
            if edge.relation == CONTRADICTS:
                src_target = -dst_value
                dst_target = -src_value
            else:
                src_target = dst_value
                dst_target = src_value
            deltas[edge.src] = deltas.get(
                edge.src, 0.0
            ) + config.learning_rate * weight * (src_target - src_value)
            deltas[edge.dst] = deltas.get(
                edge.dst, 0.0
            ) + config.learning_rate * weight * (dst_target - dst_value)
            relaxed_this_step += 1

        max_update = 0.0
        next_active: set[int] = set()
        for node, delta in deltas.items():
            update = (
                config.damping
                * node_update_multiplier(
                    policy=config.update_policy,
                    degree=degrees[node],
                    hub_threshold=hub_threshold,
                    hub_damping_factor=config.hub_damping_factor,
                )
                * delta
            )
            if update == 0.0:
                continue
            values[node] = _clamp(values[node] + update)
            max_update = max(max_update, abs(update))
            if abs(update) > config.tolerance:
                next_active.add(node)
                for edge_idx in graph.adjacency[node]:
                    edge = graph.edges[edge_idx]
                    next_active.add(edge.src)
                    next_active.add(edge.dst)

        edges_relaxed += relaxed_this_step
        global_tension, node_tension = compute_tension(graph, values, config)
        peak_node_tension = [
            max(left, right) for left, right in zip(peak_node_tension, node_tension)
        ]
        tension_history.append(global_tension)

        if _detect_oscillation(tension_history, config.oscillation_window):
            oscillation_detected = True
            break
        if max_update <= config.tolerance:
            converged = True
            break
        active_nodes = next_active or set(range(graph.spec.nodes))

    runtime_s = time.perf_counter() - start
    _current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    final_tension, final_node_tension = compute_tension(graph, values, config)
    peak_node_tension = [
        max(left, right) for left, right in zip(peak_node_tension, final_node_tension)
    ]
    top_nodes = sorted(
        [
            {"node": idx, "tension": tension}
            for idx, tension in enumerate(peak_node_tension)
        ],
        key=lambda row: row["tension"],
        reverse=True,
    )[: min(25, graph.spec.nodes)]
    localization = contradiction_localization(
        peak_node_tension, graph.spec.contradiction_pairs
    )
    diagnostics = graph_diagnostics(
        graph=graph,
        values=values,
        node_tension=final_node_tension,
        peak_node_tension=peak_node_tension,
        tension_history=tension_history,
        active_frontier_history=active_frontier_history,
        config=config,
    )
    initial_tension = tension_history[0] if tension_history else final_tension

    metrics: dict[str, float | int | bool] = {
        "runtime_s": runtime_s,
        "peak_rss_mb": peak_bytes / (1024 * 1024),
        "iterations": len(tension_history),
        "initial_global_tension": initial_tension,
        "final_global_tension": final_tension,
        "tension_reduction": initial_tension - final_tension,
        "converged": converged,
        "oscillation_detected": oscillation_detected,
        "contradiction_localization_precision": localization["precision"],
        "contradiction_localization_recall": localization["recall"],
        "contradiction_localization_f1": localization["f1"],
        "edges_relaxed": edges_relaxed,
        "edges_relaxed_per_s": edges_relaxed / runtime_s if runtime_s > 0 else 0.0,
        "plateau_step": diagnostics["plateau_step"],
        "hub_residual_tension_share": diagnostics["hub_dominance"][
            "hub_residual_tension_share"
        ],
    }
    return RelaxationResult(
        metrics=metrics,
        tension_history=tension_history,
        active_frontier_history=active_frontier_history,
        top_tension_nodes=top_nodes,
        diagnostics=diagnostics,
        final_values=values,
    )


def compute_tension(
    graph: SyntheticGraph,
    values: list[float],
    config: RelaxationConfig | None = None,
) -> tuple[float, list[float]]:
    node_tension = [0.0 for _ in values]
    total = 0.0
    for edge in graph.edges:
        weight = _effective_weight(edge, config) if config else edge.weight
        src_value = values[edge.src]
        dst_value = values[edge.dst]
        if edge.relation == CONTRADICTS:
            tension = weight * abs(src_value + dst_value)
        else:
            tension = weight * abs(src_value - dst_value)
        total += tension
        half = tension / 2.0
        node_tension[edge.src] += half
        node_tension[edge.dst] += half
    global_tension = total / max(1, len(graph.edges))
    return global_tension, node_tension


def contradiction_localization(
    node_scores: list[float],
    contradiction_pairs: list[tuple[int, int]],
) -> dict[str, float]:
    truth = {node for pair in contradiction_pairs for node in pair}
    if not truth:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    k = len(truth)
    predicted = {
        idx
        for idx, _score in sorted(
            enumerate(node_scores), key=lambda row: row[1], reverse=True
        )[:k]
    }
    true_positive = len(predicted & truth)
    precision = true_positive / max(1, len(predicted))
    recall = true_positive / max(1, len(truth))
    f1 = 2 * precision * recall / max(1e-12, precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


def contradiction_confusion_matrix(
    node_scores: list[float],
    contradiction_pairs: list[tuple[int, int]],
) -> dict[str, int]:
    truth = {node for pair in contradiction_pairs for node in pair}
    if not truth:
        return {"tp": 0, "fp": 0, "fn": 0, "tn": len(node_scores)}
    k = len(truth)
    predicted = {
        idx
        for idx, _score in sorted(
            enumerate(node_scores), key=lambda row: row[1], reverse=True
        )[:k]
    }
    all_nodes = set(range(len(node_scores)))
    return {
        "tp": len(predicted & truth),
        "fp": len(predicted - truth),
        "fn": len(truth - predicted),
        "tn": len(all_nodes - truth - predicted),
    }


def graph_diagnostics(
    *,
    graph: SyntheticGraph,
    values: list[float],
    node_tension: list[float],
    peak_node_tension: list[float],
    tension_history: list[float],
    active_frontier_history: list[int],
    config: RelaxationConfig,
) -> dict[str, object]:
    degrees = node_degrees(graph)
    residual_edges = residual_edge_tensions(graph, values, config)
    total_residual = sum(float(edge["tension"]) for edge in residual_edges)
    hub_threshold = degree_percentile(degrees, 0.95)
    hub_residual = sum(
        float(edge["tension"])
        for edge in residual_edges
        if int(edge["src_degree"]) >= hub_threshold
        or int(edge["dst_degree"]) >= hub_threshold
    )
    return {
        "tension_by_degree_bucket": tension_by_degree_bucket(degrees, node_tension),
        "top_residual_edges": residual_edges[:25],
        "hub_dominance": {
            "hub_degree_threshold": hub_threshold,
            "hub_residual_tension": hub_residual,
            "total_residual_tension": total_residual,
            "hub_residual_tension_share": (
                hub_residual / total_residual if total_residual else 0.0
            ),
        },
        "plateau_step": steps_until_plateau(tension_history),
        "active_frontier_history": active_frontier_history,
        "contradiction_localization_confusion_matrix": contradiction_confusion_matrix(
            peak_node_tension,
            graph.spec.contradiction_pairs,
        ),
    }


def node_degrees(graph: SyntheticGraph) -> list[int]:
    degrees = [0 for _ in range(graph.spec.nodes)]
    for edge in graph.edges:
        degrees[edge.src] += 1
        degrees[edge.dst] += 1
    return degrees


def residual_edge_tensions(
    graph: SyntheticGraph,
    values: list[float],
    config: RelaxationConfig,
) -> list[dict[str, float | int | str]]:
    degrees = node_degrees(graph)
    rows: list[dict[str, float | int | str]] = []
    for idx, edge in enumerate(graph.edges):
        tension = edge_tension(edge, values, config)
        rows.append(
            {
                "edge_index": idx,
                "src": edge.src,
                "dst": edge.dst,
                "relation": edge.relation,
                "weight": edge.weight,
                "tension": tension,
                "src_degree": degrees[edge.src],
                "dst_degree": degrees[edge.dst],
                "context": edge.context,
                "provenance": edge.provenance,
            }
        )
    return sorted(rows, key=lambda row: float(row["tension"]), reverse=True)


def node_update_multiplier(
    *,
    policy: str,
    degree: int,
    hub_threshold: int,
    hub_damping_factor: float,
) -> float:
    if policy == "reference" or policy == "residual_redistribution":
        return 1.0
    if policy == "degree_normalized":
        return 1.0 / sqrt(degree + 1.0)
    if policy == "hub_damping":
        return hub_damping_factor if degree >= hub_threshold else 1.0
    raise ValueError(f"unknown update_policy: {policy}")


def redistributed_active_edges(
    *,
    graph: SyntheticGraph,
    edge_indexes: list[int],
    degrees: list[int],
    hub_threshold: int,
    nonhub_fraction: float,
) -> list[int]:
    if not edge_indexes:
        return []
    hub_edges: list[int] = []
    nonhub_edges: list[int] = []
    for edge_idx in edge_indexes:
        edge = graph.edges[edge_idx]
        touches_hub = (
            degrees[edge.src] >= hub_threshold or degrees[edge.dst] >= hub_threshold
        )
        if touches_hub:
            hub_edges.append(edge_idx)
        else:
            nonhub_edges.append(edge_idx)
    if not hub_edges or not nonhub_edges:
        return edge_indexes
    target_nonhub = int(len(edge_indexes) * nonhub_fraction)
    selected_nonhub = nonhub_edges[: max(1, min(len(nonhub_edges), target_nonhub))]
    remaining = max(0, len(edge_indexes) - len(selected_nonhub))
    selected_hub = hub_edges[:remaining]
    return selected_nonhub + selected_hub


def edge_tension(
    edge: Edge, values: list[float], config: RelaxationConfig | None = None
) -> float:
    weight = _effective_weight(edge, config) if config else edge.weight
    src_value = values[edge.src]
    dst_value = values[edge.dst]
    if edge.relation == CONTRADICTS:
        return weight * abs(src_value + dst_value)
    return weight * abs(src_value - dst_value)


def tension_by_degree_bucket(
    degrees: list[int], node_tension: list[float]
) -> list[dict[str, float | int | str]]:
    buckets: list[tuple[str, int, int | None]] = [
        ("0", 0, 0),
        ("1-2", 1, 2),
        ("3-5", 3, 5),
        ("6-10", 6, 10),
        ("11-25", 11, 25),
        ("26-50", 26, 50),
        ("51+", 51, None),
    ]
    rows: list[dict[str, float | int | str]] = []
    for label, lower, upper in buckets:
        indexes = [
            idx
            for idx, degree in enumerate(degrees)
            if degree >= lower and (upper is None or degree <= upper)
        ]
        total = sum(node_tension[idx] for idx in indexes)
        rows.append(
            {
                "bucket": label,
                "nodes": len(indexes),
                "total_tension": total,
                "avg_tension": total / len(indexes) if indexes else 0.0,
                "max_tension": max((node_tension[idx] for idx in indexes), default=0.0),
            }
        )
    return rows


def degree_percentile(degrees: list[int], percentile: float) -> int:
    if not degrees:
        return 0
    ordered = sorted(degrees)
    idx = min(len(ordered) - 1, max(0, int((len(ordered) - 1) * percentile)))
    return ordered[idx]


def steps_until_plateau(
    history: list[float], tolerance: float = 1e-4, window: int = 5
) -> int:
    if len(history) < window + 1:
        return len(history)
    for idx in range(window, len(history)):
        recent = history[idx - window : idx + 1]
        deltas = [abs(recent[pos] - recent[pos - 1]) for pos in range(1, len(recent))]
        if max(deltas) <= tolerance:
            return idx - window + 1
    return len(history)


def _active_edges(graph: SyntheticGraph, active_nodes: set[int]) -> list[int]:
    seen: set[int] = set()
    for node in active_nodes:
        seen.update(graph.adjacency[node])
    return list(seen)


def _effective_weight(edge: Edge, config: RelaxationConfig | None) -> float:
    if not config or not config.provenance_weighting:
        return edge.weight
    if edge.provenance == "high_reliability":
        return edge.weight * 1.25
    if edge.provenance == "low_reliability":
        return edge.weight * 0.65
    return edge.weight


def _detect_oscillation(history: list[float], window: int) -> bool:
    if window < 4 or len(history) < window:
        return False
    recent = history[-window:]
    midpoint = window // 2
    left = recent[:midpoint]
    right = recent[midpoint:]
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    amplitude = max(recent) - min(recent)
    return amplitude > 0.01 and abs(left_mean - right_mean) < 0.002


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _random_edges(rng: random.Random, nodes: int, avg_degree: int) -> list[Edge]:
    target_edges = max(nodes - 1, nodes * avg_degree // 2)
    edges: list[Edge] = []
    seen: set[tuple[int, int]] = set()
    while len(edges) < target_edges:
        src = rng.randrange(nodes)
        dst = rng.randrange(nodes)
        if src == dst:
            continue
        key = (min(src, dst), max(src, dst))
        if key in seen:
            continue
        seen.add(key)
        edges.append(_support_edge(src, dst, rng))
    return edges


def _scale_free_edges(rng: random.Random, nodes: int, avg_degree: int) -> list[Edge]:
    edges: list[Edge] = []
    degree_bag = [0, 1]
    edges.append(_support_edge(0, 1, rng))
    links_per_node = max(1, avg_degree // 2)
    for node in range(2, nodes):
        targets: set[int] = set()
        while len(targets) < min(links_per_node, node):
            targets.add(rng.choice(degree_bag))
        for target in targets:
            edges.append(_support_edge(node, target, rng))
            degree_bag.extend([node, target])
    return edges


def _small_world_edges(rng: random.Random, nodes: int, avg_degree: int) -> list[Edge]:
    edges: list[Edge] = []
    seen: set[tuple[int, int]] = set()
    radius = max(1, avg_degree // 2)
    for src in range(nodes):
        for offset in range(1, radius + 1):
            dst = (src + offset) % nodes
            if rng.random() < 0.08:
                dst = rng.randrange(nodes)
            if src == dst:
                continue
            key = (min(src, dst), max(src, dst))
            if key not in seen:
                seen.add(key)
                edges.append(_support_edge(src, dst, rng))
    return edges


def _knowledge_edges(rng: random.Random, nodes: int, avg_degree: int) -> list[Edge]:
    edges = _random_edges(rng, nodes, avg_degree)
    relations = [SUPPORT, "is_a", "part_of", "causes", "mentions"]
    return [
        Edge(
            edge.src,
            edge.dst,
            rng.choice(relations),
            edge.weight,
            "default",
            edge.provenance,
            edge.timestamp,
        )
        for edge in edges
    ]


def _provenance_edges(rng: random.Random, nodes: int, avg_degree: int) -> list[Edge]:
    edges = _random_edges(rng, nodes, avg_degree)
    provenances = ["high_reliability", "synthetic", "low_reliability"]
    return [
        Edge(
            edge.src,
            edge.dst,
            edge.relation,
            edge.weight,
            "default",
            rng.choice(provenances),
            edge.timestamp,
        )
        for edge in edges
    ]


def _temporal_edges(rng: random.Random, nodes: int, avg_degree: int) -> list[Edge]:
    edges = _random_edges(rng, nodes, avg_degree)
    return [
        Edge(
            edge.src,
            edge.dst,
            TEMPORAL if rng.random() < 0.25 else edge.relation,
            edge.weight,
            "default",
            edge.provenance,
            idx,
        )
        for idx, edge in enumerate(edges)
    ]


def _multi_context_edges(rng: random.Random, nodes: int, avg_degree: int) -> list[Edge]:
    edges = _random_edges(rng, nodes, avg_degree)
    contexts = ["default", "context_a", "context_b", "context_c"]
    return [
        Edge(
            edge.src,
            edge.dst,
            CONTEXT if rng.random() < 0.2 else edge.relation,
            edge.weight,
            rng.choice(contexts),
            edge.provenance,
            edge.timestamp,
        )
        for edge in edges
    ]


def _support_edge(src: int, dst: int, rng: random.Random) -> Edge:
    return Edge(src=src, dst=dst, relation=SUPPORT, weight=rng.uniform(0.5, 1.0))


def _inject_contradictions(
    rng: random.Random,
    nodes: int,
    edges: list[Edge],
    contradiction_rate: float,
) -> tuple[list[Edge], list[tuple[int, int]]]:
    contradiction_count = max(1, int(sqrt(nodes) * contradiction_rate * 10))
    contradiction_pairs: list[tuple[int, int]] = []
    updated = list(edges)
    seen: set[tuple[int, int]] = set()
    while len(contradiction_pairs) < contradiction_count:
        src = rng.randrange(nodes)
        dst = rng.randrange(nodes)
        if src == dst:
            continue
        key = (min(src, dst), max(src, dst))
        if key in seen:
            continue
        seen.add(key)
        contradiction_pairs.append((src, dst))
        updated.append(
            Edge(
                src=src,
                dst=dst,
                relation=CONTRADICTS,
                weight=rng.uniform(1.5, 2.5),
                provenance="synthetic_injected_contradiction",
            )
        )
    return updated, contradiction_pairs
