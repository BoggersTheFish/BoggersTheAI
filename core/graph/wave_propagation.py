from __future__ import annotations

from typing import Dict, Iterable

from .node import GraphNode


def elect_strongest(nodes: Dict[str, GraphNode]) -> GraphNode | None:
    active = [node for node in nodes.values() if not node.collapsed]
    if not active:
        return None
    return max(active, key=lambda n: (n.activation * n.base_strength, n.stability))


def propagate(
    nodes: Dict[str, GraphNode],
    adjacency: Dict[str, Dict[str, float]],
    spread_factor: float = 0.1,
) -> None:
    updates: Dict[str, float] = {}
    for node in nodes.values():
        if node.collapsed:
            continue
        for neighbor_id, weight in adjacency.get(node.id, {}).items():
            updates[neighbor_id] = updates.get(neighbor_id, 0.0) + (
                node.activation * weight * spread_factor
            )
    for node_id, delta in updates.items():
        if node_id in nodes and not nodes[node_id].collapsed:
            nodes[node_id].activation = min(1.0, nodes[node_id].activation + delta)


def relax_toward_base_strength(nodes: Iterable[GraphNode], decay: float = 0.85) -> None:
    for node in nodes:
        if node.collapsed:
            continue
        node.activation = node.base_strength + (node.activation - node.base_strength) * decay
