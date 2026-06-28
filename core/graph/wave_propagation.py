from __future__ import annotations

import logging
from typing import Dict, Iterable, List

try:
    import numpy as np

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    np = None  # type: ignore

from ..embeddings import cosine_similarity
from .node import GraphNode

logger = logging.getLogger("boggers.graph.vectorized")

GLOBAL_ACTIVATION_CAP = 1.0


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
    activation_cap: float = GLOBAL_ACTIVATION_CAP,
    semantic_weight: float = 0.3,
) -> None:
    updates: Dict[str, float] = {}

    for node in nodes.values():
        if node.collapsed:
            continue
        for neighbor_id, weight in adjacency.get(node.id, {}).items():
            if neighbor_id not in nodes or nodes[neighbor_id].collapsed:
                continue

            topo_signal = node.activation * weight * spread_factor * damping

            sem_signal = 0.0
            if semantic_weight > 0 and node.embedding and nodes[neighbor_id].embedding:
                sim = cosine_similarity(node.embedding, nodes[neighbor_id].embedding)
                sem_signal = (
                    node.activation * sim * spread_factor * damping * semantic_weight
                )

            total = topo_signal + sem_signal
            updates[neighbor_id] = updates.get(neighbor_id, 0.0) + total

    if updates:
        _normalise_updates(updates, nodes, activation_cap)

    for node_id, delta in updates.items():
        if node_id in nodes:
            node = nodes[node_id]
            node.activation = max(0.0, min(activation_cap, node.activation + delta))


def _normalise_updates(
    updates: Dict[str, float],
    nodes: Dict[str, GraphNode],
    cap: float,
) -> None:
    if not updates:
        return
    max_delta = max(abs(v) for v in updates.values())
    if max_delta < 1e-12:
        return
    for node_id in updates:
        current = nodes[node_id].activation if node_id in nodes else 0.0
        headroom = max(0.0, cap - current)
        if updates[node_id] > headroom:
            updates[node_id] = headroom


def relax_toward_base_strength(
    nodes: Iterable[GraphNode],
    decay: float = 0.85,
    activation_cap: float = GLOBAL_ACTIVATION_CAP,
) -> None:
    for node in nodes:
        if node.collapsed:
            continue
        node.activation = (
            node.base_strength + (node.activation - node.base_strength) * decay
        )
        node.activation = max(0.0, min(activation_cap, node.activation))


def normalise_activations(
    nodes: Dict[str, GraphNode],
    cap: float = GLOBAL_ACTIVATION_CAP,
) -> int:
    clamped = 0
    for node in nodes.values():
        if node.collapsed:
            continue
        if node.activation > cap:
            node.activation = cap
            clamped += 1
        elif node.activation < 0.0:
            node.activation = 0.0
            clamped += 1


# =============================================================================
# Phase 1: Vectorized / Accelerated Wave Primitives (numpy when available)
# Pure Python fallback for on-device compatibility and determinism.
# =============================================================================


def propagate_vectorized(
    nodes: Dict[str, GraphNode],
    adjacency: Dict[str, Dict[str, float]],
    spread_factor: float = 0.1,
    damping: float = 0.95,
    activation_cap: float = GLOBAL_ACTIVATION_CAP,
    semantic_weight: float = 0.3,
) -> None:
    """Phase 1 accelerated propagate.
    Falls back to pure if no numpy or small graph.
    """
    if not HAS_NUMPY or len(nodes) < 200:
        # fallback to original
        propagate(
            nodes, adjacency, spread_factor, damping, activation_cap, semantic_weight
        )
        return

    # Build id list and arrays for speed
    node_ids: List[str] = list(nodes.keys())
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)

    activations = np.array(
        [nodes[nid].activation for nid in node_ids], dtype=np.float64
    )
    caps = np.full(n, activation_cap, dtype=np.float64)

    # Sparse updates via dict is still needed for generality, but vectorize deltas
    deltas = np.zeros(n, dtype=np.float64)

    for i, nid in enumerate(node_ids):
        if nodes[nid].collapsed:
            continue
        neigh = adjacency.get(nid, {})
        if not neigh:
            continue
        # topo
        for neigh_id, weight in neigh.items():
            if neigh_id not in id_to_idx or nodes[neigh_id].collapsed:
                continue
            j = id_to_idx[neigh_id]
            topo = activations[i] * weight * spread_factor * damping
            deltas[j] += topo

            # semantic (still per-pair, but array update)
            if (
                semantic_weight > 0
                and nodes[nid].embedding
                and nodes[neigh_id].embedding
            ):
                sim = cosine_similarity(nodes[nid].embedding, nodes[neigh_id].embedding)
                sem = activations[i] * sim * spread_factor * damping * semantic_weight
                deltas[j] += sem

    # apply
    activations = np.minimum(caps, activations + deltas)
    activations = np.maximum(0.0, activations)

    for i, nid in enumerate(node_ids):
        if not nodes[nid].collapsed:
            nodes[nid].activation = float(activations[i])


def relax_vectorized(
    nodes: Iterable[GraphNode],
    decay: float = 0.85,
    activation_cap: float = GLOBAL_ACTIVATION_CAP,
) -> None:
    if not HAS_NUMPY or len(list(nodes)) < 200:  # rough
        relax_toward_base_strength(nodes, decay, activation_cap)
        return
    # For simplicity, fall back for relax (cheap)
    relax_toward_base_strength(nodes, decay, activation_cap)
    return
