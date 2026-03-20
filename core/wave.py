from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .graph.universal_living_graph import UniversalLivingGraph
from .types import Node, Tension


@dataclass(slots=True)
class WaveResult:
    strongest_node: Node | None
    tensions: List[Tension]
    collapsed_node_id: str | None
    evolved_nodes: List[Node]


def propagate(
    graph: UniversalLivingGraph,
    spread_factor: float = 0.2,
    min_activation: float = 0.05,
) -> List[Node]:
    updates: dict[str, float] = {}
    activated: List[Node] = []

    for node in graph.nodes.values():
        if node.collapsed or node.activation < min_activation:
            continue
        for neighbor_id, weight in graph.get_neighbors(node.id).items():
            updates[neighbor_id] = updates.get(neighbor_id, 0.0) + (
                node.activation * weight * spread_factor
            )

    for node_id, delta in updates.items():
        graph.update_activation(node_id, delta)
        updated_node = graph.get_node(node_id)
        if updated_node is not None:
            activated.append(updated_node)

    return activated


def relax(
    graph: UniversalLivingGraph,
    activated: List[Node],
    high_activation: float = 1.0,
    low_stability: float = 0.2,
) -> List[Tension]:
    tensions: List[Tension] = []
    seen = set()

    for node in activated:
        if node.id in seen or node.collapsed:
            continue
        seen.add(node.id)
        score = 0.0
        violations: List[str] = []

        if node.activation > high_activation:
            score += node.activation - high_activation
            violations.append("activation_overflow")
        if node.stability < low_stability:
            score += low_stability - node.stability
            violations.append("stability_too_low")

        if score > 0:
            tensions.append(Tension(node_id=node.id, score=score, violations=violations))

    return tensions


def break_weakest(
    graph: UniversalLivingGraph,
    tensions: List[Tension],
    tension_threshold: float = 0.6,
) -> str | None:
    if not tensions:
        return None
    total_tension = sum(t.score for t in tensions)
    if total_tension < tension_threshold:
        return None

    weakest_tension = min(
        tensions,
        key=lambda t: (
            graph.get_node(t.node_id).stability if graph.get_node(t.node_id) else 1.0,
            -t.score,
        ),
    )
    node = graph.get_node(weakest_tension.node_id)
    if node is None:
        return None

    node.collapsed = True
    node.activation = 0.0
    node.stability = 0.0
    return node.id


def evolve(graph: UniversalLivingGraph, collapsed_node_id: str | None) -> List[Node]:
    if collapsed_node_id is None:
        return []

    parent = graph.get_node(collapsed_node_id)
    if parent is None:
        return []

    child_id = f"{collapsed_node_id}:evolved"
    child = graph.add_node(
        node_id=child_id,
        content=f"Evolved from {collapsed_node_id}",
        topics=parent.topics,
        activation=0.2,
        stability=0.8,
        last_wave=parent.last_wave + 1,
    )
    graph.add_edge(collapsed_node_id, child_id, weight=0.1)
    return [child]


def run_wave(graph: UniversalLivingGraph) -> WaveResult:
    activated = propagate(graph)
    tensions = relax(graph, activated)
    collapsed = break_weakest(graph, tensions)
    evolved_nodes = evolve(graph, collapsed)
    strongest = graph.strongest_node()
    if strongest:
        strongest.last_wave += 1
    return WaveResult(
        strongest_node=strongest,
        tensions=tensions,
        collapsed_node_id=collapsed,
        evolved_nodes=evolved_nodes,
    )
