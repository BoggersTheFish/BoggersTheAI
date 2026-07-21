from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

import numpy as np

from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.node import Node


@dataclass
class CIGraph:
    """Mutable deterministic Concept/Constraint Intelligence Graph state."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    def add_node(self, node: Node) -> None:
        if node.id in self.nodes:
            raise ValueError(f"Duplicate node id: {node.id}")
        self.nodes[node.id] = node

    def add_edge(self, edge: Edge) -> None:
        if edge.source not in self.nodes:
            raise KeyError(f"Edge source does not exist: {edge.source}")
        if edge.target not in self.nodes:
            raise KeyError(f"Edge target does not exist: {edge.target}")
        self.edges.append(edge)

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def node(self, node_id: str) -> Node:
        """Compatibility alias for get_node."""
        return self.get_node(node_id)

    def edge(self, edge_key: int | str) -> Edge:
        """Return an edge by list index or legacy extra `id` value."""
        if isinstance(edge_key, int):
            return self.edges[edge_key]
        for edge in self.edges:
            if getattr(edge, "id", None) == edge_key:
                return edge
        raise KeyError(edge_key)

    def reset_activations(self, value: float = 0.0) -> None:
        for node in self.nodes.values():
            node.activation = value

    def activation_vector(self) -> np.ndarray:
        return np.array([node.activation for node in self.nodes.values()], dtype=float)

    def set_activation(self, node_id: str, activation: float) -> None:
        self.get_node(node_id).activation = activation

    def copy(self) -> CIGraph:
        return deepcopy(self)

    def clone(self) -> CIGraph:
        return self.copy()

    def incoming_edges(self, node_id: str) -> list[Edge]:
        return [edge for edge in self.edges if edge.target == node_id]

    def outgoing_edges(self, node_id: str) -> list[Edge]:
        return [edge for edge in self.edges if edge.source == node_id]

    def outgoing(self, node_id: str) -> list[Edge]:
        """Compatibility alias for outgoing_edges."""
        return self.outgoing_edges(node_id)

    def split_by_context(self) -> dict[str, CIGraph]:
        """Return subgraphs grouped by node context metadata.

        TODO: Replace this with a proper context-boundary algorithm that can
        preserve selected cross-context constraints.
        """
        grouped: dict[str, CIGraph] = {}
        for node in self.nodes.values():
            context = _node_context(node)
            grouped.setdefault(context, CIGraph()).add_node(deepcopy(node))

        for edge in self.edges:
            source_context = _node_context(self.nodes[edge.source])
            target_context = _node_context(self.nodes[edge.target])
            if source_context == target_context:
                grouped[source_context].add_edge(deepcopy(edge))

        return grouped

    @classmethod
    def from_records(
        cls,
        nodes: list[dict[str, object]],
        edges: list[dict[str, object]],
    ) -> CIGraph:
        graph = cls()
        for node_record in nodes:
            graph.add_node(Node(**_normalize_node_record(node_record)))
        for edge_record in edges:
            graph.add_edge(Edge(**_normalize_edge_record(edge_record)))
        return graph


def _normalize_node_record(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    normalized.setdefault("label", normalized["id"])
    return normalized


def _normalize_edge_record(record: dict[str, object]) -> dict[str, object]:
    normalized = dict(record)
    normalized.setdefault("relation", "related")
    return normalized


def _node_context(node: Node) -> str:
    context = node.metadata.get("context")
    if context is None:
        context = getattr(node, "context", None)
    return str(context or "default")


Graph = CIGraph
