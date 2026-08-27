from __future__ import annotations

from thinking_system.graph.cig.graph import Graph


def representational_radius(graph: Graph, beta: float = 0.01) -> float:
    """Compute first-pass representational radius R.

    R = sum primitive_cost for primitive nodes + beta * edge_count.
    """
    if beta < 0.0:
        raise ValueError("beta must be non-negative")

    primitive_cost = 0.0
    for node in graph.nodes.values():
        metadata = node.metadata
        if metadata.get("primitive") is True or "primitive_cost" in metadata:
            primitive_cost += float(metadata.get("primitive_cost", 0.0))
    return float(primitive_cost + beta * len(graph.edges))
