from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from ..types import Edge, Node
from .rules_engine import RulesEngineCycleResult, detect_tension, run_rules_cycle, spawn_emergence

logger = logging.getLogger("boggers.graph")


class UniversalLivingGraph:
    def __init__(self, config: object | None = None, auto_load: bool = True) -> None:
        self.config = config
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adjacency: Dict[str, Dict[str, float]] = {}
        self._topic_index: Dict[str, Set[str]] = {}
        self.graph_path = self._resolve_graph_path(config)
        self._wave_settings = self._resolve_wave_settings(config)
        self._wave_stop_event = threading.Event()
        self._wave_thread: threading.Thread | None = None
        self._wave_cycle_count = 0
        self._last_tension = 0.0
        self._lock = threading.RLock()
        if auto_load:
            self.load()

    def _resolve_graph_path(self, config: object | None) -> Path:
        if config is None:
            return Path("graph.json")
        if isinstance(config, dict):
            runtime = config.get("runtime", {})
            candidate = runtime.get("graph_path") or config.get("graph_path")
            return Path(candidate) if candidate else Path("graph.json")
        candidate = (
            getattr(config, "graph_path", None)
            or getattr(config, "graph_file", None)
            or getattr(config, "graph_json_path", None)
        )
        return Path(candidate) if candidate else Path("graph.json")

    def _resolve_wave_settings(self, config: object | None) -> Dict[str, object]:
        defaults: Dict[str, object] = {
            "interval_seconds": 30,
            "enabled": True,
            "log_each_cycle": True,
            "auto_save": True,
            "spread_factor": 0.1,
            "relax_decay": 0.85,
            "tension_threshold": 0.2,
            "prune_threshold": 0.25,
        }
        if config is None:
            return defaults
        if isinstance(config, dict):
            wave = config.get("wave", {})
            return {**defaults, **wave} if isinstance(wave, dict) else defaults
        wave = getattr(config, "wave", None)
        if isinstance(wave, dict):
            return {**defaults, **wave}
        return defaults

    def add_node(
        self,
        node_id: str,
        content: str,
        topics: Iterable[str] | None = None,
        activation: float = 0.0,
        stability: float = 1.0,
        base_strength: float = 0.5,
        last_wave: int = 0,
        attributes: dict | None = None,
    ) -> Node:
        with self._lock:
            normalized_topics = sorted(set(topics or []))
            old = self.nodes.get(node_id)
            node = Node(
                id=node_id,
                content=content,
                topics=normalized_topics,
                activation=float(activation),
                stability=float(stability),
                base_strength=float(base_strength),
                last_wave=int(last_wave),
                collapsed=False if old is None else old.collapsed,
                attributes=dict(attributes or {}),
            )
            self.nodes[node_id] = node
            self._adjacency.setdefault(node_id, {})

            if old:
                for topic in old.topics:
                    topic_set = self._topic_index.get(topic)
                    if topic_set:
                        topic_set.discard(node_id)
                        if not topic_set:
                            self._topic_index.pop(topic, None)
            for topic in normalized_topics:
                self._topic_index.setdefault(topic, set()).add(node_id)
            return node

    def add_edge(
        self, src: str, dst: str, weight: float = 1.0, relation: str = "relates"
    ) -> Edge:
        with self._lock:
            if src not in self.nodes or dst not in self.nodes:
                raise KeyError("Both src and dst must exist before adding an edge.")
            edge = Edge(src=src, dst=dst, weight=float(weight), relation=relation)
            self.edges.append(edge)
            self._adjacency.setdefault(src, {})[dst] = float(weight)
            return edge

    def get_node(self, node_id: str) -> Node | None:
        return self.nodes.get(node_id)

    def get_neighbors(self, node_id: str) -> Dict[str, float]:
        return dict(self._adjacency.get(node_id, {}))

    def get_nodes_by_topic(self, topic: str) -> List[Node]:
        node_ids = self._topic_index.get(topic, set())
        return [self.nodes[node_id] for node_id in node_ids if node_id in self.nodes]

    def get_activated_subgraph(self, query_topic: str, top_k: int = 5) -> list[dict]:
        """Return top activated nodes + context for synthesis."""
        topic = query_topic.strip().lower()
        candidates: List[Node] = []
        seen_ids: set[str] = set()

        if topic:
            for node in self.get_nodes_by_topic(topic):
                if node.id not in seen_ids and not node.collapsed:
                    candidates.append(node)
                    seen_ids.add(node.id)

        if len(candidates) < top_k:
            ranked_global = sorted(
                [node for node in self.nodes.values() if not node.collapsed],
                key=lambda n: (n.activation, n.stability, n.base_strength, n.last_wave),
                reverse=True,
            )
            for node in ranked_global:
                if node.id in seen_ids:
                    continue
                candidates.append(node)
                seen_ids.add(node.id)
                if len(candidates) >= top_k:
                    break

        return [asdict(node) for node in candidates[:top_k]]

    def get_conversation_history(self, last_n: int = 8) -> list[dict]:
        conversation_nodes = [
            node
            for node in self.nodes.values()
            if not node.collapsed and "conversation" in [topic.lower() for topic in node.topics]
        ]
        ranked = sorted(
            conversation_nodes,
            key=lambda node: (
                str(node.attributes.get("timestamp", "")),
                node.last_wave,
                node.id,
            ),
            reverse=True,
        )
        history = []
        for node in ranked[: max(0, int(last_n))]:
            history.append(
                {
                    "id": node.id,
                    "content": node.content,
                    "topics": node.topics,
                    "activation": node.activation,
                    "stability": node.stability,
                    "timestamp": node.attributes.get("timestamp", ""),
                    "session_id": node.attributes.get("session_id", ""),
                }
            )
        return list(reversed(history))

    def update_activation(self, node_id: str, delta: float) -> float:
        with self._lock:
            node = self.nodes.get(node_id)
            if node is None:
                raise KeyError(f"Node '{node_id}' does not exist.")
            node.activation = max(0.0, min(1.0, node.activation + delta))
            return node.activation

    def strongest_node(self) -> Node | None:
        active = [node for node in self.nodes.values() if not node.collapsed]
        if not active:
            return None
        return max(active, key=lambda n: (n.activation * n.base_strength, n.stability))

    def elect_strongest(self) -> Node | None:
        return self.strongest_node()

    def propagate(self) -> None:
        with self._lock:
            updates: Dict[str, float] = {}
            for node in self.nodes.values():
                if node.collapsed:
                    continue
                for neighbor_id, weight in self._adjacency.get(node.id, {}).items():
                    updates[neighbor_id] = updates.get(neighbor_id, 0.0) + (
                    node.activation * weight * float(self._wave_settings.get("spread_factor", 0.1))
                )
            for node_id, delta in updates.items():
                self.update_activation(node_id, delta)

    def relax(self) -> None:
        with self._lock:
            for node in self.nodes.values():
                if node.collapsed:
                    continue
                node.activation = node.base_strength + (node.activation - node.base_strength) * float(self._wave_settings.get("relax_decay", 0.85))

    def prune(self, threshold: float | None = None) -> int:
        if threshold is None:
            threshold = float(self._wave_settings.get("prune_threshold", 0.25))
        kept_edges: List[Edge] = []
        pruned = 0
        for edge in self.edges:
            if edge.weight >= threshold:
                kept_edges.append(edge)
            else:
                pruned += 1
        self.edges = kept_edges
        self._rebuild_adjacency()
        return pruned

    def detect_tensions(self) -> Dict[str, float]:
        with self._lock:
            tensions: Dict[str, float] = {}
            for node in self.nodes.values():
                if node.collapsed:
                    continue
                tension = abs(node.activation - node.base_strength)
                if tension > float(self._wave_settings.get("tension_threshold", 0.2)):
                    tensions[node.id] = tension
            return tensions

    def run_wave_cycle(self) -> RulesEngineCycleResult:
        with self._lock:
            graph_nodes = {
                node_id: self._to_graph_node(node)
                for node_id, node in self.nodes.items()
                if not node.collapsed
            }
            adjacency = {src: dict(dst) for src, dst in self._adjacency.items()}
            edges = [(edge.src, edge.dst, edge.weight) for edge in self.edges]
            result = run_rules_cycle(graph_nodes, adjacency, edges)
            self._apply_graph_node_updates(graph_nodes)
            self._adjacency = adjacency
            self._sync_edges_from_tuples(edges)
            return result

    def save(self, path: str | Path | None = None) -> Path:
        with self._lock:
            target = Path(path) if path is not None else self.graph_path
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "nodes": [asdict(node) for node in self.nodes.values()],
                "edges": [asdict(edge) for edge in self.edges],
            }
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return target

    def load(self, path: str | Path | None = None) -> "UniversalLivingGraph":
        with self._lock:
            target = Path(path) if path is not None else self.graph_path
            if not target.exists():
                return self
            raw = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or "nodes" not in raw:
                logger.warning("Invalid graph.json structure; starting fresh")
                return self
            self.nodes.clear()
            self.edges.clear()
            self._adjacency.clear()
            self._topic_index.clear()
            for item in raw.get("nodes", []):
                node = self.add_node(
                    node_id=item["id"],
                    content=item.get("content", ""),
                    topics=item.get("topics", []),
                    activation=float(item.get("activation", 0.0)),
                    stability=float(item.get("stability", 1.0)),
                    base_strength=float(item.get("base_strength", 0.5)),
                    last_wave=int(item.get("last_wave", 0)),
                    attributes=item.get("attributes", {}),
                )
                node.collapsed = bool(item.get("collapsed", False))
            for item in raw.get("edges", []):
                if item.get("src") in self.nodes and item.get("dst") in self.nodes:
                    self.add_edge(
                        src=item["src"],
                        dst=item["dst"],
                        weight=float(item.get("weight", 1.0)),
                        relation=item.get("relation", "relates"),
                    )
            return self

    def start_background_wave(self) -> threading.Thread:
        if self._wave_thread and self._wave_thread.is_alive():
            return self._wave_thread

        self._wave_stop_event.clear()
        interval = float(self._wave_settings.get("interval_seconds", 30))
        log_each_cycle = bool(self._wave_settings.get("log_each_cycle", True))

        def _wave_loop() -> None:
            while not self._wave_stop_event.is_set():
                if self._wave_stop_event.wait(interval):
                    break
                strongest = self.elect_strongest()
                self.propagate()
                self.relax()
                pruned_count = self.prune()

                graph_nodes = {
                    node_id: self._to_graph_node(node)
                    for node_id, node in self.nodes.items()
                    if not node.collapsed
                }
                edge_tuples = [(edge.src, edge.dst, edge.weight) for edge in self.edges]
                tensions = detect_tension(graph_nodes)
                emergent_ids = spawn_emergence(graph_nodes, tensions, edge_tuples)
                self._apply_graph_node_updates(graph_nodes)
                self._sync_edges_from_tuples(edge_tuples)
                self._last_tension = max(tensions.values()) if tensions else 0.0

                self._wave_cycle_count += 1
                if log_each_cycle:
                    strongest_label = (
                        strongest.topics[0]
                        if strongest and strongest.topics
                        else (strongest.id if strongest else "none")
                    )
                    tension_score = max(tensions.values()) if tensions else 0.0
                    print(
                        f'🌊 Wave cycle #{self._wave_cycle_count} | Tension: {tension_score:.2f} '
                        f'| Nodes: {len(self.nodes)} | Strongest: "{strongest_label}" '
                        f"| Pruned: {pruned_count} | New emergence: {len(emergent_ids)}"
                    )
                if bool(self._wave_settings.get("auto_save", True)):
                    self.save()

        self._wave_thread = threading.Thread(
            target=_wave_loop,
            name="TS-OS-Wave-Engine",
            daemon=True,
        )
        self._wave_thread.start()
        return self._wave_thread

    def stop_background_wave(self) -> None:
        self._wave_stop_event.set()
        if self._wave_thread and self._wave_thread.is_alive():
            self._wave_thread.join(timeout=2.0)

    def get_wave_status(self) -> dict:
        """Return current wave health for observability."""
        return {
            "cycle_count": getattr(self, "_wave_cycle_count", 0),
            "thread_alive": self._wave_thread.is_alive() if self._wave_thread else False,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "tension": float(getattr(self, "_last_tension", 0.0)),
            "last_cycle": "running" if self._wave_thread else "stopped",
        }

    def get_metrics(self) -> dict:
        active = [n for n in self.nodes.values() if not n.collapsed]
        topic_counts: dict[str, int] = {}
        for node in active:
            for topic in node.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        avg_activation = sum(n.activation for n in active) / max(len(active), 1)
        avg_stability = sum(n.stability for n in active) / max(len(active), 1)
        return {
            "total_nodes": len(self.nodes),
            "active_nodes": len(active),
            "collapsed_nodes": len(self.nodes) - len(active),
            "edges": len(self.edges),
            "avg_activation": round(avg_activation, 4),
            "avg_stability": round(avg_stability, 4),
            "topics": topic_counts,
            "edge_density": round(len(self.edges) / max(len(active), 1), 4),
        }

    def _rebuild_adjacency(self) -> None:
        self._adjacency = {node_id: {} for node_id in self.nodes}
        for edge in self.edges:
            self._adjacency.setdefault(edge.src, {})[edge.dst] = edge.weight

    def _sync_edges_from_tuples(self, tuples: List[Tuple[str, str, float]]) -> None:
        self.edges = [
            Edge(src=src, dst=dst, weight=weight, relation="relates")
            for src, dst, weight in tuples
            if src in self.nodes and dst in self.nodes
        ]

    def _to_graph_node(self, node: Node):
        from .node import GraphNode

        return GraphNode(
            id=node.id,
            content=node.content,
            topics=node.topics[:],
            activation=node.activation,
            stability=node.stability,
            base_strength=node.base_strength,
            last_wave=node.last_wave,
            collapsed=node.collapsed,
            attributes=dict(node.attributes),
        )

    def _apply_graph_node_updates(self, graph_nodes: Dict[str, object]) -> None:
        from .node import GraphNode

        for node_id, graph_node in graph_nodes.items():
            if not isinstance(graph_node, GraphNode):
                continue
            existing = self.nodes.get(node_id)
            if existing is None:
                self.add_node(
                    node_id=node_id,
                    content=graph_node.content,
                    topics=graph_node.topics,
                    activation=graph_node.activation,
                    stability=graph_node.stability,
                    base_strength=graph_node.base_strength,
                    last_wave=graph_node.last_wave,
                    attributes=graph_node.attributes,
                )
                self.nodes[node_id].collapsed = graph_node.collapsed
                continue
            existing.content = graph_node.content
            existing.topics = graph_node.topics[:]
            existing.activation = graph_node.activation
            existing.stability = graph_node.stability
            existing.base_strength = graph_node.base_strength
            existing.last_wave = graph_node.last_wave
            existing.collapsed = graph_node.collapsed
            existing.attributes = dict(graph_node.attributes)
            self.add_node(
                node_id=existing.id,
                content=existing.content,
                topics=existing.topics,
                activation=existing.activation,
                stability=existing.stability,
                base_strength=existing.base_strength,
                last_wave=existing.last_wave,
                attributes=existing.attributes,
            )

    def __repr__(self) -> str:
        return (
            "UniversalLivingGraph("
            f"nodes={len(self.nodes)}, edges={len(self.edges)}, path='{self.graph_path.as_posix()}')"
        )
