from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, List, Protocol

from .graph import UniversalLivingGraph
from .types import Node


class GraphProtocol(Protocol):
    def add_node(
        self,
        node_id: str,
        content: str,
        topics: Iterable[str] | None = None,
        activation: float = 0.0,
        stability: float = 1.0,
        last_wave: int = 0,
    ) -> Node: ...

    def add_edge(self, src: str, dst: str, weight: float = 1.0) -> object: ...
    def get_nodes_by_topic(self, topic: str) -> List[Node]: ...


class InferenceProtocol(Protocol):
    def synthesize(self, context: str, query: str) -> str: ...


class IngestProtocol(Protocol):
    def ingest(self, topic: str) -> List[Node]: ...


class ToolProtocol(Protocol):
    def execute(self, tool_name: str, args: dict) -> str: ...


class ToolRouterProtocol(Protocol):
    def route(self, query: str, sufficiency_score: float, topics: List[str]) -> object | None: ...


class ConsolidationProtocol(Protocol):
    def consolidate(self, graph: object, nodes: Iterable[Node] | None = None) -> object: ...


class InsightProtocol(Protocol):
    def write_insight(
        self, content: str, topics: List[str], source_nodes: List[str], vault_path: str
    ) -> str: ...

    def extract_hypotheses(
        self, content: str, topics: Iterable[str], limit: int = 5
    ) -> List[str]: ...


@dataclass(slots=True)
class QueryAdapters:
    inference: InferenceProtocol | None = None
    ingest: IngestProtocol | None = None
    tool: ToolProtocol | None = None
    tool_router: ToolRouterProtocol | None = None
    consolidation: ConsolidationProtocol | None = None
    insight: InsightProtocol | None = None
    insight_vault_path: str | None = None


@dataclass(slots=True)
class QueryResponse:
    query: str
    topics: List[str]
    context: List[Node]
    sufficiency_score: float
    used_research: bool
    used_tool: bool
    tool_name: str | None
    consolidated_merges: int
    insight_path: str | None
    hypotheses: List[str]
    answer: str


