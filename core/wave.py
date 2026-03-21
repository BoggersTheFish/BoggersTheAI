from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import List

from .contradiction import detect_contradictions, resolve_contradiction
from .graph.rules_engine import detect_tension as rules_detect_tension
from .graph.universal_living_graph import UniversalLivingGraph
from .types import Node, Tension

_wave_history: deque[dict] = deque(maxlen=100)


def get_wave_history() -> list[dict]:
    return list(_wave_history)


@dataclass(slots=True)
class WaveResult:
    strongest_node: Node | None
    tensions: List[Tension]
    collapsed_node_id: str | None
    evolved_nodes: List[Node]
    contradictions_found: int = 0


def propagate(
    graph: UniversalLivingGraph,
    spread_factor: float = 0.2,
    min_activation: float = 0.05,
) -> List[Node]:
    updates: dict[str, float] = {}
    activated: List[Node] = []
    cap = float(graph._wave_settings.get("activation_cap", 1.0))
    damping = float(graph._wave_settings.get("damping", 0.95))

    for node in graph.nodes.values():
        if node.collapsed or node.activation < min_activation:
            continue
        for neighbor_id, weight in graph.get_neighbors(node.id).items():
            if neighbor_id not in graph.nodes or graph.nodes[neighbor_id].collapsed:
                continue
            topo = node.activation * weight * spread_factor * damping
            sem = 0.0
            if node.embedding and graph.nodes[neighbor_id].embedding:
                from .embeddings import cosine_similarity

                sim = cosine_similarity(
                    node.embedding, graph.nodes[neighbor_id].embedding
                )
                semantic_w = float(graph._wave_settings.get("semantic_weight", 0.3))
                sem = node.activation * sim * spread_factor * damping * semantic_w
            updates[neighbor_id] = updates.get(neighbor_id, 0.0) + topo + sem

    for node_id, delta in updates.items():
        node = graph.nodes.get(node_id)
        if node is not None:
            node.activation = max(0.0, min(cap, node.activation + delta))
            graph._dirty_nodes.add(node_id)
            activated.append(node)

    return activated


def relax(
    graph: UniversalLivingGraph,
    activated: List[Node],
    high_activation: float = 1.0,
    low_stability: float = 0.2,
) -> List[Tension]:
    tensions: List[Tension] = []
    seen = set()
    cap = float(graph._wave_settings.get("activation_cap", 1.0))

    graph_nodes = {
        nid: graph._to_graph_node(n)
        for nid, n in graph.nodes.items()
        if not n.collapsed
    }
    rules_tensions = rules_detect_tension(graph_nodes)

    for node in activated:
        if node.id in seen or node.collapsed:
            continue
        seen.add(node.id)
        score = 0.0
        violations: List[str] = []

        if node.activation > cap:
            score += node.activation - cap
            violations.append("activation_overflow")
            node.activation = cap
        if node.stability < low_stability:
            score += low_stability - node.stability
            violations.append("stability_too_low")

        if node.id in rules_tensions:
            score += rules_tensions[node.id]
            violations.append("rules_engine_tension")

        if score > 0:
            tensions.append(
                Tension(node_id=node.id, score=score, violations=violations)
            )

    contradictions = detect_contradictions(graph.nodes)
    for c in contradictions:
        resolve_contradiction(graph.nodes, c, strategy="weaken_lower")

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

    neighbor_ids = list(graph.get_neighbors(collapsed_node_id).keys())[:3]
    neighbor_contents = [
        graph.nodes[nid].content for nid in neighbor_ids if nid in graph.nodes
    ]

    content = f"Evolved from {collapsed_node_id}"
    if graph._evolve_fn is not None:
        try:
            content = graph._evolve_fn(
                parent.content,
                neighbor_contents,
                ",".join(parent.topics),
            )
        except Exception:
            pass

    child = graph.add_node(
        node_id=child_id,
        content=content,
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

    from .graph.wave_propagation import normalise_activations as _norm

    gn = {
        nid: graph._to_graph_node(n)
        for nid, n in graph.nodes.items()
        if not n.collapsed
    }
    cap = float(graph._wave_settings.get("activation_cap", 1.0))
    _norm(gn, cap=cap)
    for nid, gnode in gn.items():
        if nid in graph.nodes:
            graph.nodes[nid].activation = gnode.activation

    _wave_history.append(
        {
            "strongest": strongest.id if strongest else None,
            "tension_count": len(tensions),
            "total_tension": sum(t.score for t in tensions),
            "collapsed": collapsed,
            "evolved_count": len(evolved_nodes),
        }
    )
    return WaveResult(
        strongest_node=strongest,
        tensions=tensions,
        collapsed_node_id=collapsed,
        evolved_nodes=evolved_nodes,
    )
