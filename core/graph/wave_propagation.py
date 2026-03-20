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
    damping: float = 0.95,
) -> None:
    updates: Dict[str, float] = {}
    for node in nodes.values():
        if node.collapsed:
            continue
        for neighbor_id, weight in adjacency.get(node.id, {}).items():
            if neighbor_id in nodes and not nodes[neighbor_id].collapsed:
                updates[neighbor_id] = updates.get(neighbor_id, 0.0) + (
                    node.activation * weight * spread_factor * damping
                )
    for node_id, delta in updates.items():
        if node_id in nodes:
            node = nodes[node_id]
            node.activation = max(0.0, min(1.0, node.activation + delta))


def relax_toward_base_strength(nodes: Iterable[GraphNode], decay: float = 0.85) -> None:
    for node in nodes:
        if node.collapsed:
            continue
        node.activation = (
            node.base_strength + (node.activation - node.base_strength) * decay
        )
