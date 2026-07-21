"""Reference baselines for graph contradiction localization."""

from __future__ import annotations

import random

from thinking_system.benchmarks.graph_scaling.tasks.scaling import (
    CONTRADICTS,
    SyntheticGraph,
    contradiction_localization,
)


def degree_baseline(graph: SyntheticGraph) -> dict[str, float]:
    scores = [0.0 for _ in range(graph.spec.nodes)]
    for edge in graph.edges:
        scores[edge.src] += edge.weight
        scores[edge.dst] += edge.weight
    return contradiction_localization(scores, graph.spec.contradiction_pairs)


def pagerank_like_baseline(
    graph: SyntheticGraph, steps: int = 32, damping: float = 0.85
) -> dict[str, float]:
    """Small dependency-free PageRank-like diffusion baseline."""

    n = graph.spec.nodes
    scores = [1.0 / n for _ in range(n)]
    neighbors: list[list[int]] = [[] for _ in range(n)]
    contradiction_boost = [0.0 for _ in range(n)]

    for edge in graph.edges:
        neighbors[edge.src].append(edge.dst)
        neighbors[edge.dst].append(edge.src)
        if edge.relation == CONTRADICTS:
            contradiction_boost[edge.src] += edge.weight
            contradiction_boost[edge.dst] += edge.weight

    for _ in range(steps):
        next_scores = [(1.0 - damping) / n for _ in range(n)]
        for src, src_neighbors in enumerate(neighbors):
            if not src_neighbors:
                continue
            share = damping * scores[src] / len(src_neighbors)
            for dst in src_neighbors:
                next_scores[dst] += share
        scores = [
            score + 0.05 * contradiction_boost[idx]
            for idx, score in enumerate(next_scores)
        ]

    return contradiction_localization(scores, graph.spec.contradiction_pairs)


def random_residual_baseline(graph: SyntheticGraph) -> dict[str, float]:
    """Deterministic random localization floor."""

    rng = random.Random(graph.spec.seed + 1009)
    scores = [rng.random() for _ in range(graph.spec.nodes)]
    return contradiction_localization(scores, graph.spec.contradiction_pairs)
