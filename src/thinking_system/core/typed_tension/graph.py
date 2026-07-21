"""Domain-neutral graph state for typed tension runtimes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .types import Edge, Node, to_jsonable


@dataclass
class GraphState:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.nodes:
            raise ValueError(f"unknown edge source: {edge.source}")
        if edge.target not in self.nodes:
            raise ValueError(f"unknown edge target: {edge.target}")
        self.edges.append(edge)

    def outgoing(self, node_id: str, relation: str | None = None) -> list[Edge]:
        return [
            edge
            for edge in self.edges
            if edge.source == node_id
            and (relation is None or edge.relation == relation)
        ]

    def incoming(self, node_id: str, relation: str | None = None) -> list[Edge]:
        return [
            edge
            for edge in self.edges
            if edge.target == node_id
            and (relation is None or edge.relation == relation)
        ]

    def has_edge(self, source: str, target: str, relation: str | None = None) -> bool:
        return any(
            edge.source == source
            and edge.target == target
            and (relation is None or edge.relation == relation)
            for edge in self.edges
        )

    def edge_keys(self) -> set[tuple[str, str, str]]:
        return {(edge.source, edge.target, edge.relation) for edge in self.edges}

    def extend(self, nodes: Iterable[Node] = (), edges: Iterable[Edge] = ()) -> None:
        for node in nodes:
            self.add_node(node)
        for edge in edges:
            self.add_edge(edge)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": {
                node_id: node.to_dict() for node_id, node in sorted(self.nodes.items())
            },
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": to_jsonable(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "GraphState":
        graph = cls(metadata=dict(payload.get("metadata") or {}))
        raw_nodes = payload.get("nodes") or {}
        if isinstance(raw_nodes, dict):
            raw_nodes = raw_nodes.values()
        for item in raw_nodes:
            graph.add_node(
                Node(
                    node_id=str(item.get("node_id") or item.get("id")),
                    kind=str(item.get("kind", "state")),
                    activation=float(item.get("activation", 0.0)),
                    stability=float(item.get("stability", 1.0)),
                    data=dict(item.get("data") or {}),
                )
            )
        for item in payload.get("edges") or []:
            graph.add_edge(
                Edge(
                    source=str(item.get("source") or item.get("from")),
                    target=str(item.get("target") or item.get("to")),
                    relation=str(item.get("relation", "constraint")),
                    weight=float(item.get("weight", 1.0)),
                    directed=bool(item.get("directed", True)),
                    data=dict(item.get("data") or {}),
                )
            )
        return graph
