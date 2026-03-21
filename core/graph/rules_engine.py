from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from ..contradiction import detect_contradictions, resolve_contradiction
from .node import GraphNode
from .wave_propagation import (
    elect_strongest,
    normalise_activations,
    propagate,
    relax_toward_base_strength,
)

logger = logging.getLogger("boggers.graph.rules")

PRUNE_EDGE_THRESHOLD = 0.25
EMERGENCE_MAX_SPAWN = 2
EMERGENCE_BASE_ACTIVATION = 0.3
EMERGENCE_TENSION_MULTIPLIER = 0.2
EMERGENCE_BASE_STABILITY = 0.7
EMERGENCE_BASE_STRENGTH = 0.6
MERGE_SIMILARITY_THRESHOLD = 0.7
SPLIT_ACTIVATION_CAP = 0.95
SPLIT_ACTIVATION_FACTOR = 0.5
SPLIT_STABILITY_FACTOR = 0.9
NOVELTY_BOOST = 0.05
NOVELTY_RECENCY_WINDOW = 10


@dataclass(slots=True)
class RulesEngineCycleResult:
    strongest_node_id: str | None
    tensions: Dict[str, float]
    pruned_edges: int
    emergent_nodes: List[str] = field(default_factory=list)
    contradictions_found: int = 0
    contradictions_resolved: int = 0


