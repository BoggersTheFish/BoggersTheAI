from __future__ import annotations

import atexit
import logging
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

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
)
from ..core.events import bus
from ..core.fine_tuner import UnslothFineTuner
from ..core.graph.universal_living_graph import UniversalLivingGraph
from ..core.health import health_checker
from ..core.local_llm import LocalLLM
from ..core.metrics import metrics
from ..core.plugins import adapter_plugins, tool_plugins
from ..core.temperament import apply_temperament, get_temperament
from ..core.trace_processor import TraceProcessor
from ..entities import (
    ConsolidationEngine,
    InferenceRouter,
    InsightEngine,
    MetaCritiqueNode,
    ThrottlePolicy,
)
from ..multimodal import ImageInAdapter, VoiceInAdapter, VoiceOutAdapter
from ..tools import ToolExecutor, ToolRouter
from .autonomous_loop import AutonomousLoopMixin
from .self_improvement import SelfImprovementMixin

logger = logging.getLogger("boggers.runtime")


@dataclass(slots=True)
class RuntimeConfig:
    insight_vault_path: str = "./vault"
    graph_path: str = "./graph.json"
    graph_backend: str | None = None
    sqlite_path: str | None = None
    snapshot_dir: str | None = None
    inference: dict[str, object] = field(
        default_factory=lambda: {
            "synthesis": {
                "use_graph_subgraph": True,
                "top_k_nodes": 5,
                "graph_native_primary": True,
                "llm_fallback": True,
                "source_stability_edges": True,
                "graph_only": {
                    "pure_graph": True,
                    "max_excerpt_chars": 420,
                    "max_bullets": 5,
                },
            },
            "ollama": {
                "enabled": True,
                "model": "llama3.2",
                "temperature": 0.3,
                "max_tokens": 512,
            },
            "self_improvement": {
                "trace_logging_enabled": True,
                "min_confidence_for_log": 0.7,
                "traces_dir": "traces",
                "meta_critique_self_ingest": False,
                "meta_critique_wave_bus": False,
                "meta_critique_traces_dir": "traces/meta_critique",
                "dataset_build": {
                    "min_confidence": 0.75,
                    "max_samples": 5000,
                    "output_dir": "dataset",
                    "split_ratio": 0.8,
                },
                "fine_tuning": {
                    "enabled": False,
                    "track": "gpu_qlora",
                    "base_model": "unsloth/llama-3.2-1b-instruct",
                    "max_seq_length": 2048,
                    "learning_rate": 2e-4,
                    "epochs": 1,
                    "adapter_save_path": "models/fine_tuned_adapter",
                    "auto_hotswap": True,
                    "auto_schedule": False,
                    "min_new_traces": 50,
                    "validation_enabled": True,
                    "max_memory_gb": 12,
                    "safety_dry_run": True,
                },
            },
        }
    )
    wave: dict[str, object] = field(
        default_factory=lambda: {
            "mode": "tension",
            "interval_seconds": 30,
            "tension_fire_threshold": 0.7,
            "idle_heartbeat_seconds": None,
            "enabled": True,
            "log_each_cycle": True,
        }
    )
    os_loop: dict[str, object] = field(
        default_factory=lambda: {
            "enabled": True,
            "interval_seconds": 60,
            "idle_threshold_seconds": 120,
            "autonomous_modes": ["exploration", "consolidation", "insight"],
            "nightly_hour_utc": 3,
            "consolidation_on_shutdown": True,
            "multi_turn_enabled": True,
            "reconciliation_wave": True,
        }
    )
    autonomous: dict[str, object] = field(
        default_factory=lambda: {
            "exploration_strength": 0.3,
            "consolidation_prune_threshold": 0.2,
            "insight_min_tension": 0.8,
        }
    )
    tui: dict[str, object] = field(
        default_factory=lambda: {
            "enabled": False,
            "theme": "matrix",
        }
    )
    runtime: dict[str, object] = field(
        default_factory=lambda: {
            "session_id": "auto",
            "fold_waves_jsonl_on_startup": False,
        }
    )
    throttle_seconds: int = 60
    max_hypotheses_per_cycle: int = 2

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)


