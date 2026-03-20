from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Set

from .types import Edge, Node


class UniversalLivingGraph:
    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adjacency: Dict[str, Dict[str, float]] = {}
        self._topic_index: Dict[str, Set[str]] = {}

    def add_node(
        self,
        node_id: str,
        content: str,
        topics: Iterable[str] | None = None,
        activation: float = 0.0,
        stability: float = 1.0,
        last_wave: int = 0,
    ) -> Node:
        normalized_topics = sorted(set(topics or []))
        node = Node(
            id=node_id,
            content=content,
            topics=normalized_topics,
            activation=activation,
            stability=stability,
            last_wave=last_wave,
        )
        old_node = self.nodes.get(node_id)
        self.nodes[node_id] = node
        self._adjacency.setdefault(node_id, {})

        if old_node:
            for topic in old_node.topics:
                topic_set = self._topic_index.get(topic)
                if topic_set:
                    topic_set.discard(node_id)
                    if not topic_set:
                        self._topic_index.pop(topic, None)

        for topic in normalized_topics:
            self._topic_index.setdefault(topic, set()).add(node_id)

        return node

    def add_edge(self, src: str, dst: str, weight: float = 1.0) -> Edge:
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError("Both src and dst must exist before adding an edge.")

        edge = Edge(src=src, dst=dst, weight=weight)
        self.edges.append(edge)
        self._adjacency.setdefault(src, {})[dst] = weight
        return edge

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> Dict[str, float]:
        return dict(self._adjacency.get(node_id, {}))

    def get_nodes_by_topic(self, topic: str) -> List[Node]:
        node_ids = self._topic_index.get(topic, set())
        return [self.nodes[node_id] for node_id in node_ids if node_id in self.nodes]

    def update_activation(self, node_id: str, delta: float) -> float:
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node '{node_id}' does not exist.")
        node.activation = max(0.0, node.activation + delta)
        return node.activation

    def strongest_node(self) -> Node | None:
        active_nodes = [node for node in self.nodes.values() if not node.collapsed]
        if not active_nodes:
            return None
        return max(active_nodes, key=lambda n: (n.activation, n.stability))

    def save(self, path: str | Path) -> None:
        serialized = {
            "nodes": [asdict(node) for node in self.nodes.values()],
            "edges": [asdict(edge) for edge in self.edges],
        }
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(serialized, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "UniversalLivingGraph":
        graph = cls()
        path = Path(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        for item in raw.get("nodes", []):
            graph.add_node(
                node_id=item["id"],
                content=item["content"],
                topics=item.get("topics", []),
                activation=float(item.get("activation", 0.0)),
                stability=float(item.get("stability", 1.0)),
                last_wave=int(item.get("last_wave", 0)),
            )
            graph.nodes[item["id"]].collapsed = bool(item.get("collapsed", False))

        for item in raw.get("edges", []):
            graph.add_edge(
                src=item["src"],
                dst=item["dst"],
                weight=float(item.get("weight", 1.0)),
            )
        return graph
