from __future__ import annotations

import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from ..types import Edge, Node

logger = logging.getLogger("boggers.graph.snapshots")

_DEFAULT_SNAPSHOT_DIR = "snapshots"
_MAX_SNAPSHOTS = 50


class GraphSnapshotManager:
    def __init__(self, snapshot_dir: str = _DEFAULT_SNAPSHOT_DIR) -> None:
        self.snapshot_dir = Path(snapshot_dir)
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(
        self,
        nodes: Dict[str, Node],
        edges: List[Edge],
        label: str = "",
    ) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        slug = label.replace(" ", "-")[:40] if label else "auto"
        filename = f"snapshot-{ts}-{slug}.json"
        path = self.snapshot_dir / filename
        payload = {
            "timestamp": ts,
            "label": label,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": [asdict(n) for n in nodes.values()],
            "edges": [asdict(e) for e in edges],
        }
        path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        logger.info(
            "Snapshot saved: %s (%d nodes, %d edges)", path.name, len(nodes), len(edges)
        )
        self._enforce_limit()
        return path

    def list_snapshots(self) -> List[dict]:
        results = []
        for f in sorted(self.snapshot_dir.glob("snapshot-*.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append(
                    {
                        "file": f.name,
                        "timestamp": data.get("timestamp", ""),
                        "label": data.get("label", ""),
                        "node_count": data.get("node_count", 0),
                        "edge_count": data.get("edge_count", 0),
                    }
                )
            except Exception:
                continue
        return results

    def load_snapshot(self, filename: str) -> dict:
        path = self.snapshot_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {filename}")
        return json.loads(path.read_text(encoding="utf-8"))

    def restore_snapshot(
        self,
        filename: str,
    ) -> tuple[Dict[str, Node], List[Edge]]:
        data = self.load_snapshot(filename)
        nodes: Dict[str, Node] = {}
        edges: List[Edge] = []
        for item in data.get("nodes", []):
            nodes[item["id"]] = Node(
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
        for item in data.get("edges", []):
            if item.get("src") in nodes and item.get("dst") in nodes:
                edges.append(
                    Edge(
                        src=item["src"],
                        dst=item["dst"],
                        weight=float(item.get("weight", 1.0)),
                        relation=item.get("relation", "relates"),
                    )
                )
        logger.info(
            "Restored snapshot %s: %d nodes, %d edges", filename, len(nodes), len(edges)
        )
        return nodes, edges

    def delete_snapshot(self, filename: str) -> bool:
        path = self.snapshot_dir / filename
        if path.exists():
            path.unlink()
            return True
        return False

    def _enforce_limit(self) -> None:
        files = sorted(self.snapshot_dir.glob("snapshot-*.json"))
        while len(files) > _MAX_SNAPSHOTS:
            oldest = files.pop(0)
            oldest.unlink()
            logger.debug("Pruned old snapshot: %s", oldest.name)