def prune_edges(
    adjacency: Dict[str, Dict[str, float]],
    threshold: float = PRUNE_EDGE_THRESHOLD,
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


_TYPE_STABILITY_THRESHOLDS = {
    "conversation": 0.15,
    "insight": 0.25,
    "emergent": 0.3,
    "autonomous": 0.2,
    "default": 0.2,
}


def detect_tension(
    nodes: Dict[str, GraphNode],
    type_thresholds: Dict[str, float] | None = None,
) -> Dict[str, float]:
    thresholds = type_thresholds or _TYPE_STABILITY_THRESHOLDS
    tensions: Dict[str, float] = {}
    for node in nodes.values():
        if node.collapsed:
            continue
        node_type = str(node.attributes.get("type", "default"))
        threshold = thresholds.get(node_type, thresholds.get("default", 0.2))
        tension = abs(node.activation - node.base_strength)
        if tension > threshold:
            tensions[node.id] = tension
    return tensions


def spawn_emergence(
    nodes: Dict[str, GraphNode],
    tensions: Dict[str, float],
    edges: List[Tuple[str, str, float]],
    evolve_fn: Optional[Callable[[str, List[str], str], str]] = None,
) -> List[str]:
    created: List[str] = []
    if not tensions:
        return created

    sorted_tensions = sorted(tensions.items(), key=lambda item: item[1], reverse=True)
    for node_id, tension in sorted_tensions[:EMERGENCE_MAX_SPAWN]:
        emergent_id = f"emergent:{node_id}"
        if emergent_id in nodes:
            continue
        source = nodes[node_id]

        neighbor_ids = [dst for src, dst, _ in edges if src == node_id and dst in nodes]
        neighbor_contents = [
            nodes[nid].content for nid in neighbor_ids[:3] if nid in nodes
        ]

        content = f"Emerged from tension around {node_id}"
        if evolve_fn is not None:
            try:
                content = evolve_fn(
                    source.content,
                    neighbor_contents,
                    ",".join(source.topics),
                )
            except Exception as exc:
                logger.warning("LLM evolve failed for %s: %s", node_id, exc)

        nodes[emergent_id] = GraphNode(
            id=emergent_id,
            content=content,
            topics=source.topics[:],
            activation=min(
                1.0,
                EMERGENCE_BASE_ACTIVATION + tension * EMERGENCE_TENSION_MULTIPLIER,
            ),
            stability=EMERGENCE_BASE_STABILITY,
            base_strength=EMERGENCE_BASE_STRENGTH,
            attributes={"type": "emergent", "source": node_id},
        )
        edges.append((node_id, emergent_id, 0.3))
        created.append(emergent_id)
        logger.info(
            "Emergence: spawned %s from tension on %s (tension=%.3f)",
            emergent_id,
            node_id,
            tension,
        )
    return created


def merge_similar_topics(
    nodes: Dict[str, GraphNode],
    edges: List[Tuple[str, str, float]],
    similarity_threshold: float = MERGE_SIMILARITY_THRESHOLD,
) -> List[str]:
    merged: List[str] = []
    topic_groups: Dict[str, List[str]] = {}
    for node in nodes.values():
        if node.collapsed:
            continue
        for topic in node.topics:
            topic_groups.setdefault(topic.lower(), []).append(node.id)

    for topic, ids in topic_groups.items():
        if len(ids) < 2:
            continue
        keeper_id = ids[0]
        keeper = nodes.get(keeper_id)
        if keeper is None:
            continue
        for other_id in ids[1:]:
            other = nodes.get(other_id)
            if other is None or other.collapsed:
                continue
            topic_overlap = len(set(keeper.topics) & set(other.topics)) / max(
                len(set(keeper.topics) | set(other.topics)), 1
            )
            if topic_overlap >= similarity_threshold:
                keeper.activation = max(keeper.activation, other.activation)
                keeper.stability = max(keeper.stability, other.stability)
                other.collapsed = True
                other.activation = 0.0
                merged.append(other.id)
                logger.info(
                    "Merge: collapsed %s into %s (overlap=%.2f)",
                    other.id,
                    keeper_id,
                    topic_overlap,
                )
    return merged


def split_overactivated(
    nodes: Dict[str, GraphNode],
    edges: List[Tuple[str, str, float]],
    activation_cap: float = SPLIT_ACTIVATION_CAP,
) -> List[str]:
    created: List[str] = []
    for node in list(nodes.values()):
        if node.collapsed or node.activation < activation_cap:
            continue
        split_id = f"split:{node.id}"
        if split_id in nodes:
            continue
        original_activation = node.activation
        nodes[split_id] = GraphNode(
            id=split_id,
            content=f"Split from overactivated {node.id}",
            topics=node.topics[:],
            activation=node.activation * 0.5,
            stability=node.stability * 0.9,
            base_strength=node.base_strength,
            attributes={"type": "split", "source": node.id},
        )
        node.activation *= 0.5
        edges.append((node.id, split_id, 0.4))
        created.append(split_id)
        logger.info(
            "Split: created %s from overactivated %s (activation was %.3f)",
            split_id,
            node.id,
            original_activation,
        )
    return created


def reward_novelty(
    nodes: Dict[str, GraphNode],
    novelty_boost: float = NOVELTY_BOOST,
    recency_window: int = NOVELTY_RECENCY_WINDOW,
    current_wave: int = 0,
) -> int:
    boosted = 0
    for node in nodes.values():
        if node.collapsed:
            continue
        if current_wave - node.last_wave <= recency_window:
            node.activation = min(1.0, node.activation + novelty_boost)
            boosted += 1
    return boosted


def run_rules_cycle(
    nodes: Dict[str, GraphNode],
    adjacency: Dict[str, Dict[str, float]],
    edges: List[Tuple[str, str, float]],
    damping: float = 0.95,
    activation_cap: float = 1.0,
    semantic_weight: float = 0.3,
    evolve_fn: Optional[Callable[[str, List[str], str], str]] = None,
) -> RulesEngineCycleResult:
    strongest = elect_strongest(nodes)
    propagate(
        nodes,
        adjacency,
        damping=damping,
        activation_cap=activation_cap,
        semantic_weight=semantic_weight,
    )
    relax_toward_base_strength(nodes.values(), activation_cap=activation_cap)
    normalise_activations(nodes, cap=activation_cap)
    pruned = prune_edges(adjacency)
    merge_similar_topics(nodes, edges)
    split = split_overactivated(nodes, edges, activation_cap=activation_cap)

    # Contradiction detection + resolution
    contradictions = detect_contradictions(nodes)
    resolved = 0
    for c in contradictions:
        resolve_contradiction(nodes, c, strategy="weaken_lower")
        resolved += 1

    tensions = detect_tension(nodes)
    emergent = spawn_emergence(nodes, tensions, edges, evolve_fn=evolve_fn)
    strongest_id = strongest.id if strongest else None
    return RulesEngineCycleResult(
        strongest_node_id=strongest_id,
        tensions=tensions,
        pruned_edges=pruned,
        emergent_nodes=emergent + split,
        contradictions_found=len(contradictions),
        contradictions_resolved=resolved,
    )
