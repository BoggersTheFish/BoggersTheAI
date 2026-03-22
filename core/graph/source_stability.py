from __future__ import annotations

import logging
from dataclasses import dataclass

from .universal_living_graph import UniversalLivingGraph

logger = logging.getLogger("boggers.source_stability")

DEFAULT_EDGE_WEIGHT = 0.85
NIGHTLY_DECAY = 0.995


@dataclass(slots=True)
class SourceStabilityTracker:
    """Weighted source→content edges; nightly reconciliation decays stale weights."""

    graph: UniversalLivingGraph

    def ensure_source_node(self, adapter_name: str) -> str:
        node_id = f"source:adapter:{adapter_name}"
        existing = self.graph.get_node(node_id)
        if existing is not None:
            return node_id
        self.graph.add_node(
            node_id=node_id,
            content=f"External knowledge source: {adapter_name}",
            topics=["source", "adapter", adapter_name],
            activation=0.05,
            stability=0.95,
            base_strength=0.9,
            attributes={"kind": "source_root", "adapter": adapter_name},
        )
        return node_id

    def link_ingestion(self, adapter_name: str, content_node_id: str) -> None:
        src = self.ensure_source_node(adapter_name)
        if self.graph.get_node(content_node_id) is None:
            return
        if not self._has_source_edge(src, content_node_id):
            try:
                self.graph.add_edge(
                    src,
                    content_node_id,
                    weight=DEFAULT_EDGE_WEIGHT,
                    relation="source_stability",
                )
            except KeyError:
                pass

    def reconcile_nightly(self) -> dict[str, int]:
        """Decay ``source_stability`` edges (merge placeholder)."""
        adjusted = 0
        with self.graph._lock:  # noqa: SLF001
            for edge in list(self.graph.edges):
                if edge.relation != "source_stability":
                    continue
                edge.weight = max(0.05, float(edge.weight) * NIGHTLY_DECAY)
                adjusted += 1
        if adjusted:
            logger.info(
                "Reconciliation wave: decayed %d source_stability edges",
                adjusted,
            )
        self.graph.save_incremental()
        return {"edges_decayed": adjusted}

    def _has_source_edge(self, src: str, dst: str) -> bool:
        for e in self.graph.edges:
            if e.src == src and e.dst == dst and e.relation == "source_stability":
                return True
        return False
