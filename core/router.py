from __future__ import annotations

import logging
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Protocol

from .graph.universal_living_graph import UniversalLivingGraph
from .mode_manager import ModeManager
from .protocols import ImageInProtocol, VoiceInProtocol
from .query_processor import QueryProcessor, QueryResponse
from .graph.wave import run_wave

logger = logging.getLogger(__name__)


class AdapterRegistryProtocol(Protocol):
    def names(self) -> List[str]: ...

    def ingest(self, name: str, source: str): ...


@dataclass(slots=True)
class RouterConfig:
    default_adapter: str = "wikipedia"
    adapter_sources: Dict[str, List[str]] = field(default_factory=dict)
    max_hypotheses_per_cycle: int = 2
    user_request_timeout: float = 30.0


class RegistryIngestAdapter:
    """
    Adapter bridge for QueryProcessor.

    QueryProcessor asks for `ingest(topic)`. This bridge fans out to one
    or more configured adapters and returns a merged node list.
    """

    poll_interval = 0

    def __init__(
        self,
        registry: AdapterRegistryProtocol,
        adapter_sources: Dict[str, List[str]] | None = None,
        default_adapter: str = "wikipedia",
    ) -> None:
        self.registry = registry
        self.adapter_sources = adapter_sources or {}
        self.default_adapter = default_adapter

    def ingest(self, topic: str) -> List[object]:
        from ..core.types import Node
        sources = self.adapter_sources.get(topic, [self.default_adapter])
        nodes: List[object] = []
        for name in sources:
            try:
                res = self.registry.ingest(name, topic)
                if isinstance(res, list):
                    nodes.extend(res)
            except Exception as exc:
                logger.warning("Adapter %s failed to ingest %s: %s", name, topic, exc)
        return nodes


class QueryRouter:
    """
    Routes query request text to search, tools, or local LLM/consolidator.
    Pauses autonomous loops when user query runs.
    """

    def __init__(
        self,
        graph: UniversalLivingGraph,
        query_processor: QueryProcessor,
        mode_manager: ModeManager,
        config: RouterConfig | None = None,
    ) -> None:
        self.graph = graph
        self.query_processor = query_processor
        self.mode_manager = mode_manager
        self.config = config or RouterConfig()
        self._hypothesis_queue: Deque[str] = deque()
        self._queue_lock = threading.Lock()

    def process_text(self, query: str) -> QueryResponse:
        timeout = getattr(self.config, "user_request_timeout", 30.0)
        if not self.mode_manager.request_user_mode(timeout=timeout):
            logger.warning("request_user_mode timed out; autonomous cycle still active")
            return QueryResponse(
                query=query,
                topics=[],
                context=[],
                sufficiency_score=0.0,
                used_research=False,
                used_tool=False,
                tool_name=None,
                context_nodes=[],
                activation_scores=[],
                consolidated_merges=0,
                insight_path=None,
                hypotheses=[],
                confidence=0.0,
                reasoning_trace="",
                answer="System busy, please try again",
            )
        try:
            response = self.query_processor.process_query(query)
            self._enqueue_hypotheses(response.hypotheses)
            return response
        finally:
            self.mode_manager.release_to_auto()

    def process_audio(self, audio: bytes, voice_in: VoiceInProtocol) -> QueryResponse:
        transcript = voice_in.transcribe(audio)
        query = transcript or "transcription-empty"
        return self.process_text(query)

    def process_image(
        self, image: bytes, image_in: ImageInProtocol, query_hint: str = ""
    ) -> QueryResponse:
        caption = image_in.caption(image)
        query = f"{query_hint}\nimage_context: {caption}".strip()
        return self.process_text(query)

    def run_autonomous_cycle(self) -> List[QueryResponse]:
        if not self.mode_manager.begin_cycle():
            return []

        responses: List[QueryResponse] = []
        try:
            wave_result = run_wave(self.graph)
            strongest = wave_result.strongest_node
            with self._queue_lock:
                if strongest and strongest.topics:
                    self._hypothesis_queue.append(f"explore:{strongest.topics[0]}")
                if strongest and not strongest.topics:
                    self._hypothesis_queue.append(f"explore:{strongest.id}")

            limit = self.config.max_hypotheses_per_cycle
            processed = 0
            while processed < limit:
                with self._queue_lock:
                    if not self._hypothesis_queue:
                        break
                    hypothesis = self._hypothesis_queue.popleft()
                response = self.query_processor.process_query(hypothesis)
                responses.append(response)
                self._enqueue_hypotheses(response.hypotheses)
                processed += 1
        finally:
            self.mode_manager.end_cycle()
        return responses

    def _enqueue_hypotheses(self, hypotheses: list) -> None:
        with self._queue_lock:
            for item in hypotheses:
                if isinstance(item, dict):
                    text = str(item.get("text", "")).strip()
                elif isinstance(item, str):
                    text = item.strip()
                else:
                    continue
                if not text:
                    continue
                if text not in self._hypothesis_queue:
                    self._hypothesis_queue.append(text)
