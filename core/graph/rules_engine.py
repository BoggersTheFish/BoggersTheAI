from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from .node import GraphNode
from .wave_propagation import elect_strongest, propagate, relax_toward_base_strength


@dataclass(slots=True)
class RulesEngineCycleResult:
    strongest_node_id: str | None
    tensions: Dict[str, float]
    pruned_edges: int
    emergent_nodes: List[str] = field(default_factory=list)


def prune_edges(
    adjacency: Dict[str, Dict[str, float]],
    threshold: float = 0.25,
) -> int:
    pruned = 0
    for src, neighbors in list(adjacency.items()):
        for dst, weight in list(neighbors.items()):
            if weight < threshold:
                del adjacency[src][dst]
                pruned += 1
        if not adjacency[src]:
            del adjacency[src]
    return pruned


def detect_tension(nodes: Dict[str, GraphNode]) -> Dict[str, float]:
    tensions: Dict[str, float] = {}
    for node in nodes.values():
        if node.collapsed:
            continue
        tension = abs(node.activation - node.base_strength)
        if tension > 0.2:
            tensions[node.id] = tension
    return tensions


def spawn_emergence(
    nodes: Dict[str, GraphNode],
    tensions: Dict[str, float],
    edges: List[Tuple[str, str, float]],
) -> List[str]:
    created: List[str] = []
    if not tensions:
        return created

    sorted_tensions = sorted(tensions.items(), key=lambda item: item[1], reverse=True)
    for node_id, tension in sorted_tensions[:2]:
        emergent_id = f"emergent:{node_id}"
        if emergent_id in nodes:
            continue
        source = nodes[node_id]
        nodes[emergent_id] = GraphNode(
            id=emergent_id,
            content=f"Emerged from tension around {node_id}",
            topics=source.topics[:],
            activation=min(1.0, 0.3 + tension * 0.2),
            stability=0.7,
            base_strength=0.6,
            attributes={"type": "emergent", "source": node_id},
        )
        edges.append((node_id, emergent_id, 0.3))
        created.append(emergent_id)
    return created


def run_rules_cycle(
    nodes: Dict[str, GraphNode],
    adjacency: Dict[str, Dict[str, float]],
    edges: List[Tuple[str, str, float]],
) -> RulesEngineCycleResult:
    strongest = elect_strongest(nodes)
    propagate(nodes, adjacency)
    relax_toward_base_strength(nodes.values())
    pruned = prune_edges(adjacency)
    tensions = detect_tension(nodes)
    emergent = spawn_emergence(nodes, tensions, edges)
    strongest_id = strongest.id if strongest else None
    return RulesEngineCycleResult(
        strongest_node_id=strongest_id,
        tensions=tensions,
        pruned_edges=pruned,
        emergent_nodes=emergent,
    )
