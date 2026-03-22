from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Protocol

from .graph.graph_only_synthesizer import GraphOnlySynthesizer
from .graph.universal_living_graph import UniversalLivingGraph
from .metrics import metrics
from .types import Node

logger = logging.getLogger("boggers.query")


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
    def get_activated_subgraph(
        self, query_topic: str, top_k: int = 5
    ) -> list[dict]: ...


class InferenceProtocol(Protocol):
    def synthesize(self, context: str, query: str) -> str: ...


class LocalLLMProtocol(Protocol):
    def summarize_and_hypothesize(self, context: str, query: str) -> dict: ...


class IngestProtocol(Protocol):
    def ingest(self, topic: str) -> List[Node]: ...


class ToolProtocol(Protocol):
    def execute(self, tool_name: str, args: dict) -> str: ...


class ToolRouterProtocol(Protocol):
    def route(
        self, query: str, sufficiency_score: float, topics: List[str]
    ) -> object | None: ...


class ConsolidationProtocol(Protocol):
    def consolidate(
        self, graph: object, nodes: Iterable[Node] | None = None
    ) -> object: ...


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
    context_nodes: List[str]
    activation_scores: List[float]
    consolidated_merges: int
    insight_path: str | None
    hypotheses: List[dict]
    confidence: float
    reasoning_trace: str
    answer: str