class QueryProcessor:
    def __init__(
        self,
        graph: GraphProtocol,
        adapters: QueryAdapters | None = None,
        min_sufficiency: float = 0.4,
    ) -> None:
        self.graph = graph
        self.adapters = adapters or QueryAdapters()
        self.min_sufficiency = min_sufficiency

    def process_query(self, query: str) -> QueryResponse:
        topics = self._extract_topics(query)
        context = self._retrieve_context(topics)
        sufficiency = self._score_sufficiency(context)
        used_research = False
        used_tool = False
        tool_name: str | None = None
        consolidated_merges = 0
        insight_path: str | None = None
        hypotheses: List[str] = []

        if sufficiency < self.min_sufficiency and self.adapters.ingest:
            for topic in topics:
                ingested_nodes = self.adapters.ingest.ingest(topic)
                for node in ingested_nodes:
                    self.graph.add_node(
                        node_id=node.id,
                        content=node.content,
                        topics=node.topics,
                        activation=node.activation,
                        stability=node.stability,
                        last_wave=node.last_wave,
                    )
            context = self._retrieve_context(topics)
            sufficiency = self._score_sufficiency(context)
            used_research = True

        tool_node = self._execute_tool_if_needed(query, topics, sufficiency)
        if tool_node is not None:
            context = [tool_node, *context]
            used_tool = True
            tool_name = tool_node.topics[0] if tool_node.topics else None

        answer = self._synthesize(query, context)
        query_node = self._consolidate(query, topics, context, answer)
        if self.adapters.consolidation:
            consolidation_result = self.adapters.consolidation.consolidate(
                self.graph, nodes=[*context, query_node]
            )
            consolidated_merges = int(getattr(consolidation_result, "merged_count", 0))
        if self.adapters.insight and self.adapters.insight_vault_path:
            source_nodes = [node.id for node in context[:8]] + [query_node.id]
            insight_path = self.adapters.insight.write_insight(
                content=answer,
                topics=topics,
                source_nodes=source_nodes,
                vault_path=self.adapters.insight_vault_path,
            )
            hypotheses = self.adapters.insight.extract_hypotheses(answer, topics)
        return QueryResponse(
            query=query,
            topics=topics,
            context=context,
            sufficiency_score=sufficiency,
            used_research=used_research,
            used_tool=used_tool,
            tool_name=tool_name,
            consolidated_merges=consolidated_merges,
            insight_path=insight_path,
            hypotheses=hypotheses,
            answer=answer,
        )

    def _execute_tool_if_needed(
        self, query: str, topics: List[str], sufficiency: float
    ) -> Node | None:
        if not (self.adapters.tool and self.adapters.tool_router):
            return None

        decision = self.adapters.tool_router.route(query, sufficiency, topics)
        if decision is None:
            return None

        tool_name = getattr(decision, "tool_name", None)
        args = getattr(decision, "args", None)
        if not tool_name or not isinstance(args, dict):
            return None

        result = self.adapters.tool.execute(tool_name, args)
        if not result:
            return None

        digest = hashlib.sha1(
            f"tool:{tool_name}:{query}:{result[:120]}".encode("utf-8")
        ).hexdigest()[:12]
        node = Node(
            id=f"tool:{digest}",
            content=result,
            topics=[tool_name, *topics[:2]],
            activation=0.25,
            stability=0.7,
        )
        self.graph.add_node(
            node_id=node.id,
            content=node.content,
            topics=node.topics,
            activation=node.activation,
            stability=node.stability,
            last_wave=node.last_wave,
        )
        return node

    def _extract_topics(self, query: str) -> List[str]:
        tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
        stop = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "is",
            "are",
            "be",
            "this",
            "that",
            "it",
        }
        filtered = [token for token in tokens if token not in stop and len(token) > 2]
        unique: List[str] = []
        seen = set()
        for token in filtered:
            if token not in seen:
                seen.add(token)
                unique.append(token)
            if len(unique) >= 5:
                break
        return unique or ["general"]

    def _retrieve_context(self, topics: List[str]) -> List[Node]:
        seen: dict[str, Node] = {}
        for topic in topics:
            for node in self.graph.get_nodes_by_topic(topic):
                seen[node.id] = node
        ranked = sorted(
            seen.values(),
            key=lambda n: (n.activation, n.stability, n.last_wave),
            reverse=True,
        )
        return ranked[:20]

    def _score_sufficiency(self, nodes: List[Node]) -> float:
        if not nodes:
            return 0.0
        count_score = min(len(nodes) / 10.0, 1.0) * 0.4
        activation_score = min(
            sum(node.activation for node in nodes) / max(len(nodes), 1), 1.0
        ) * 0.4
        recency_score = (
            min(max(node.last_wave for node in nodes) / 10.0, 1.0) * 0.2
            if nodes
            else 0.0
        )
        return count_score + activation_score + recency_score

    def _synthesize(self, query: str, context: List[Node]) -> str:
        context_text = self._render_context_text(context)
        if self.adapters.inference:
            return self.adapters.inference.synthesize(context_text, query)
        if not context:
            return "No strong graph context yet; additional research may be required."
        preview = "; ".join(node.content for node in context[:3])
        return (
            f"Best graph-grounded response for '{query}': {preview}\n"
            "Source: retrieved graph context only."
        )

    def _render_context_text(self, context: List[Node]) -> str:
        if not context:
            return ""
        lines: List[str] = []
        for node in context:
            lines.append(
                f"[node:{node.id}] topic={','.join(node.topics)} activation={node.activation:.2f} "
                f"stability={node.stability:.2f}"
            )
            lines.append(node.content.strip())
        return "\n".join(lines)

    def _consolidate(
        self, query: str, topics: List[str], context: List[Node], answer: str
    ) -> Node:
        digest = hashlib.sha1(query.encode("utf-8")).hexdigest()[:12]
        node_id = f"query:{digest}"
        content = f"Q: {query}\nA: {answer}"
        activation = 0.3 if context else 0.1
        stability = 0.7 if context else 0.4
        new_node = self.graph.add_node(
            node_id=node_id,
            content=content,
            topics=topics,
            activation=activation,
            stability=stability,
        )
        for ctx in context[:5]:
            self.graph.add_edge(ctx.id, new_node.id, weight=0.2)
        return new_node


def process_query(
    query: str,
    graph: UniversalLivingGraph,
    adapters: QueryAdapters | None = None,
) -> QueryResponse:
    processor = QueryProcessor(graph=graph, adapters=adapters)
    return processor.process_query(query)
