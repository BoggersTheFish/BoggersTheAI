"""Deterministic replay for canonical TS receipts."""

from __future__ import annotations

from typing import Any

from .receipts import validate_receipt_hash
from .transaction import graph_snapshot, graph_state_hash


def replay_receipt(graph: Any, receipt: Any, *, verify_hash: bool = True) -> str:
    payload = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
    if verify_hash and not validate_receipt_hash(payload):
        raise ValueError("receipt hash validation failed")

    base_hash = str(payload.get("base_graph_hash", ""))
    current_hash = graph_state_hash(graph)
    if base_hash and current_hash != base_hash:
        raise ValueError("current graph hash does not match receipt base_graph_hash")

    snapshot = graph_snapshot(graph)
    delta = payload.get("committed_graph_delta", {"nodes": [], "edges": []})
    decision = str(payload.get("commit_decision", ""))
    try:
        if decision not in {"commit", "branch"}:
            post_hash = graph_state_hash(graph)
            expected_post = str(payload.get("post_state_hash", ""))
            if expected_post and post_hash != expected_post:
                raise ValueError("replay post_state_hash mismatch")
            return post_hash

        for node in sorted(delta.get("nodes", []), key=lambda item: item["id"]):
            graph.add_node(
                node_id=node["id"],
                content=node.get("content", ""),
                topics=node.get("topics", []),
                activation=float(node.get("activation", 0.0)),
                stability=float(node.get("stability", 1.0)),
                base_strength=float(node.get("base_strength", 0.5)),
                last_wave=int(node.get("last_wave", 0)),
                attributes=node.get("attributes", {}),
                embedding=node.get("embedding", []),
            )
        for edge in sorted(
            delta.get("edges", []),
            key=lambda item: (
                item.get("src", ""),
                item.get("dst", ""),
                item.get("relation", ""),
                item.get("weight", 0.0),
            ),
        ):
            if edge["src"] in graph.nodes and edge["dst"] in graph.nodes:
                graph.add_edge(
                    edge["src"],
                    edge["dst"],
                    weight=float(edge.get("weight", 1.0)),
                    relation=edge.get("relation", "relates"),
                )
        post_hash = graph_state_hash(graph)
        expected_post = str(payload.get("post_state_hash", ""))
        if expected_post and post_hash != expected_post:
            raise ValueError("replay post_state_hash mismatch")
        return post_hash
    except Exception:
        _restore_graph(graph, snapshot)
        raise


def _restore_graph(graph: Any, snapshot: Any) -> None:
    nodes, edges = snapshot
    graph.nodes = nodes
    graph.edges = edges
    if hasattr(graph, "_rebuild_adjacency"):
        graph._rebuild_adjacency()
    if hasattr(graph, "_rebuild_topic_index"):
        graph._rebuild_topic_index()
    if hasattr(graph, "_dirty_nodes"):
        graph._dirty_nodes = set(nodes)
    if hasattr(graph, "_strongest_cache_valid"):
        graph._strongest_cache_valid = False