class BoggersRuntime(AutonomousLoopMixin, SelfImprovementMixin):
    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self.config = config or RuntimeConfig()
        from ..core.config_loader import load_and_apply

        self.raw_config = load_and_apply(self.config)

        self._apply_temperament()

        self.graph = UniversalLivingGraph(config=self.config)
        self.graph.load()

        self._warn_self_improvement()

        self._setup_embedder()

        if self.config.get("wave", {}).get("enabled", True):
            self.graph.start_background_wave()
        self._last_query_time = time.time()
        self._wave_cycle_meta_handler: Callable[..., None] | None = None
        self._state_lock = threading.Lock()
        self._os_loop_thread: threading.Thread | None = None
        self._os_stop_event = threading.Event()
        self._autonomous_mode_index = 0
        self._tui_thread: threading.Thread | None = None
        self._tui_stop_event = threading.Event()
        self._last_conversation_node_id: str | None = None
        self._llm_lock = threading.Lock()
        self.mode_manager = ModeManager()
        self.session_id = self._resolve_session_id()
        self._ensure_session_node()
        self._ensure_self_improvement_node()

        adapter_registry = AdapterRegistry()
        adapter_flags = self.raw_config.get("adapters", {}).get("enabled", {})
        if isinstance(adapter_flags, dict):
            if adapter_flags.get("wikipedia", True):
                adapter_registry.register("wikipedia", WikipediaAdapter())
            if adapter_flags.get("rss", True):
                adapter_registry.register("rss", RSSAdapter())
            if adapter_flags.get("hacker_news", True):
                adapter_registry.register("hacker_news", HackerNewsAdapter())
            if adapter_flags.get("vault", True):
                adapter_registry.register("vault", VaultAdapter(self.raw_config))
            if adapter_flags.get("x_api", False):
                adapter_registry.register("x_api", XApiAdapter())
        else:
            adapter_registry.register("wikipedia", WikipediaAdapter())
            adapter_registry.register("rss", RSSAdapter())
            adapter_registry.register("hacker_news", HackerNewsAdapter())
            adapter_registry.register("vault", VaultAdapter(self.raw_config))
            adapter_registry.register("x_api", XApiAdapter())
        adapter_plugins.discover_entry_points("boggers.adapters")
        for name in adapter_plugins.names():
            plugin = adapter_plugins.get(name)
            if plugin is not None:
                adapter_registry.register(name, plugin)
        tool_plugins.discover_entry_points("boggers.tools")

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
        synthesis_cfg = {}
        inference_cfg = self.config.get("inference", {})
        if isinstance(inference_cfg, dict):
            synthesis_cfg = inference_cfg.get("synthesis", {})
            self_improvement_cfg = inference_cfg.get("self_improvement", {})
            if isinstance(self_improvement_cfg, dict):
                traces_dir = str(self_improvement_cfg.get("traces_dir", "traces"))
                Path(traces_dir).mkdir(parents=True, exist_ok=True)
                dataset_build_cfg = self_improvement_cfg.get("dataset_build", {})
                if isinstance(dataset_build_cfg, dict):
                    dataset_dir = str(dataset_build_cfg.get("output_dir", "dataset"))
                    Path(dataset_dir).mkdir(parents=True, exist_ok=True)
        ollama_cfg = (
            inference_cfg.get("ollama", {}) if isinstance(inference_cfg, dict) else {}
        )
        self.local_llm = None
        if isinstance(ollama_cfg, dict) and bool(ollama_cfg.get("enabled", False)):
            self.local_llm = LocalLLM(
                model=str(ollama_cfg.get("model", "llama3.2")),
                temperature=float(ollama_cfg.get("temperature", 0.3)),
                max_tokens=int(ollama_cfg.get("max_tokens", 512)),
                base_url=str(ollama_cfg.get("base_url", "http://localhost:11434")),
            )
        self._setup_evolve_fn()
        self.query_processor = QueryProcessor(
            graph=self.graph,
            adapters=adapters,
            synthesis_config=synthesis_cfg if isinstance(synthesis_cfg, dict) else {},
            inference_config=inference_cfg if isinstance(inference_cfg, dict) else {},
            local_llm=self.local_llm,
        )
        self.query_router = QueryRouter(
            graph=self.graph,
            query_processor=self.query_processor,
            mode_manager=self.mode_manager,
            config=RouterConfig(
                max_hypotheses_per_cycle=self.config.max_hypotheses_per_cycle
            ),
        )
        self.trace_processor = TraceProcessor(config=self.config)
        mc_dir = "traces/meta_critique"
        if isinstance(inference_cfg, dict):
            si_mc = inference_cfg.get("self_improvement", {})
            if isinstance(si_mc, dict):
                mc_dir = str(si_mc.get("meta_critique_traces_dir", mc_dir))
        self.meta_critique = MetaCritiqueNode(traces_dir=Path(mc_dir))
        self.fine_tuner = UnslothFineTuner(config=self.config, graph=self.graph)
        self._fine_cfg = self._resolve_fine_cfg()
        fine_cfg = self._fine_cfg
        adapter_save_path = str(
            fine_cfg.get("adapter_save_path", "models/fine_tuned_adapter")
        )
        Path(adapter_save_path).mkdir(parents=True, exist_ok=True)
        Path("models/backups").mkdir(parents=True, exist_ok=True)
        self._trace_count_cache: int = 0
        self._trace_count_cache_time: float = 0.0
        self.min_traces_for_tune = (
            int(fine_cfg.get("min_new_traces", 50))
            if isinstance(fine_cfg, dict)
            else 50
        )
        state = self._get_self_improvement_state()
        self._last_fine_tune_time = float(state.get("last_fine_tune_time", 0.0))
        self._last_tuned_trace_count = int(state.get("last_tuned_trace_count", 0))

        self._register_meta_critique_wave_bus()
        self._meta_critique_self_ingest_if_enabled()

        rt_cfg = self.config.get("runtime", {})
        _fold = (
            rt_cfg.get("fold_waves_jsonl_on_startup", False)
            if isinstance(rt_cfg, dict)
            else False
        )
        fold_waves = bool(_fold)
        if fold_waves:
            try:
                self.graph.ingest_waves_jsonl(Path(mc_dir) / "waves.jsonl")
            except Exception as exc:
                logger.warning("ingest_waves_jsonl: %s", exc)

        self.voice_in = VoiceInAdapter()
        self.voice_out = VoiceOutAdapter()
        self.image_in = ImageInAdapter()
        if self.config.get("os_loop", {}).get("enabled", True):
            self._start_os_loop()
        if self.config.get("tui", {}).get("enabled", False):
            self._start_tui_thread()
        atexit.register(self.shutdown)
        self._register_health_checks()

    def ask(self, query: str):
        with self._state_lock:
            self._last_query_time = time.time()
        bus.emit("query", query=query)
        metrics.increment("queries_total")
        with metrics.timer("ask_duration"):
            effective_query = self._apply_history_context(query)
            response = self.query_router.process_text(effective_query)
        response.query = query
        self._save_conversation_turn(user_query=query, answer=response.answer)
        bus.emit("query_complete", query=query, answer=response.answer)
        return response

    def ask_audio(self, audio: bytes):
        with self._state_lock:
            self._last_query_time = time.time()
        try:
            transcript = self.voice_in.transcribe(audio) or "audio_input"
        except Exception as exc:
            logger.warning("Voice transcription failed: %s", exc)
            transcript = "audio_input"
        effective_query = self._apply_history_context(transcript)
        transcript_response = self.query_router.process_text(effective_query)
        transcript_response.query = transcript
        self._save_conversation_turn(
            user_query=f"[audio] {transcript}",
            answer=transcript_response.answer,
        )
        return transcript_response

    def ask_image(self, image: bytes, query_hint: str = ""):
        with self._state_lock:
            self._last_query_time = time.time()
        try:
            caption = self.image_in.caption(image)
        except Exception as exc:
            logger.warning("Image captioning failed: %s", exc)
            caption = "[image_caption_failed]"
        if caption and not caption.startswith("["):
            caption_node_id = f"image_caption:{int(time.time() * 1000)}"
            self.graph.add_node(
                node_id=caption_node_id,
                content=caption,
                topics=["image", "caption", "multimodal"],
                activation=0.25,
                stability=0.6,
                base_strength=0.5,
                attributes={
                    "type": "image_caption",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        base_query = f"{query_hint}\nimage_context: {caption}".strip()
        effective_query = self._apply_history_context(base_query)
        response = self.query_router.process_text(effective_query)
        response.query = base_query
        self._save_conversation_turn(
            user_query=f"[image] {query_hint}".strip(),
            answer=response.answer,
        )
        return response

    def speak(self, text: str) -> bytes:
        return self.voice_out.synthesize(text)

    def get_status(self) -> dict:
        return self.graph.get_wave_status()

    def shutdown(self) -> None:
        if self._wave_cycle_meta_handler is not None:
            try:
                bus.off("wave_cycle", self._wave_cycle_meta_handler)
            except Exception:
                pass
            self._wave_cycle_meta_handler = None
        self._stop_os_loop()
        self._stop_tui_thread()
        os_cfg = self.config.get("os_loop", {})
        skip_consolidation = bool(os.environ.get("BOGGERS_SKIP_SHUTDOWN_CONSOLIDATION"))
        if (
            bool(os_cfg.get("consolidation_on_shutdown", True))
            and not skip_consolidation
            and not sys.is_finalizing()
        ):
            self.run_nightly_consolidation(force=True)
        self.graph.save()
        if bool(os_cfg.get("consolidation_on_shutdown", True)):
            if getattr(self.graph, "_snapshot_manager", None) is not None:
                self.graph.save_graph_snapshot(label="shutdown")
        self.graph.stop_background_wave()

    def __del__(self) -> None:
        try:
            self.shutdown()
        except Exception:
            pass

    def run_tui(self) -> None:
        if self.config.get("tui", {}).get("enabled", False):
            from ..mind.tui import run_tui as mind_run_tui

            mind_run_tui(
                self,
                stop_event=self._tui_stop_event,
                theme=str(self.config.get("tui", {}).get("theme", "matrix")),
            )

    def _start_tui_thread(self) -> None:
        if self._tui_thread and self._tui_thread.is_alive():
            return
        self._tui_stop_event.clear()
        self._tui_thread = threading.Thread(
            target=self.run_tui,
            name="TS-OS-TUI",
            daemon=True,
        )
        self._tui_thread.start()

    def _stop_tui_thread(self) -> None:
        self._tui_stop_event.set()
        if self._tui_thread and self._tui_thread.is_alive():
            self._tui_thread.join(timeout=2.0)

    def get_conversation_history(self, last_n: int = 8) -> list[dict]:
        return self.graph.get_conversation_history(last_n=last_n)

    def _ensure_self_improvement_node(self) -> None:
        node_id = "runtime:self_improvement"
        if self.graph.get_node(node_id) is None:
            self.graph.add_node(
                node_id=node_id,
                content="Self-improvement state",
                topics=["runtime", "self_improvement"],
                activation=0.0,
                stability=0.9,
                base_strength=0.8,
                attributes={
                    "best_val_loss": None,
                    "last_fine_tune_time": 0.0,
                    "last_tuned_trace_count": 0,
                },
            )
            self.graph.save()

    def _register_meta_critique_wave_bus(self) -> None:
        inf = self.config.get("inference", {})
        si = inf.get("self_improvement", {}) if isinstance(inf, dict) else {}
        if not isinstance(si, dict) or not si.get("meta_critique_wave_bus", False):
            return

        def _handler(**kwargs: Any) -> None:
            try:
                self.meta_critique.ingest_wave_cycle_event(dict(kwargs))
            except Exception as exc:
                logger.warning("meta_critique wave_cycle bus: %s", exc)

        self._wave_cycle_meta_handler = _handler
        bus.on("wave_cycle", _handler)

    def _meta_critique_self_ingest_if_enabled(self) -> None:
        inf = self.config.get("inference", {})
        si = inf.get("self_improvement", {}) if isinstance(inf, dict) else {}
        if not isinstance(si, dict) or not si.get("meta_critique_self_ingest", False):
            return
        try:
            wave_cfg = self.config.get("wave", {})
            mode = (
                wave_cfg.get("mode", "tension")
                if isinstance(wave_cfg, dict)
                else "tension"
            )
            syn = inf.get("synthesis", {}) if isinstance(inf, dict) else {}
            if isinstance(syn, dict):
                gnp = bool(syn.get("graph_native_primary", True))
            else:
                gnp = True
            self.meta_critique.ingest(
                prompt="TS-OS Meta-Critique: session bootstrap",
                traces=[
                    {
                        "session_id": self.session_id,
                        "wave_mode": str(mode),
                        "graph_native_primary": gnp,
                    }
                ],
                extra={"source": "BoggersRuntime", "event": "self_ingest"},
            )
        except Exception as exc:
            logger.warning("Meta critique self-ingest failed: %s", exc)

    def _resolve_session_id(self) -> str:
        runtime_cfg = self.config.get("runtime", {})
        if not isinstance(runtime_cfg, dict):
            return str(uuid.uuid4())
        raw = str(runtime_cfg.get("session_id", "auto")).strip()
        if raw and raw != "auto":
            return raw
        generated = str(uuid.uuid4())
        runtime_cfg["session_id"] = generated
        return generated

    def _ensure_session_node(self) -> None:
        session_node_id = f"session:{self.session_id}"
        if self.graph.get_node(session_node_id) is None:
            self.graph.add_node(
                node_id=session_node_id,
                content=f"Session {self.session_id}",
                topics=["conversation", "session"],
                activation=0.1,
                stability=0.8,
                base_strength=0.7,
                attributes={"session_id": self.session_id, "type": "session_meta"},
            )
            self.graph.save()

    def _apply_history_context(self, query: str) -> str:
        if not bool(self.config.get("os_loop", {}).get("multi_turn_enabled", True)):
            return query
        history_context = self.graph.get_conversation_history(last_n=8)
        if not history_context:
            return query
        history_lines = []
        for item in history_context:
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            history_lines.append(f"- {content[:280]}")
        if not history_lines:
            return query
        return (
            "Conversation history:\n"
            + "\n".join(history_lines)
            + f"\n\nCurrent query:\n{query}"
        )

    def _save_conversation_turn(self, user_query: str, answer: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        node_id = f"conversation:{self.session_id}:{int(time.time() * 1000)}"
        content = f"User: {user_query}\nAssistant: {answer}"
        node = self.graph.add_node(
            node_id=node_id,
            content=content,
            topics=["conversation"],
            activation=0.2,
            stability=0.75,
            base_strength=0.65,
            attributes={
                "timestamp": timestamp,
                "session_id": self.session_id,
                "type": "conversation_turn",
            },
        )
        session_node_id = f"session:{self.session_id}"
        if self.graph.get_node(session_node_id) is not None:
            self.graph.add_edge(session_node_id, node.id, weight=0.2)
        with self._state_lock:
            if self._last_conversation_node_id and self.graph.get_node(
                self._last_conversation_node_id
            ):
                self.graph.add_edge(
                    self._last_conversation_node_id, node.id, weight=0.3
                )
            self._last_conversation_node_id = node.id
        self.graph.save()

    def _apply_temperament(self) -> None:
        wave_cfg = self.config.get("wave", {})
        if not isinstance(wave_cfg, dict):
            return
        name = str(wave_cfg.get("temperament", "default"))
        if name and name != "default":
            temperament = get_temperament(name)
            updated = apply_temperament(wave_cfg, temperament)
            wave_cfg.update(updated)
            logger.info("Applied cognitive temperament: %s", name)

    def _setup_embedder(self) -> None:
        embed_cfg = self.raw_config.get("embeddings", {})
        if not isinstance(embed_cfg, dict) or not bool(embed_cfg.get("enabled", False)):
            return
        try:
            from ..core.embeddings import OllamaEmbedder

            model = str(embed_cfg.get("model", "nomic-embed-text"))
            embedder = OllamaEmbedder(model=model)
            if embedder.is_available():
                self.graph.set_embedder(embedder)
                logger.info("Embedder active: %s", model)
            else:
                logger.info("Embedder not available (model %s not pulled?)", model)
        except Exception as exc:
            logger.debug("Embedder setup failed: %s", exc)

    def _register_health_checks(self) -> None:
        def _graph_health() -> dict:
            m = self.graph.get_metrics()
            return {"nodes": m["active_nodes"], "edges": m["edges"]}

        def _wave_health() -> dict:
            s = self.graph.get_wave_status()
            return {
                "alive": s.get("thread_alive", False),
                "cycles": s.get("cycle_count", 0),
            }

        def _llm_health() -> dict:
            if self.local_llm is None:
                return {"available": False}
            try:
                ok = self.local_llm.health_check()
                return {"available": ok}
            except Exception:
                return {"available": False}

        health_checker.register("graph", _graph_health)
        health_checker.register("wave", _wave_health)
        health_checker.register("llm", _llm_health)

    def run_health_checks(self) -> dict:
        return health_checker.run_all()

    def _setup_evolve_fn(self) -> None:
        if self.local_llm is not None:
            self.graph.set_evolve_fn(self.local_llm.synthesize_evolved_content)
