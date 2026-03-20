from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..adapters import (
    AdapterRegistry,
    HackerNewsAdapter,
    RSSAdapter,
    VaultAdapter,
    WikipediaAdapter,
    XApiAdapter,
)
from ..core import (
    ModeManager,
    QueryAdapters,
    QueryProcessor,
    QueryRouter,
    RegistryIngestAdapter,
    RouterConfig,
    UniversalLivingGraph,
)
from ..entities import ConsolidationEngine, InferenceRouter, InsightEngine, ThrottlePolicy
from ..multimodal import ImageInAdapter, VoiceInAdapter, VoiceOutAdapter
from ..tools import ToolExecutor, ToolRouter


@dataclass(slots=True)
class RuntimeConfig:
    insight_vault_path: str = "./vault"
    throttle_seconds: int = 60
    max_hypotheses_per_cycle: int = 2


class BoggersRuntime:
    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self.config = config or RuntimeConfig()
        self.graph = UniversalLivingGraph()
        self.mode_manager = ModeManager()

        adapter_registry = AdapterRegistry()
        adapter_registry.register("wikipedia", WikipediaAdapter())
        adapter_registry.register("rss", RSSAdapter())
        adapter_registry.register("hacker_news", HackerNewsAdapter())
        adapter_registry.register("vault", VaultAdapter())
        adapter_registry.register("x_api", XApiAdapter())
        ingest_adapter = RegistryIngestAdapter(adapter_registry)

        inference_router = InferenceRouter(
            throttle=ThrottlePolicy(min_interval_seconds=self.config.throttle_seconds)
        )
        tool_executor = ToolExecutor.with_defaults()
        tool_router = ToolRouter()

        insight_path = str(Path(self.config.insight_vault_path))
        adapters = QueryAdapters(
            inference=inference_router,
            ingest=ingest_adapter,
            tool=tool_executor,
            tool_router=tool_router,
            consolidation=ConsolidationEngine(),
            insight=InsightEngine(),
            insight_vault_path=insight_path,
        )
        self.query_processor = QueryProcessor(graph=self.graph, adapters=adapters)
        self.query_router = QueryRouter(
            graph=self.graph,
            query_processor=self.query_processor,
            mode_manager=self.mode_manager,
            config=RouterConfig(max_hypotheses_per_cycle=self.config.max_hypotheses_per_cycle),
        )

        self.voice_in = VoiceInAdapter()
        self.voice_out = VoiceOutAdapter()
        self.image_in = ImageInAdapter()

    def ask(self, query: str):
        return self.query_router.process_text(query)

    def ask_audio(self, audio: bytes):
        return self.query_router.process_audio(audio=audio, voice_in=self.voice_in)

    def ask_image(self, image: bytes, query_hint: str = ""):
        return self.query_router.process_image(
            image=image, image_in=self.image_in, query_hint=query_hint
        )

    def speak(self, text: str) -> bytes:
        return self.voice_out.synthesize(text)
