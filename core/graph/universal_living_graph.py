from __future__ import annotations

import copy
import hashlib
import heapq
import json
import logging
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

from ..events import bus
from ..types import Edge, Node
from .migrate import migrate_graph_data
from .rules_engine import (
    RulesEngineCycleResult,
    run_rules_cycle,
)
from .wave_runner import WaveConfig, WaveCycleRunner

logger = logging.getLogger("boggers.graph")

_MAX_NODES_SAFETY = 10000
_MAX_CYCLES_PER_HOUR = 200
_HIGH_TENSION_PAUSE_THRESHOLD = 0.95


class UniversalLivingGraph:
    def __init__(self, config: object | None = None, auto_load: bool = True) -> None:
        self.config = config
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adjacency: Dict[str, Dict[str, float]] = {}
        self._topic_index: Dict[str, Set[str]] = {}
        self.graph_path = self._resolve_graph_path(config)
        self._wave_settings = self._resolve_wave_settings(config)
        self._wave_runner: WaveCycleRunner | None = None
        self._last_tension = 0.0
        self._lock = threading.RLock()
        self._sqlite_backend = None
        self._dirty_nodes: set[str] = set()
        self._cycles_this_hour: int = 0
        self._hour_marker: int = 0
        self._evolve_fn: Optional[Callable[[str, List[str], str], str]] = None
        self._embedder = None
        self._snapshot_manager = None
        self._strongest_cache: Node | None = None
        self._strongest_cache_valid = False

        backend = self._resolve_backend(config)
        if backend == "sqlite":
            from .sqlite_backend import SQLiteGraphBackend

            db_path = self._resolve_sqlite_path(config)
            self._sqlite_backend = SQLiteGraphBackend(db_path)

        if auto_load:
            self.load()

    def set_evolve_fn(self, fn: Callable[[str, List[str], str], str]) -> None:
        self._evolve_fn = fn

    def set_embedder(self, embedder: object) -> None:
        self._embedder = embedder

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
            "mode": "tension",
            "interval_seconds": 30,
            "tension_fire_threshold": 0.7,
            "idle_heartbeat_seconds": None,
            "enabled": True,
            "log_each_cycle": True,
            "auto_save": True,
            "spread_factor": 0.1,
            "relax_decay": 0.85,
            "tension_threshold": 0.2,
            "prune_threshold": 0.25,
            "max_nodes_per_cycle": 50,
            "damping": 0.95,
            "activation_cap": 1.0,
            "semantic_weight": 0.3,
            "incremental_save_interval": 5,
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

    def _resolve_backend(self, config: object | None) -> str:
        if config is None:
            return "sqlite"
        if isinstance(config, dict):
            return str(config.get("runtime", {}).get("graph_backend", "sqlite"))
        runtime = getattr(config, "runtime", None)
        if isinstance(runtime, dict):
            return str(runtime.get("graph_backend", "sqlite"))
        return "sqlite"

    def _resolve_sqlite_path(self, config: object | None) -> str:
        if config is None:
            return "graph.db"
        if isinstance(config, dict):
            return str(config.get("runtime", {}).get("sqlite_path", "graph.db"))
        runtime = getattr(config, "runtime", None)
        if isinstance(runtime, dict):
            return str(runtime.get("sqlite_path", "graph.db"))
        return "graph.db"

    def snapshot_read(self) -> tuple[Dict[str, Node], List[Edge]]:
        with self._lock:
            nodes_copy = {nid: copy.deepcopy(n) for nid, n in self.nodes.items()}
            edges_copy = [copy.deepcopy(e) for e in self.edges]
        return nodes_copy, edges_copy

    def save_incremental(self) -> int:
        with self._lock:
            if not self._dirty_nodes:
                return 0
            count = len(self._dirty_nodes)
            dirty = [self.nodes[nid] for nid in self._dirty_nodes if nid in self.nodes]
            self._dirty_nodes.clear()
            if self._sqlite_backend:
                self._sqlite_backend.save_nodes_batch(dirty)
                self._sqlite_backend.save_edges_batch(self.edges)
            else:
                self.save()
            return count

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
        embedding: list[float] | None = None,
    ) -> Node:
        with self._lock:
            normalized_topics = sorted(set(topics or []))
            old = self.nodes.get(node_id)

            node_embedding = embedding or []
            if (
                not node_embedding
                and self._embedder is not None
                and content
                and hasattr(self._embedder, "embed")
            ):
                try:
                    node_embedding = self._embedder.embed(content)
                except Exception:
                    pass

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
                embedding=node_embedding,
            )
            self.nodes[node_id] = node
            self._dirty_nodes.add(node_id)
            self._strongest_cache_valid = False
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
        topic = query_topic.strip().lower()
        candidates: List[Node] = []
        seen_ids: set[str] = set()

        if topic:
            for node in self.get_nodes_by_topic(topic):
                if node.id not in seen_ids and not node.collapsed:
                    candidates.append(node)
                    seen_ids.add(node.id)

        if len(candidates) < top_k:
            needed = top_k - len(candidates)
            pool = [
                node
                for node in self.nodes.values()
                if not node.collapsed and node.id not in seen_ids
            ]

            def _rank_key(n):
                return (
                    n.activation,
                    n.stability,
                    n.base_strength,
                    n.last_wave,
                )

            ranked_global = heapq.nlargest(needed, pool, key=_rank_key)
            for node in ranked_global:
                candidates.append(node)
                seen_ids.add(node.id)

        return [asdict(node) for node in candidates[:top_k]]

    def get_conversation_history(self, last_n: int = 8) -> list[dict]:
        conversation_nodes = [
            node
            for node in self.nodes.values()
            if not node.collapsed
            and "conversation" in [topic.lower() for topic in node.topics]
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
            cap = float(self._wave_settings.get("activation_cap", 1.0))
            node.activation = max(0.0, min(cap, node.activation + delta))
            self._dirty_nodes.add(node_id)
            self._strongest_cache_valid = False
            return node.activation

    def strongest_node(self) -> Node | None:
        if self._strongest_cache_valid and self._strongest_cache is not None:
            if not self._strongest_cache.collapsed:
                return self._strongest_cache
        active = [node for node in self.nodes.values() if not node.collapsed]
        if not active:
            self._strongest_cache = None
            self._strongest_cache_valid = True
            return None
        result = max(
            active, key=lambda n: (n.activation * n.base_strength, n.stability)
        )
        self._strongest_cache = result
        self._strongest_cache_valid = True
        return result

    def elect_strongest(self) -> Node | None:
        return self.strongest_node()

    def propagate(self) -> None:
        with self._lock:
            cap = float(self._wave_settings.get("activation_cap", 1.0))
            damping = float(self._wave_settings.get("damping", 0.95))
            semantic = float(self._wave_settings.get("semantic_weight", 0.3))
            updates: Dict[str, float] = {}
            for node in self.nodes.values():
                if node.collapsed:
                    continue
                for neighbor_id, weight in self._adjacency.get(node.id, {}).items():
                    if (
                        neighbor_id not in self.nodes
                        or self.nodes[neighbor_id].collapsed
                    ):
                        continue
                    topo = (
                        node.activation
                        * weight
                        * float(self._wave_settings.get("spread_factor", 0.1))
                        * damping
                    )
                    sem = 0.0
                    if (
                        semantic > 0
                        and node.embedding
                        and self.nodes[neighbor_id].embedding
                    ):
                        from ..embeddings import cosine_similarity

                        sim = cosine_similarity(
                            node.embedding, self.nodes[neighbor_id].embedding
                        )
                        sem = (
                            node.activation
                            * sim
                            * float(self._wave_settings.get("spread_factor", 0.1))
                            * damping
                            * semantic
                        )
                    updates[neighbor_id] = updates.get(neighbor_id, 0.0) + topo + sem
            for node_id, delta in updates.items():
                if node_id in self.nodes:
                    node = self.nodes[node_id]
                    node.activation = max(0.0, min(cap, node.activation + delta))
                    self._dirty_nodes.add(node_id)

    def relax(self) -> None:
        with self._lock:
            cap = float(self._wave_settings.get("activation_cap", 1.0))
            for node in self.nodes.values():
                if node.collapsed:
                    continue
                node.activation = node.base_strength + (
                    node.activation - node.base_strength
                ) * float(self._wave_settings.get("relax_decay", 0.85))
                node.activation = max(0.0, min(cap, node.activation))

    def prune(self, threshold: float | None = None) -> int:
        with self._lock:
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
            result = run_rules_cycle(
                graph_nodes,
                adjacency,
                edges,
                damping=float(self._wave_settings.get("damping", 0.95)),
                activation_cap=float(self._wave_settings.get("activation_cap", 1.0)),
                semantic_weight=float(self._wave_settings.get("semantic_weight", 0.3)),
                evolve_fn=self._evolve_fn,
            )
            self._apply_graph_node_updates(graph_nodes)
            self._adjacency = adjacency
            self._sync_edges_from_tuples(edges)
            return result

    def _check_guardrails(self) -> str | None:
        with self._lock:
            active_count = sum(1 for n in self.nodes.values() if not n.collapsed)
            if active_count > _MAX_NODES_SAFETY:
                return f"node_cap_exceeded ({active_count} > {_MAX_NODES_SAFETY})"

            current_hour = int(time.time() // 3600)
            if current_hour != self._hour_marker:
                self._hour_marker = current_hour
                self._cycles_this_hour = 0
            if self._cycles_this_hour >= _MAX_CYCLES_PER_HOUR:
                return f"cycles_per_hour_exceeded ({self._cycles_this_hour})"

            if self._last_tension >= _HIGH_TENSION_PAUSE_THRESHOLD:
                return f"high_tension_pause (tension={self._last_tension:.2f})"

            return None

    def save(self, path: str | Path | None = None) -> Path:
        with self._lock:
            if self._sqlite_backend and path is None:
                nodes_list = list(self.nodes.values())
                self._sqlite_backend.save_nodes_batch(nodes_list)
                self._sqlite_backend.save_edges_batch(self.edges)
                self._dirty_nodes.clear()
                return Path(self._sqlite_backend.db_path)
            target = Path(path) if path is not None else self.graph_path
            target.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "nodes": [asdict(node) for node in self.nodes.values()],
                "edges": [asdict(edge) for edge in self.edges],
            }
            target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return target

    def load(self, path: str | Path | None = None) -> "UniversalLivingGraph":
        # Note: add_node() re-acquires self._lock; safe because _lock is an RLock
        with self._lock:
            if self._sqlite_backend and path is None:
                return self._load_from_sqlite()
            target = Path(path) if path is not None else self.graph_path
            if not target.exists():
                return self
            raw = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(raw, dict) or "nodes" not in raw:
                logger.warning("Invalid graph.json structure; starting fresh")
                return self
            raw = migrate_graph_data(raw)
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
                    embedding=item.get("embedding", []),
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
            self._dirty_nodes.clear()
            return self

    def _load_from_sqlite(self) -> "UniversalLivingGraph":
        self.nodes.clear()
        self.edges.clear()
        self._adjacency.clear()
        self._topic_index.clear()
        loaded_nodes = self._sqlite_backend.load_all_nodes()
        for node in loaded_nodes.values():
            self.nodes[node.id] = node
            self._adjacency.setdefault(node.id, {})
            for topic in node.topics:
                self._topic_index.setdefault(topic, set()).add(node.id)
        loaded_edges = self._sqlite_backend.load_all_edges()
        for edge in loaded_edges:
            if edge.src in self.nodes and edge.dst in self.nodes:
                self.edges.append(edge)
                self._adjacency.setdefault(edge.src, {})[edge.dst] = edge.weight
        self._dirty_nodes.clear()
        logger.info(
            "Loaded %d nodes, %d edges from SQLite",
            len(self.nodes),
            len(self.edges),
        )
        return self

    def save_graph_snapshot(self, label: str = "") -> Path | None:
        from .snapshots import GraphSnapshotManager

        if self._snapshot_manager is None:
            self._snapshot_manager = GraphSnapshotManager()
        nodes_copy, edges_copy = self.snapshot_read()
        return self._snapshot_manager.save_snapshot(
            {nid: n for nid, n in nodes_copy.items()},
            edges_copy,
            label=label,
        )

    def restore_graph_snapshot(self, filename: str) -> None:
        from .snapshots import GraphSnapshotManager

        if self._snapshot_manager is None:
            self._snapshot_manager = GraphSnapshotManager()
        nodes, edges = self._snapshot_manager.restore_snapshot(filename)
        with self._lock:
            self.nodes = nodes
            self.edges = edges
            self._rebuild_adjacency()
            self._rebuild_topic_index()
            self._dirty_nodes = set(self.nodes.keys())

    def export_graphml(self, path: str | Path) -> Path:
        from .export import export_graphml

        nodes_copy, edges_copy = self.snapshot_read()
        return export_graphml(nodes_copy, edges_copy, path)

    def export_json_ld(self, path: str | Path) -> Path:
        from .export import export_json_ld

        nodes_copy, edges_copy = self.snapshot_read()
        return export_json_ld(nodes_copy, edges_copy, path)

    def emit_global_tension_signal(self) -> None:
        """Publish max tension for TensionTriggeredWave (not cron-only)."""
        tensions = self.detect_tensions()
        t = max(tensions.values()) if tensions else 0.0
        self._last_tension = max(float(self._last_tension), float(t))
        bus.emit("global_tension", tension=float(t))

    def ingest_waves_jsonl(
        self,
        path: str | Path | None = None,
        *,
        max_nodes: int = 500,
    ) -> dict[str, object]:
        """Fold ``waves.jsonl`` into graph nodes (skips next_grok_prompt)."""
        p = Path(path) if path else Path("traces/meta_critique/waves.jsonl")
        if not p.exists():
            return {"ingested": 0, "skipped": True, "reason": "file_missing"}

        ingested = 0
        seen_hashes: set[str] = set()
        with self._lock:
            if "runtime:meta_critique_anchor" not in self.nodes:
                self.add_node(
                    node_id="runtime:meta_critique_anchor",
                    content="Meta-critique wave anchor (waves.jsonl fold)",
                    topics=["runtime", "meta_critique"],
                    activation=0.05,
                    stability=0.95,
                    base_strength=0.75,
                    attributes={"kind": "anchor"},
                )
            for raw_line in p.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("kind") == "next_grok_prompt":
                    continue
                h = hashlib.sha256(line.encode("utf-8")).hexdigest()[:20]
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)
                nid = f"meta:{h}"
                if nid in self.nodes:
                    continue
                if ingested >= max_nodes:
                    break
                kind = str(obj.get("kind", "wave"))
                content = json.dumps(obj, ensure_ascii=False)[:4000]
                self.add_node(
                    node_id=nid,
                    content=content,
                    topics=["meta_critique", "waves_jsonl", kind],
                    activation=0.12,
                    stability=0.88,
                    base_strength=0.55,
                    attributes={
                        "source": "waves.jsonl",
                        "kind": kind,
                        "timestamp": str(obj.get("timestamp", "")),
                    },
                )
                try:
                    self.add_edge(
                        "runtime:meta_critique_anchor",
                        nid,
                        weight=0.35,
                        relation="meta_wave",
                    )
                except KeyError:
                    pass
                ingested += 1
            self.save_incremental()
        return {"ingested": ingested, "skipped": False}

    def folded_wave_nodes(self) -> list[dict[str, object]]:
        """Inspectable nodes originating from folded ``waves.jsonl`` (dashboard/TUI)."""
        with self._lock:
            out: list[dict[str, object]] = []
            for n in self.nodes.values():
                if n.collapsed:
                    continue
                if n.id.startswith("meta:") or "waves_jsonl" in n.topics:
                    out.append(
                        {
                            "id": n.id,
                            "kind": n.attributes.get("kind", ""),
                            "topics": n.topics[:],
                            "activation": n.activation,
                            "stability": n.stability,
                            "preview": (n.content or "")[:400],
                        }
                    )
            return out

    def start_background_wave(self) -> threading.Thread:
        if self._wave_runner is not None and self._wave_runner.is_alive:
            return self._wave_runner._thread

        idle_hb = self._wave_settings.get("idle_heartbeat_seconds")
        config = WaveConfig(
            mode=str(self._wave_settings.get("mode", "interval")),
            interval_seconds=float(self._wave_settings.get("interval_seconds", 30)),
            tension_fire_threshold=float(
                self._wave_settings.get("tension_fire_threshold", 0.7)
            ),
            idle_heartbeat_seconds=(
                float(idle_hb) if idle_hb is not None else None
            ),
            log_each_cycle=bool(self._wave_settings.get("log_each_cycle", True)),
            auto_save=bool(self._wave_settings.get("auto_save", True)),
            incremental_save_interval=int(
                self._wave_settings.get("incremental_save_interval", 5)
            ),
        )
        self._wave_runner = WaveCycleRunner(self, config)
        self._wave_runner.start()
        return self._wave_runner._thread

    def stop_background_wave(self) -> None:
        if self._wave_runner is not None:
            self._wave_runner.stop()

    def get_wave_status(self) -> dict:
        runner = self._wave_runner
        return {
            "cycle_count": runner.cycle_count if runner else 0,
            "thread_alive": runner.is_alive if runner else False,
            "nodes": len(self.nodes),
            "edges": len(self.edges),
            "tension": float(self._last_tension),
            "last_cycle": "running" if runner and runner.is_alive else "stopped",
            "cycles_this_hour": self._cycles_this_hour,
            "backend": "sqlite" if self._sqlite_backend else "json",
        }

    def get_metrics(self) -> dict:
        active = [n for n in self.nodes.values() if not n.collapsed]
        topic_counts: dict[str, int] = {}
        for node in active:
            for topic in node.topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
        avg_activation = sum(n.activation for n in active) / max(len(active), 1)
        avg_stability = sum(n.stability for n in active) / max(len(active), 1)
        embedded = sum(1 for n in active if n.embedding)
        return {
            "total_nodes": len(self.nodes),
            "active_nodes": len(active),
            "collapsed_nodes": len(self.nodes) - len(active),
            "edges": len(self.edges),
            "avg_activation": round(avg_activation, 4),
            "avg_stability": round(avg_stability, 4),
            "topics": topic_counts,
            "edge_density": round(len(self.edges) / max(len(active), 1), 4),
            "embedded_nodes": embedded,
        }

    def _rebuild_adjacency(self) -> None:
        self._adjacency = {node_id: {} for node_id in self.nodes}
        for edge in self.edges:
            self._adjacency.setdefault(edge.src, {})[edge.dst] = edge.weight

    def _rebuild_topic_index(self) -> None:
        self._topic_index.clear()
        for node in self.nodes.values():
            for topic in node.topics:
                self._topic_index.setdefault(topic, set()).add(node.id)

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
            embedding=node.embedding[:] if node.embedding else [],
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
                    embedding=graph_node.embedding,
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
            existing.embedding = graph_node.embedding[:] if graph_node.embedding else []
            self._dirty_nodes.add(node_id)
            self._strongest_cache_valid = False
            for topic in existing.topics:
                self._topic_index.setdefault(topic, set()).add(node_id)

    @property
    def _wave_cycle_count(self) -> int:
        runner = self._wave_runner
        return runner.cycle_count if runner else 0

    def __repr__(self) -> str:
        return (
            "UniversalLivingGraph("
            f"nodes={len(self.nodes)}, edges={len(self.edges)}, "
            f"backend={'sqlite' if self._sqlite_backend else 'json'}, "
            f"path='{self.graph_path.as_posix()}')"
        )
