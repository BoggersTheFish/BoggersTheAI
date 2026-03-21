from __future__ import annotations

import threading
from collections import deque
from typing import Dict, List, Set

from ..types import Edge, Node


def get_subgraph_around(
    nodes: Dict[str, Node],
    edges: List[Edge],
    node_id: str,
    depth: int = 2,
    max_nodes: int = 50,
) -> dict:
    """BFS neighborhood extraction around *node_id*.

    Returns ``{"nodes": {...}, "edges": [...]}`` containing
    only the subgraph within *depth* hops, capped at
    *max_nodes*.
    """
    if node_id not in nodes:
        return {"nodes": {}, "edges": []}

    adj: Dict[str, Set[str]] = {}
    for edge in edges:
        adj.setdefault(edge.src, set()).add(edge.dst)
        adj.setdefault(edge.dst, set()).add(edge.src)

    visited: Set[str] = set()
    queue: deque[tuple[str, int]] = deque()
    queue.append((node_id, 0))
    visited.add(node_id)

    while queue:
        current, d = queue.popleft()
        if len(visited) >= max_nodes:
            break
        if d >= depth:
            continue
        for neighbor in adj.get(current, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, d + 1))
                if len(visited) >= max_nodes:
                    break

    sub_nodes = {nid: nodes[nid] for nid in visited if nid in nodes}
    sub_edges = [e for e in edges if e.src in visited and e.dst in visited]
    return {"nodes": sub_nodes, "edges": sub_edges}


def batch_add_nodes(
    graph: object,
    nodes_data: List[dict],
) -> int:
    """Bulk insert nodes with a single lock acquisition.

    *graph* must be a ``UniversalLivingGraph`` (or any object
    with ``_lock`` and ``add_node``).  Returns the count of
    nodes actually added.
    """
    lock = getattr(graph, "_lock", None)
    if lock is None:
        lock = threading.RLock()

    added = 0
    with lock:
        for data in nodes_data:
            node_id = data.get("id") or data.get("node_id")
            if node_id is None:
                continue
            content = data.get("content", "")
            graph.add_node(
                node_id=node_id,
                content=content,
                topics=data.get("topics", []),
                activation=float(data.get("activation", 0.0)),
                stability=float(data.get("stability", 1.0)),
                base_strength=float(data.get("base_strength", 0.5)),
                last_wave=int(data.get("last_wave", 0)),
                attributes=data.get("attributes", {}),
                embedding=data.get("embedding", []),
            )
            added += 1
    return added


def find_connected_components(
    nodes: Dict[str, Node],
    edges: List[Edge],
) -> List[Set[str]]:
    """Union-find connected components.

    Treats edges as undirected.  Returns a list of sets,
    each set being one connected component of node IDs.
    """
    parent: Dict[str, str] = {nid: nid for nid in nodes}
    rank: Dict[str, int] = {nid: 0 for nid in nodes}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra == rb:
            return
        if rank[ra] < rank[rb]:
            ra, rb = rb, ra
        parent[rb] = ra
        if rank[ra] == rank[rb]:
            rank[ra] += 1

    for edge in edges:
        if edge.src in parent and edge.dst in parent:
            union(edge.src, edge.dst)

    components: Dict[str, Set[str]] = {}
    for nid in nodes:
        root = find(nid)
        components.setdefault(root, set()).add(nid)

    return list(components.values())


def get_nodes_by_activation_range(
    nodes: Dict[str, Node],
    lo: float = 0.0,
    hi: float = 1.0,
) -> List[Node]:
    """Filter nodes whose activation is in [lo, hi]."""
    return [node for node in nodes.values() if lo <= node.activation <= hi]
