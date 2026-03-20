from __future__ import annotations

import atexit
import json
import logging
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
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
)
from ..core.local_llm import LocalLLM
from ..core.fine_tuner import UnslothFineTuner
from ..core.trace_processor import TraceProcessor
from ..core.graph.universal_living_graph import UniversalLivingGraph
from ..core.graph.rules_engine import spawn_emergence
from ..entities import ConsolidationEngine, InferenceRouter, InsightEngine, ThrottlePolicy
from ..multimodal import ImageInAdapter, VoiceInAdapter, VoiceOutAdapter
from ..tools import ToolExecutor, ToolRouter

logger = logging.getLogger("boggers.runtime")


@dataclass(slots=True)
class RuntimeConfig:
    insight_vault_path: str = "./vault"
    graph_path: str = "./graph.json"
    inference: dict[str, object] = field(
        default_factory=lambda: {
            "synthesis": {
                "use_graph_subgraph": True,
                "top_k_nodes": 5,
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
                "dataset_build": {
                    "min_confidence": 0.75,
                    "max_samples": 5000,
                    "output_dir": "dataset",
                    "split_ratio": 0.8,
                },
                "fine_tuning": {
                    "enabled": True,
                    "base_model": "unsloth/llama-3.2-1b-instruct",
                    "max_seq_length": 2048,
                    "learning_rate": 2e-4,
                    "epochs": 1,
                    "adapter_save_path": "models/fine_tuned_adapter",
                    "auto_hotswap": True,
                    "auto_schedule": True,
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
            "interval_seconds": 30,
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
            "multi_turn_enabled": True,
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
        }
    )
    throttle_seconds: int = 60
    max_hypotheses_per_cycle: int = 2

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)


class BoggersRuntime:
    def __init__(self, config: RuntimeConfig | None = None) -> None:
        self.config = config or RuntimeConfig()
        from ..core.config_loader import load_and_apply
        self.raw_config = load_and_apply(self.config)
        self.graph = UniversalLivingGraph(config=self.config)
        self.graph.load()
        if self.config.get("wave", {}).get("enabled", True):
            self.graph.start_background_wave()
        self._last_query_time = time.time()
        self._state_lock = threading.Lock()
        self._os_loop_thread: threading.Thread | None = None
        self._os_stop_event = threading.Event()
        self._autonomous_mode_index = 0
        self._tui_thread: threading.Thread | None = None
        self._tui_stop_event = threading.Event()
        self._last_conversation_node_id: str | None = None
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
                adapter_registry.register("vault", VaultAdapter())
            if adapter_flags.get("x_api", False):
                adapter_registry.register("x_api", XApiAdapter())
        else:
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
            inference_cfg.get("ollama", {})
            if isinstance(inference_cfg, dict)
            else {}
        )
        self.local_llm = None
        if isinstance(ollama_cfg, dict) and bool(ollama_cfg.get("enabled", False)):
            self.local_llm = LocalLLM(
                model=str(ollama_cfg.get("model", "llama3.2")),
                temperature=float(ollama_cfg.get("temperature", 0.3)),
                max_tokens=int(ollama_cfg.get("max_tokens", 512)),
            )
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
            config=RouterConfig(max_hypotheses_per_cycle=self.config.max_hypotheses_per_cycle),
        )
        self.trace_processor = TraceProcessor(config=self.config)
        self.fine_tuner = UnslothFineTuner(config=self.config)
        fine_cfg = (
            self.config.get("inference", {})
            .get("self_improvement", {})
            .get("fine_tuning", {})
        )
        adapter_save_path = str(fine_cfg.get("adapter_save_path", "models/fine_tuned_adapter"))
        Path(adapter_save_path).mkdir(parents=True, exist_ok=True)
        Path("models/backups").mkdir(parents=True, exist_ok=True)
        self.min_traces_for_tune = int(fine_cfg.get("min_new_traces", 50)) if isinstance(fine_cfg, dict) else 50
        state = self._get_self_improvement_state()
        self._last_fine_tune_time = float(state.get("last_fine_tune_time", 0.0))
        self._last_tuned_trace_count = int(state.get("last_tuned_trace_count", 0))

        self.voice_in = VoiceInAdapter()
        self.voice_out = VoiceOutAdapter()
        self.image_in = ImageInAdapter()
        if self.config.get("os_loop", {}).get("enabled", True):
            self._start_os_loop()
        if self.config.get("tui", {}).get("enabled", False):
            self._start_tui_thread()
        atexit.register(self.shutdown)

    def ask(self, query: str):
        with self._state_lock:
            self._last_query_time = time.time()
        effective_query = self._apply_history_context(query)
        response = self.query_router.process_text(effective_query)
        response.query = query
        self._save_conversation_turn(user_query=query, answer=response.answer)
        return response

    def ask_audio(self, audio: bytes):
        with self._state_lock:
            self._last_query_time = time.time()
        transcript = self.voice_in.transcribe(audio) or "audio_input"
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
        caption = self.image_in.caption(image)
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

    def build_training_dataset(self) -> dict:
        return self.trace_processor.build_dataset()

    def trigger_self_improvement(self) -> dict:
        return self._auto_fine_tune_check(force=True)

    def fine_tune_and_hotswap(self, epochs: int = 1) -> dict:
        stats = self.fine_tuner.fine_tune(epochs=epochs)
        if not bool(stats.get("success", False)):
            stats["hotswapped"] = False
            return stats

        fine_cfg = (
            self.config.get("inference", {})
            .get("self_improvement", {})
            .get("fine_tuning", {})
        )
        auto_hotswap = bool(fine_cfg.get("auto_hotswap", True)) if isinstance(fine_cfg, dict) else True
        validation_enabled = bool(fine_cfg.get("validation_enabled", True)) if isinstance(fine_cfg, dict) else True
        state = self._get_self_improvement_state()
        previous_best_loss = state.get("best_val_loss")
        new_val_loss = stats.get("val_loss")
        if validation_enabled and new_val_loss is not None and previous_best_loss is not None:
            if float(new_val_loss) >= float(previous_best_loss):
                stats["hotswapped"] = False
                stats["skipped"] = True
                stats["reason"] = "validation_not_improved"
                stats["previous_best_val_loss"] = float(previous_best_loss)
                return stats

        adapter_path = str(stats.get("adapter_path", ""))
        backup_path = None
        if (
            self.local_llm is not None
            and getattr(self.local_llm, "adapter_path", None)
            and Path(str(self.local_llm.adapter_path)).exists()
        ):
            backup_root = Path("models/backups")
            backup_root.mkdir(parents=True, exist_ok=True)
            backup_path = backup_root / f"adapter_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
            shutil.copytree(str(self.local_llm.adapter_path), str(backup_path), dirs_exist_ok=True)

        if auto_hotswap and adapter_path:
            try:
                if self.local_llm is None:
                    ollama_cfg = (
                        self.config.get("inference", {}).get("ollama", {})
                        if isinstance(self.config.get("inference", {}), dict)
                        else {}
                    )
                    self.local_llm = LocalLLM(
                        model=str(ollama_cfg.get("model", "llama3.2")),
                        temperature=float(ollama_cfg.get("temperature", 0.3)),
                        max_tokens=int(ollama_cfg.get("max_tokens", 512)),
                        adapter_path=adapter_path,
                        base_model=str(
                            fine_cfg.get("base_model", "unsloth/llama-3.2-1b-instruct")
                        ) if isinstance(fine_cfg, dict) else "unsloth/llama-3.2-1b-instruct",
                    )
                else:
                    self.local_llm.load_adapter(
                        adapter_path,
                        base_model=str(
                            fine_cfg.get("base_model", "unsloth/llama-3.2-1b-instruct")
                        ) if isinstance(fine_cfg, dict) else "unsloth/llama-3.2-1b-instruct",
                    )
                self.query_processor.local_llm = self.local_llm
                stats["hotswapped"] = True
            except Exception as exc:
                rolled_back = False
                if self.local_llm is not None:
                    rolled_back = self.local_llm.load_previous_adapter()
                if not rolled_back and backup_path and self.local_llm is not None:
                    self.local_llm.load_adapter(
                        str(backup_path),
                        base_model=str(
                            fine_cfg.get("base_model", "unsloth/llama-3.2-1b-instruct")
                        ) if isinstance(fine_cfg, dict) else "unsloth/llama-3.2-1b-instruct",
                    )
                    rolled_back = True
                stats["hotswapped"] = False
                stats["rollback_applied"] = rolled_back
                stats["error"] = str(exc)
                return stats
        else:
            stats["hotswapped"] = False

        current_trace_count = self._count_traces()
        self._last_fine_tune_time = time.time()
        self._last_tuned_trace_count = current_trace_count
        state_update = {
            "last_fine_tune_time": self._last_fine_tune_time,
            "last_tuned_trace_count": self._last_tuned_trace_count,
        }
        if validation_enabled and new_val_loss is not None:
            if previous_best_loss is None or float(new_val_loss) < float(previous_best_loss):
                state_update["best_val_loss"] = float(new_val_loss)
        self._update_self_improvement_state(state_update)
        stats["previous_best_val_loss"] = (
            float(previous_best_loss) if previous_best_loss is not None else None
        )
        stats["best_val_loss"] = self._get_self_improvement_state().get("best_val_loss")
        return stats

    def shutdown(self) -> None:
        self._stop_os_loop()
        self._stop_tui_thread()
        if datetime.now(timezone.utc).hour == int(
            self.config.get("os_loop", {}).get("nightly_hour_utc", 3)
        ):
            self.run_nightly_consolidation()
        self.graph.save()
        self.graph.stop_background_wave()

    def __del__(self) -> None:
        try:
            self.shutdown()
        except Exception:
            pass

    def _start_os_loop(self) -> None:
        if self._os_loop_thread and self._os_loop_thread.is_alive():
            return
        self._os_stop_event.clear()
        self._os_loop_thread = threading.Thread(
            target=self._os_loop,
            name="TS-OS-Main-Loop",
            daemon=True,
        )
        self._os_loop_thread.start()

    def _stop_os_loop(self) -> None:
        self._os_stop_event.set()
        if self._os_loop_thread and self._os_loop_thread.is_alive():
            self._os_loop_thread.join(timeout=2.0)

    def _os_loop(self) -> None:
        os_cfg = self.config.get("os_loop", {})
        interval_seconds = float(os_cfg.get("interval_seconds", 60))
        idle_threshold_seconds = float(os_cfg.get("idle_threshold_seconds", 120))
        autonomous_modes = list(
            os_cfg.get("autonomous_modes", ["exploration", "consolidation", "insight"])
        )
        if not autonomous_modes:
            autonomous_modes = ["exploration", "consolidation", "insight"]

        while not self._os_stop_event.is_set():
            if self._os_stop_event.wait(interval_seconds):
                break
            self._auto_fine_tune_check(force=False)
            with self._state_lock:
                idle_seconds = time.time() - self._last_query_time
            if idle_seconds < idle_threshold_seconds:
                continue

            mode_name = autonomous_modes[self._autonomous_mode_index % len(autonomous_modes)]
            self._autonomous_mode_index += 1
            if mode_name == "exploration":
                self._autonomous_exploration()
            elif mode_name == "consolidation":
                self._autonomous_consolidation()
            elif mode_name == "insight":
                self._autonomous_insight_generation()

    def _autonomous_exploration(self) -> None:
        if not self._is_user_idle():
            return
        strength = float(
            self.config.get("autonomous", {}).get("exploration_strength", 0.3)
        )
        candidates = sorted(
            [node for node in self.graph.nodes.values() if not node.collapsed],
            key=lambda node: (node.activation * node.stability, node.base_strength),
        )
        for node in candidates[:2]:
            self.graph.update_activation(node.id, strength)
        self.graph.elect_strongest()
        self.graph.propagate()
        self.graph.relax()

        strongest = self.graph.strongest_node()
        strongest_topic = (
            strongest.topics[0]
            if strongest and strongest.topics
            else (strongest.id if strongest else "exploration")
        )
        created = 0
        for idx in range(2):
            node_id = (
                f"auto:explore:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}:{idx}"
            )
            if node_id in self.graph.nodes:
                continue
            self.graph.add_node(
                node_id=node_id,
                content=f"Autonomous exploration spawned around {strongest_topic}",
                topics=[str(strongest_topic), "autonomous", "exploration"],
                activation=0.2 + (0.05 * idx),
                stability=0.65,
                base_strength=0.55,
            )
            if strongest is not None:
                self.graph.add_edge(strongest.id, node_id, weight=0.3)
            created += 1
        wave_status = self.graph.get_wave_status()
        logger.info(
            "OS Loop: exploration | tension: %.2f | spawned: %d",
            float(wave_status.get("tension", 0.0)),
            created,
        )

    def _autonomous_consolidation(self) -> None:
        if not self._is_user_idle():
            return
        nightly_hour = int(self.config.get("os_loop", {}).get("nightly_hour_utc", 3))
        if datetime.now(timezone.utc).hour == nightly_hour:
            self.run_nightly_consolidation()
            return
        prune_threshold = float(
            self.config.get("autonomous", {}).get("consolidation_prune_threshold", 0.2)
        )
        collapsed_count = 0
        for node in self.graph.nodes.values():
            if node.collapsed:
                continue
            if node.stability < prune_threshold:
                node.collapsed = True
                node.activation = 0.0
                collapsed_count += 1

        topic_map: dict[str, list[str]] = {}
        for node in self.graph.nodes.values():
            if node.collapsed or not node.topics:
                continue
            topic_map.setdefault(node.topics[0].lower(), []).append(node.id)

        merged_count = 0
        for topic, ids in topic_map.items():
            if len(ids) < 2:
                continue
            keeper_id = ids[0]
            keeper = self.graph.get_node(keeper_id)
            if keeper is None:
                continue
            for other_id in ids[1:]:
                other = self.graph.get_node(other_id)
                if other is None or other.collapsed:
                    continue
                keeper.content = f"{keeper.content}\n\n{other.content}"
                keeper.activation = max(keeper.activation, other.activation)
                keeper.stability = max(keeper.stability, other.stability)
                other.collapsed = True
                other.activation = 0.0
                merged_count += 1
            keeper.attributes["merged_topic"] = topic

        self.graph.prune(threshold=prune_threshold)
        self.graph.save()
        wave_status = self.graph.get_wave_status()
        logger.info(
            "OS Loop: consolidation | tension: %.2f | pruned: %d | merged: %d",
            float(wave_status.get("tension", 0.0)),
            collapsed_count,
            merged_count,
        )

    def run_nightly_consolidation(self) -> None:
        prune_threshold = 0.15
        collapsed_count = 0
        for node in self.graph.nodes.values():
            if node.collapsed:
                continue
            if node.stability < prune_threshold:
                node.collapsed = True
                node.activation = 0.0
                collapsed_count += 1

        topic_map: dict[str, list[str]] = {}
        for node in self.graph.nodes.values():
            if node.collapsed:
                continue
            for topic in node.topics:
                topic_map.setdefault(topic.lower(), []).append(node.id)

        merged_count = 0
        for topic, ids in topic_map.items():
            if len(ids) < 2:
                continue
            keeper = self.graph.get_node(ids[0])
            if keeper is None:
                continue
            for other_id in ids[1:]:
                other = self.graph.get_node(other_id)
                if other is None or other.collapsed:
                    continue
                keeper.content = f"{keeper.content}\n\n{other.content}"
                keeper.activation = max(keeper.activation, other.activation)
                keeper.stability = max(keeper.stability, other.stability)
                other.collapsed = True
                other.activation = 0.0
                merged_count += 1
            keeper.attributes["nightly_merged_topic"] = topic

        self.graph.prune(threshold=prune_threshold)

        graph_nodes = {
            node_id: self.graph._to_graph_node(node)  # noqa: SLF001
            for node_id, node in self.graph.nodes.items()
            if not node.collapsed
        }
        edge_tuples = [(edge.src, edge.dst, edge.weight) for edge in self.graph.edges]
        tensions = self.graph.detect_tensions()
        emergent_ids = spawn_emergence(graph_nodes, tensions, edge_tuples)
        self.graph._apply_graph_node_updates(graph_nodes)  # noqa: SLF001
        self.graph._sync_edges_from_tuples(edge_tuples)  # noqa: SLF001
        self.graph.save()
        wave_status = self.graph.get_wave_status()
        logger.info(
            "OS Loop: nightly_consolidation | tension: %.2f | pruned: %d | merged: %d | emergence: %d",
            float(wave_status.get("tension", 0.0)),
            collapsed_count,
            merged_count,
            len(emergent_ids),
        )

    def _autonomous_insight_generation(self) -> None:
        if not self._is_user_idle():
            return
        min_tension = float(
            self.config.get("autonomous", {}).get("insight_min_tension", 0.8)
        )
        tensions = self.graph.detect_tensions()
        if not tensions:
            wave_status = self.graph.get_wave_status()
            logger.info(
                "OS Loop: insight | tension: %.2f | skipped: no_tension",
                float(wave_status.get("tension", 0.0)),
            )
            return
        strongest_tension = max(tensions.values())
        if strongest_tension < min_tension:
            wave_status = self.graph.get_wave_status()
            logger.info(
                "OS Loop: insight | tension: %.2f | skipped: below_threshold",
                float(wave_status.get("tension", 0.0)),
            )
            return

        highest_tension_node_id = max(tensions, key=tensions.get)
        node = self.graph.get_node(highest_tension_node_id)
        topic = (
            node.topics[0] if node and node.topics else highest_tension_node_id
        )
        query = f"Autonomous insight synthesis for {topic}"
        response = self.query_processor.process_query(query)
        traces_dir = Path("traces")
        traces_dir.mkdir(parents=True, exist_ok=True)
        insight_trace = traces_dir / (
            f"autonomous_insight_{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')}.jsonl"
        )
        payload = {
            "query": query,
            "answer": response.answer,
            "topic": topic,
            "tension": float(strongest_tension),
        }
        insight_trace.write_text(json.dumps(payload) + "\n", encoding="utf-8")
        wave_status = self.graph.get_wave_status()
        logger.info(
            "OS Loop: insight | tension: %.2f | topic: %s",
            float(wave_status.get("tension", 0.0)),
            topic,
        )

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

    def _is_user_idle(self) -> bool:
        idle_threshold = float(
            self.config.get("os_loop", {}).get("idle_threshold_seconds", 120)
        )
        with self._state_lock:
            return (time.time() - self._last_query_time) >= idle_threshold

    def get_conversation_history(self, last_n: int = 8) -> list[dict]:
        return self.graph.get_conversation_history(last_n=last_n)

    def _auto_fine_tune_check(self, force: bool = False) -> dict:
        inference_cfg = self.config.get("inference", {})
        self_improvement_cfg = (
            inference_cfg.get("self_improvement", {})
            if isinstance(inference_cfg, dict)
            else {}
        )
        fine_cfg = (
            self_improvement_cfg.get("fine_tuning", {})
            if isinstance(self_improvement_cfg, dict)
            else {}
        )
        if not isinstance(fine_cfg, dict) or not bool(fine_cfg.get("enabled", False)):
            return {"triggered": False, "reason": "fine_tuning_disabled"}
        if not force and not bool(fine_cfg.get("auto_schedule", True)):
            return {"triggered": False, "reason": "auto_schedule_disabled"}

        current_trace_count = self._count_traces()
        new_traces = max(0, current_trace_count - int(self._last_tuned_trace_count))
        nightly_hour = int(self.config.get("os_loop", {}).get("nightly_hour_utc", 3))
        should_run_nightly = datetime.now(timezone.utc).hour == nightly_hour
        should_run_threshold = new_traces >= int(self.min_traces_for_tune)

        if not force and not (should_run_nightly or should_run_threshold):
            return {
                "triggered": False,
                "reason": "conditions_not_met",
                "new_traces": new_traces,
            }

        epochs = int(fine_cfg.get("epochs", 1))
        stats = self.fine_tune_and_hotswap(epochs=epochs)
        stats["triggered"] = True
        stats["new_traces"] = new_traces
        return stats

    def _count_traces(self) -> int:
        inference_cfg = self.config.get("inference", {})
        self_improvement_cfg = (
            inference_cfg.get("self_improvement", {})
            if isinstance(inference_cfg, dict)
            else {}
        )
        traces_dir = str(self_improvement_cfg.get("traces_dir", "traces")) if isinstance(self_improvement_cfg, dict) else "traces"
        traces_path = Path(traces_dir)
        if not traces_path.exists():
            return 0
        total = 0
        for file_path in traces_path.glob("*.jsonl"):
            try:
                total += len(file_path.read_text(encoding="utf-8").splitlines())
            except Exception:
                continue
        return total

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

    def _get_self_improvement_state(self) -> dict:
        node = self.graph.get_node("runtime:self_improvement")
        if node is None:
            return {}
        attrs = getattr(node, "attributes", {})
        return attrs if isinstance(attrs, dict) else {}

    def _update_self_improvement_state(self, updates: dict) -> None:
        node = self.graph.get_node("runtime:self_improvement")
        if node is None:
            self._ensure_self_improvement_node()
            node = self.graph.get_node("runtime:self_improvement")
        if node is None:
            return
        attributes = getattr(node, "attributes", {})
        if not isinstance(attributes, dict):
            attributes = {}
        attributes.update(updates)
        node.attributes = attributes
        self.graph.save()

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
            if self._last_conversation_node_id and self.graph.get_node(self._last_conversation_node_id):
                self.graph.add_edge(self._last_conversation_node_id, node.id, weight=0.3)
            self._last_conversation_node_id = node.id
        self.graph.save()
