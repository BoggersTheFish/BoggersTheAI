from __future__ import annotations

import logging
from collections import defaultdict
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

        topic_buckets: dict[str, list[Node]] = defaultdict(list)
        for node in candidates:
            for topic in node.topics:
                topic_buckets[topic].append(node)

        idx = {n.id: i for i, n in enumerate(candidates)}
        pair_order: list[tuple[int, int]] = []
        seen_pairs: set[tuple[str, str]] = set()
        for topic in sorted(topic_buckets.keys()):
            bucket = topic_buckets[topic]
            for bi in range(len(bucket)):
                for bj in range(bi + 1, len(bucket)):
                    left_n, right_n = bucket[bi], bucket[bj]
                    if left_n.id == right_n.id:
                        continue
                    pair_key = (
                        (left_n.id, right_n.id)
                        if left_n.id < right_n.id
                        else (right_n.id, left_n.id)
                    )
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    ia, ib = idx[left_n.id], idx[right_n.id]
                    if ia > ib:
                        ia, ib = ib, ia
                    pair_order.append((ia, ib))
        pair_order.sort()

        for ia, ib in pair_order:
            left = candidates[ia]
            right = candidates[ib]
            skip = (
                left.id in processed
                or right.id in processed
                or left.collapsed
                or right.collapsed
            )
            if skip:
                continue
            if self._jaccard(left.content, right.content) <= self.similarity_threshold:
                continue

            survivor, absorbed = self._pick_survivor(left, right)
            self._absorb(graph, survivor, absorbed)
            processed.add(absorbed.id)
            result.merged_count += 1
            result.merged_pairs.append((survivor.id, absorbed.id))

        return result

    def _jaccard(self, left: str, right: str) -> float:
        left_tokens = {token for token in left.lower().split() if token}
        right_tokens = {token for token in right.lower().split() if token}
        if not left_tokens or not right_tokens:
            return 0.0
        if len(left_tokens) > len(right_tokens):
            left_tokens, right_tokens = right_tokens, left_tokens
        intersection = 0
        for token in left_tokens:
            if token in right_tokens:
                intersection += 1
        if intersection == 0:
            return 0.0
        union = len(left_tokens) + len(right_tokens) - intersection
        if not union:
            return 0.0
        return intersection / union

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
