from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, List, Tuple

from ..core.graph.universal_living_graph import UniversalLivingGraph
from ..core.types import Node

logger = logging.getLogger("boggers.consolidation")


@dataclass(slots=True)
class ConsolidationResult:
    merged_count: int = 0
    merged_pairs: List[Tuple[str, str]] = field(default_factory=list)
    candidates_count: int = 0


class ConsolidationEngine:
    def __init__(self, similarity_threshold: float = 0.3) -> None:
        self.similarity_threshold = similarity_threshold

    def consolidate(
        self, graph: UniversalLivingGraph, nodes: Iterable[Node] | None = None
    ) -> ConsolidationResult:
        candidates = [n for n in (nodes or graph.nodes.values()) if not n.collapsed]
        result = ConsolidationResult(candidates_count=len(candidates))
        processed: set[str] = set()

        for left_index in range(len(candidates)):
            left = candidates[left_index]
            if left.id in processed or left.collapsed:
                continue
            for right_index in range(left_index + 1, len(candidates)):
                right = candidates[right_index]
                if right.id in processed or right.collapsed:
                    continue
                if not self._share_topic(left, right):
                    continue
                if (
                    self._jaccard(left.content, right.content)
                    <= self.similarity_threshold
                ):
                    continue

                survivor, absorbed = self._pick_survivor(left, right)
                self._absorb(graph, survivor, absorbed)
                processed.add(absorbed.id)
                result.merged_count += 1
                result.merged_pairs.append((survivor.id, absorbed.id))

        return result

    def _share_topic(self, left: Node, right: Node) -> bool:
        return bool(set(left.topics) & set(right.topics))

    def _jaccard(self, left: str, right: str) -> float:
        left_tokens = {token for token in left.lower().split() if token}
        right_tokens = {token for token in right.lower().split() if token}
        if not left_tokens or not right_tokens:
            return 0.0
        intersection = len(left_tokens & right_tokens)
        union = len(left_tokens | right_tokens)
        return intersection / union if union else 0.0

    def _pick_survivor(self, left: Node, right: Node) -> tuple[Node, Node]:
        if (left.activation, left.stability) >= (right.activation, right.stability):
            return left, right
        return right, left

    def _absorb(
        self, graph: UniversalLivingGraph, survivor: Node, absorbed: Node
    ) -> None:
        merged_topics = sorted(set(survivor.topics + absorbed.topics))
        merged_content = (
            f"{survivor.content}\n\n---\nMerged from {absorbed.id}:\n{absorbed.content}"
        )
        survivor.activation = max(survivor.activation, absorbed.activation)
        survivor.stability = max(survivor.stability, absorbed.stability)
        survivor.content = merged_content
        survivor.topics = merged_topics

        # Keep topic index consistent for survivor and remove absorbed from index.
        graph.add_node(
            node_id=survivor.id,
            content=survivor.content,
            topics=survivor.topics,
            activation=survivor.activation,
            stability=survivor.stability,
            last_wave=survivor.last_wave,
        )
        try:
            for topic in list(absorbed.topics):
                topic_set = graph._topic_index.get(topic)  # noqa: SLF001
                if topic_set:
                    topic_set.discard(absorbed.id)
                    if not topic_set:
                        graph._topic_index.pop(topic, None)  # noqa: SLF001
        except (AttributeError, KeyError) as exc:
            logger.debug("Topic index cleanup skipped: %s", exc)

        absorbed.topics = []
        absorbed.collapsed = True
        absorbed.activation = 0.0
        absorbed.stability = 0.0
        try:
            graph.add_edge(absorbed.id, survivor.id, weight=0.05)
        except KeyError as exc:
            logger.debug("Edge creation skipped (node missing): %s", exc)