class QueryProcessor:
    def __init__(
        self,
        graph: GraphProtocol,
        adapters: QueryAdapters | None = None,
        min_sufficiency: float = 0.4,
        synthesis_config: dict | None = None,
        inference_config: dict | None = None,
        local_llm: LocalLLMProtocol | None = None,
    ) -> None:
        self.graph = graph
        self.adapters = adapters or QueryAdapters()
        self.min_sufficiency = min_sufficiency
        self.synthesis_config = synthesis_config or {}
        self.inference_config = inference_config or {}
        self.local_llm = local_llm
        self.self_improvement_config = self.inference_config.get("self_improvement", {})
        self._graph_synth: GraphOnlySynthesizer | None = None

    def _get_graph_synthesizer(self) -> GraphOnlySynthesizer:
        if self._graph_synth is None:
            go = self.synthesis_config.get("graph_only")
            self._graph_synth = GraphOnlySynthesizer.from_synthesis_options(
                go if isinstance(go, dict) else {}
            )
        return self._graph_synth

    @staticmethod
    def _graph_synth_sufficient(answer: str, context: List[Node]) -> bool:
        if not answer or not answer.strip() or not context:
            return False
        low = answer.lower()
        if "do not have enough retrieved context" in low:
            return False
        return len(answer.strip()) >= 12

    def process_query(self, query: str) -> QueryResponse:
        metrics.increment("queries_total")
        with metrics.timer("query_processing"):
            return self._process_query_inner(query)

    def _process_query_inner(self, query: str) -> QueryResponse:
        topics = self._extract_topics(query)
        context = self._retrieve_context(topics)
        sufficiency = self._score_sufficiency(context)
        used_research = False
        used_tool = False
        tool_name: str | None = None
        consolidated_merges = 0
        insight_path: str | None = None
        hypotheses: List[dict] = []
        confidence = 0.0
        reasoning_trace = ""

        if sufficiency < self.min_sufficiency and self.adapters.ingest:
            track_sources = bool(
                self.synthesis_config.get("source_stability_edges", True)
            )
            tracker = None
            if track_sources:
                from .graph.source_stability import SourceStabilityTracker

                tracker = SourceStabilityTracker(self.graph)
            for topic in topics:
                ingested_nodes = self.adapters.ingest.ingest(topic)
                for node in ingested_nodes:
                    self.graph.add_node(
                        node_id=node.id,
                        content=node.content,
                        topics=node.topics,
                        activation=node.activation,
                        stability=node.stability,
                        base_strength=node.base_strength,
                        last_wave=node.last_wave,
                        attributes=node.attributes,
                    )
                    if tracker is not None:
                        src = node.attributes.get("ingest_source", "unknown")
                        if isinstance(src, str):
                            tracker.link_ingestion(src, node.id)
            context = self._retrieve_context(topics)
            sufficiency = self._score_sufficiency(context)
            used_research = True

        tool_node = self._execute_tool_if_needed(query, topics, sufficiency)
        if tool_node is not None:
            context = [tool_node, *context]
            used_tool = True
            tool_name = tool_node.topics[0] if tool_node.topics else None

        answer, hypotheses, confidence, reasoning_trace = self._synthesize(
            query, context
        )
        min_confidence_for_log = float(
            self.self_improvement_config.get("min_confidence_for_log", 0.7)
        )
        trace_logging_enabled = bool(
            self.self_improvement_config.get("trace_logging_enabled", True)
        )
        if (
            trace_logging_enabled
            and confidence > min_confidence_for_log
            and reasoning_trace
        ):
            self._log_reasoning_trace(
                query=query,
                answer=answer,
                hypotheses=hypotheses,
                confidence=confidence,
                reasoning_trace=reasoning_trace,
            )
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
            extracted = self.adapters.insight.extract_hypotheses(answer, topics)
            for item in extracted:
                hypotheses.append(
                    {
                        "text": item,
                        "confidence": 0.35,
                        "supporting_nodes": [node.id for node in context[:3]],
                    }
                )
        emit_gt = getattr(self.graph, "emit_global_tension_signal", None)
        if callable(emit_gt):
            try:
                emit_gt()
            except Exception:
                logger.debug("emit_global_tension_signal failed", exc_info=True)
        return QueryResponse(
            query=query,
            topics=topics,
            context=context,
            sufficiency_score=sufficiency,
            used_research=used_research,
            used_tool=used_tool,
            tool_name=tool_name,
            context_nodes=[node.id for node in context],
            activation_scores=[node.activation for node in context],
            consolidated_merges=consolidated_merges,
            insight_path=insight_path,
            hypotheses=hypotheses,
            confidence=confidence,
            reasoning_trace=reasoning_trace,
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
        use_subgraph = bool(self.synthesis_config.get("use_graph_subgraph", True))
        top_k = int(self.synthesis_config.get("top_k_nodes", 5))
        if use_subgraph:
            query_topic = topics[0] if topics else "general"
            activated_context = self.graph.get_activated_subgraph(
                query_topic=query_topic, top_k=top_k
            )
            context_nodes = [self._node_from_dict(item) for item in activated_context]
            context_nodes = [node for node in context_nodes if node is not None]
            if context_nodes:
                logger.info(
                    "Using %d activated nodes for synthesis context", len(context_nodes)
                )
                return context_nodes

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

    def _node_from_dict(self, item: dict) -> Node | None:
        node_id = item.get("id")
        if not node_id:
            return None
        return Node(
            id=str(node_id),
            content=str(item.get("content", "")),
            topics=list(item.get("topics", [])),
            activation=float(item.get("activation", 0.0)),
            stability=float(item.get("stability", 1.0)),
            base_strength=float(item.get("base_strength", 0.5)),
            last_wave=int(item.get("last_wave", 0)),
            collapsed=bool(item.get("collapsed", False)),
            attributes=dict(item.get("attributes", {})),
        )

    def _score_sufficiency(self, nodes: List[Node]) -> float:
        if not nodes:
            return 0.0
        w_count = float(self.synthesis_config.get("sufficiency_weight_count", 0.4))
        w_activation = float(
            self.synthesis_config.get("sufficiency_weight_activation", 0.4)
        )
        w_recency = float(self.synthesis_config.get("sufficiency_weight_recency", 0.2))
        count_score = min(len(nodes) / 10.0, 1.0) * w_count
        activation_score = (
            min(sum(node.activation for node in nodes) / max(len(nodes), 1), 1.0)
            * w_activation
        )
        recency_score = (
            min(max(node.last_wave for node in nodes) / 10.0, 1.0) * w_recency
            if nodes
            else 0.0
        )
        return count_score + activation_score + recency_score

    def _synthesize(
        self, query: str, context: List[Node]
    ) -> tuple[str, List[dict], float, str]:
        context_text = self._render_context_text(context)
        graph_primary = bool(self.synthesis_config.get("graph_native_primary", True))
        llm_fallback = bool(self.synthesis_config.get("llm_fallback", True))

        if graph_primary:
            graph_answer = self._get_graph_synthesizer().synthesize(context_text, query)
            if self._graph_synth_sufficient(graph_answer, context):
                return (
                    graph_answer,
                    [],
                    0.62,
                    "graph_native_primary",
                )

        ollama_cfg = self.inference_config.get("ollama", {})
        if (
            isinstance(ollama_cfg, dict)
            and bool(ollama_cfg.get("enabled", False))
            and self.local_llm is not None
            and llm_fallback
        ):
            max_retries = int(self.synthesis_config.get("max_retries", 2))
            for attempt in range(max_retries):
                try:
                    llm_output = self.local_llm.summarize_and_hypothesize(
                        context_text, query
                    )
                    answer = str(llm_output.get("answer", "")).strip()
                    hypotheses = llm_output.get("hypotheses", [])
                    if not isinstance(hypotheses, list):
                        hypotheses = []
                    hypotheses = self._check_hypothesis_consistency(hypotheses, context)
                    confidence = float(llm_output.get("confidence", 0.0))
                    reasoning_trace = str(llm_output.get("reasoning_trace", "")).strip()
                    if answer:
                        return (
                            answer,
                            hypotheses,
                            max(0.0, min(confidence, 1.0)),
                            reasoning_trace,
                        )
                    break
                except Exception as exc:
                    logger.warning(
                        "LLM synthesis attempt %d failed: %s", attempt + 1, exc
                    )
                    if attempt == max_retries - 1:
                        break

        if self.adapters.inference:
            answer = self.adapters.inference.synthesize(context_text, query)
            return (answer, [], 0.0, "inference_router_fallback")
        if not context:
            return (
                "No strong graph context yet; additional research may be required.",
                [],
                0.2,
                "no_context_fallback",
            )
        preview = "; ".join(node.content for node in context[:3])
        return (
            f"Best graph-grounded response for '{query}': {preview}\n"
            "Source: retrieved graph context only.",
            [],
            0.4,
            "extractive_fallback",
        )

    def _check_hypothesis_consistency(
        self, hypotheses: List[dict], context_nodes: List[Node]
    ) -> List[dict]:
        node_ids = [node.id for node in context_nodes]
        topic_to_node_ids: dict[str, list[str]] = {}
        for node in context_nodes:
            for topic in node.topics:
                topic_to_node_ids.setdefault(topic.lower(), []).append(node.id)
        context_blob = " ".join(node.content.lower() for node in context_nodes)
        checked: List[dict] = []
        for raw in hypotheses[:3]:
            if not isinstance(raw, dict):
                continue
            text = str(raw.get("text", "")).strip()
            if not text:
                continue
            confidence = float(raw.get("confidence", 0.0))
            supporting_nodes = raw.get("supporting_nodes", [])
            if not isinstance(supporting_nodes, list):
                supporting_nodes = []
            lowered_text = text.lower()

            for topic, ids in topic_to_node_ids.items():
                if topic in lowered_text:
                    supporting_nodes.extend(ids[:2])
            if not supporting_nodes and node_ids:
                supporting_nodes = node_ids[:2]

            supporting_nodes = list(
                dict.fromkeys(str(node_id) for node_id in supporting_nodes)
            )
            contradiction = (
                " not " in lowered_text
                and lowered_text.replace(" not ", " ") in context_blob
            ) or (
                " never " in lowered_text
                and lowered_text.replace(" never ", " always ") in context_blob
            )
            if contradiction:
                confidence = max(0.0, confidence - 0.25)
            if confidence < 0.15:
                continue
            checked.append(
                {
                    "text": text,
                    "confidence": max(0.0, min(confidence, 1.0)),
                    "supporting_nodes": supporting_nodes,
                }
            )
        return checked

    def _log_reasoning_trace(
        self,
        query: str,
        answer: str,
        hypotheses: List[dict],
        confidence: float,
        reasoning_trace: str,
    ) -> None:
        traces_dir = str(self.self_improvement_config.get("traces_dir", "traces"))
        traces_path = Path(traces_dir)
        traces_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        trace_file = traces_path / f"reasoning_{timestamp}.jsonl"

        wave_status = {}
        get_wave_status = getattr(self.graph, "get_wave_status", None)
        if callable(get_wave_status):
            try:
                wave_status = get_wave_status() or {}
            except Exception:
                wave_status = {}

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "query": query,
            "answer": answer,
            "hypotheses": hypotheses,
            "confidence": max(0.0, min(float(confidence), 1.0)),
            "reasoning_trace": reasoning_trace,
            "graph_tension": float(wave_status.get("tension", 0.0)),
            "cycle_count": int(wave_status.get("cycle_count", 0)),
        }
        trace_file.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def _render_context_text(self, context: List[Node]) -> str:
        if not context:
            return ""
        lines: List[str] = []
        for node in context:
            lines.append(
                f"[node:{node.id}] topic={','.join(node.topics)} "
                f"activation={node.activation:.2f} stability={node.stability:.2f}"
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
    synthesis_config: dict | None = None,
    inference_config: dict | None = None,
    local_llm: LocalLLMProtocol | None = None,
) -> QueryResponse:
    processor = QueryProcessor(
        graph=graph,
        adapters=adapters,
        synthesis_config=synthesis_config,
        inference_config=inference_config,
        local_llm=local_llm,
    )
    return processor.process_query(query)
