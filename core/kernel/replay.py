"""Deterministic replay for canonical TS receipts."""

from __future__ import annotations

from typing import Any

from .transaction import graph_state_hash


def replay_receipt(graph: Any, receipt: Any) -> str:
    payload = receipt.to_dict() if hasattr(receipt, "to_dict") else dict(receipt)
    delta = payload.get("committed_graph_delta", {"nodes": [], "edges": []})
    decision = str(payload.get("commit_decision", ""))
    if decision not in {"commit", "branch"}:
        return graph_state_hash(graph)

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
    return graph_state_hash(graph)
