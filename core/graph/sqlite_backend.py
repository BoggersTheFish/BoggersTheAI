from __future__ import annotations

import json
import logging
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List

from ..types import Edge, Node

logger = logging.getLogger("boggers.graph.sqlite")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL DEFAULT '',
    topics TEXT NOT NULL DEFAULT '[]',
    activation REAL NOT NULL DEFAULT 0.0,
    stability REAL NOT NULL DEFAULT 1.0,
    base_strength REAL NOT NULL DEFAULT 0.5,
    last_wave INTEGER NOT NULL DEFAULT 0,
    collapsed INTEGER NOT NULL DEFAULT 0,
    attributes TEXT NOT NULL DEFAULT '{}',
    embedding TEXT NOT NULL DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS edges (
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    relation TEXT NOT NULL DEFAULT 'relates',
    PRIMARY KEY (src, dst)
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_nodes_topics ON nodes(topics);
CREATE INDEX IF NOT EXISTS idx_nodes_collapsed ON nodes(collapsed);
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
"""


class SQLiteGraphBackend:
    def __init__(self, db_path: str | Path = "graph.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_schema()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(
                str(self.db_path), check_same_thread=False
            )
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_schema(self) -> None:
        conn = self._get_conn()
        conn.executescript(_SCHEMA)
        conn.commit()
        self._ensure_embedding_column(conn)

    def _ensure_embedding_column(self, conn: sqlite3.Connection) -> None:
        try:
            cursor = conn.execute("PRAGMA table_info(nodes)")
            columns = {row[1] for row in cursor.fetchall()}
            if "embedding" not in columns:
                conn.execute(
                    "ALTER TABLE nodes ADD COLUMN embedding TEXT NOT NULL DEFAULT '[]'"
                )
                conn.commit()
        except Exception:
            pass

    def save_node(self, node: Node) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO nodes
               (id, content, topics, activation, stability, base_strength,
                last_wave, collapsed, attributes, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                node.id,
                node.content,
                json.dumps(node.topics),
                node.activation,
                node.stability,
                node.base_strength,
                node.last_wave,
                int(node.collapsed),
                json.dumps(node.attributes, default=str),
                json.dumps(node.embedding if node.embedding else []),
            ),
        )
        conn.commit()

    def save_nodes_batch(self, nodes: list[Node]) -> None:
        conn = self._get_conn()
        conn.executemany(
            """INSERT OR REPLACE INTO nodes
               (id, content, topics, activation, stability, base_strength,
                last_wave, collapsed, attributes, embedding)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    n.id,
                    n.content,
                    json.dumps(n.topics),
                    n.activation,
                    n.stability,
                    n.base_strength,
                    n.last_wave,
                    int(n.collapsed),
                    json.dumps(n.attributes, default=str),
                    json.dumps(n.embedding if n.embedding else []),
                )
                for n in nodes
            ],
        )
        conn.commit()

    def save_edge(self, edge: Edge) -> None:
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO edges (src, dst, weight, relation)
               VALUES (?, ?, ?, ?)""",
            (edge.src, edge.dst, edge.weight, edge.relation),
        )
        conn.commit()

    def save_edges_batch(self, edges: list[Edge]) -> None:
        conn = self._get_conn()
        conn.executemany(
            """INSERT OR REPLACE INTO edges (src, dst, weight, relation)
               VALUES (?, ?, ?, ?)""",
            [(e.src, e.dst, e.weight, e.relation) for e in edges],
        )
        conn.commit()

    def load_all_nodes(self) -> Dict[str, Node]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM nodes").fetchall()
        nodes: Dict[str, Node] = {}
        for row in rows:
            raw_embed = row["embedding"] if "embedding" in row.keys() else "[]"
            nodes[row["id"]] = Node(
                id=row["id"],
                content=row["content"],
                topics=json.loads(row["topics"]),
                activation=row["activation"],
                stability=row["stability"],
                base_strength=row["base_strength"],
                last_wave=row["last_wave"],
                collapsed=bool(row["collapsed"]),
                attributes=json.loads(row["attributes"]),
                embedding=json.loads(raw_embed) if raw_embed else [],
            )
        return nodes

    def load_all_edges(self) -> List[Edge]:
        conn = self._get_conn()
        rows = conn.execute("SELECT * FROM edges").fetchall()
        return [
            Edge(
                src=row["src"],
                dst=row["dst"],
                weight=row["weight"],
                relation=row["relation"],
            )
            for row in rows
        ]

    def delete_node(self, node_id: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM nodes WHERE id = ?", (node_id,))
        conn.execute("DELETE FROM edges WHERE src = ? OR dst = ?", (node_id, node_id))
        conn.commit()

    def delete_edges_below(self, threshold: float) -> int:
        conn = self._get_conn()
        cursor = conn.execute("DELETE FROM edges WHERE weight < ?", (threshold,))
        conn.commit()
        return cursor.rowcount

    def node_count(self) -> int:
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]

    def set_meta(self, key: str, value: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()

    def get_meta(self, key: str, default: str = "") -> str:
        conn = self._get_conn()
        row = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def close(self) -> None:
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None

    def import_from_json(self, json_path: str | Path) -> int:
        target = Path(json_path)
        if not target.exists():
            return 0
        raw = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return 0
        count = 0
        for item in raw.get("nodes", []):
            node = Node(
                id=item["id"],
                content=item.get("content", ""),
                topics=item.get("topics", []),
                activation=float(item.get("activation", 0.0)),
                stability=float(item.get("stability", 1.0)),
                base_strength=float(item.get("base_strength", 0.5)),
                last_wave=int(item.get("last_wave", 0)),
                collapsed=bool(item.get("collapsed", False)),
                attributes=item.get("attributes", {}),
                embedding=item.get("embedding", []),
            )
            self.save_node(node)
            count += 1
        for item in raw.get("edges", []):
            edge = Edge(
                src=item["src"],
                dst=item["dst"],
                weight=float(item.get("weight", 1.0)),
                relation=item.get("relation", "relates"),
            )
            self.save_edge(edge)
        logger.info("Imported %d nodes from %s", count, target)
        return count

    def export_to_json(self, json_path: str | Path) -> Path:
        from dataclasses import asdict

        target = Path(json_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        nodes = self.load_all_nodes()
        edges = self.load_all_edges()
        payload = {
            "nodes": [asdict(n) for n in nodes.values()],
            "edges": [asdict(e) for e in edges],
        }
        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return target
