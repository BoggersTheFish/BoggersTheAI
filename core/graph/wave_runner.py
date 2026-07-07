from __future__ import annotations

import logging
import threading
from contextlib import nullcontext
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from ..bogvm_bridge import execute_bogvm_assembly
from ..events import bus
from .rules_engine import detect_tension, spawn_emergence

if TYPE_CHECKING:
    from .universal_living_graph import UniversalLivingGraph

logger = logging.getLogger("boggers.wave_runner")

_LONG_IDLE_WAIT_S = 86400.0


@dataclass
class WaveConfig:
    """Wave engine config (``mode='tension'`` = EventBus-driven, not fixed cron)."""

    mode: str = "tension"  # "interval" | "tension"
    interval_seconds: float = 30.0
    tension_fire_threshold: float = 0.7
    idle_heartbeat_seconds: float | None = None
    log_each_cycle: bool = True
    auto_save: bool = True
    incremental_save_interval: int = 5
    bogvm_payloads_enabled: bool = True
    bogvm_payloads_per_cycle: int = 1


class WaveCycleRunner:
    """Owns the step order of a wave cycle; delegates data ops to the graph."""

    def __init__(self, graph: UniversalLivingGraph, config: WaveConfig) -> None:
        self._graph = graph
        self._config = config
        self._stop_event = threading.Event()
        self._wake_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cycle_count = 0
        self._tension_handler: Callable[..., None] | None = None
        self._reactors_registered = False

    def _on_tension_signal(self, **kwargs: Any) -> None:
        t = float(kwargs.get("tension", 0.0))
        if t >= self._config.tension_fire_threshold:
            self._wake_event.set()

    def _register_tension_reactors(self) -> None:
        if self._config.mode != "tension" or self._reactors_registered:
            return
        self._tension_handler = self._on_tension_signal
        bus.on("wave_cycle", self._tension_handler)
        bus.on("global_tension", self._tension_handler)
        self._reactors_registered = True
        logger.info(
            "TensionTriggeredWave: wave_cycle + global_tension (threshold=%.2f)",
            self._config.tension_fire_threshold,
        )

    def _unregister_tension_reactors(self) -> None:
        if not self._reactors_registered or self._tension_handler is None:
            return
        bus.off("wave_cycle", self._tension_handler)
        bus.off("global_tension", self._tension_handler)
        self._reactors_registered = False
        self._tension_handler = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._register_tension_reactors()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="TS-OS-Wave-Engine",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._wake_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._unregister_tension_reactors()

    def run_single_cycle(self) -> dict:
        graph = self._graph
        graph_lock = getattr(graph, "_lock", nullcontext())
        bogvm_jobs: list[dict[str, Any]] = []

        with graph_lock:
            guardrail = graph._check_guardrails()
            if guardrail:
                skipped = {"skipped": guardrail}
                logger.warning("Wave cycle skipped: %s", guardrail)
                return skipped

            strongest = graph.elect_strongest()
            graph.propagate()
            graph.relax()
            pruned_count = graph.prune()

            graph_nodes = {
                node_id: graph._to_graph_node(node)
                for node_id, node in graph.nodes.items()
                if not node.collapsed
            }
            edge_tuples = [(edge.src, edge.dst, edge.weight) for edge in graph.edges]
            tensions = detect_tension(graph_nodes)
            emergent_ids = spawn_emergence(
                graph_nodes,
                tensions,
                edge_tuples,
                evolve_fn=graph._evolve_fn,
            )
            graph._apply_graph_node_updates(graph_nodes)
            graph._sync_edges_from_tuples(edge_tuples)
            graph._last_tension = max(tensions.values()) if tensions else 0.0

            self._cycle_count += 1
            graph._cycles_this_hour += 1

            tension_score = max(tensions.values()) if tensions else 0.0
            strongest_label = (
                strongest.topics[0]
                if strongest and strongest.topics
                else (strongest.id if strongest else "none")
            )
            node_count = len(graph.nodes)
            cycle = self._cycle_count
            event_payload = {
                "cycle": cycle,
                "tension": graph._last_tension,
                "nodes": node_count,
                "pruned": pruned_count,
                "emergent": len(emergent_ids),
                "bogvm_payloads_executed": 0,
                "bogvm_payloads_failed": 0,
            }
            result = dict(event_payload)
            if self._config.bogvm_payloads_enabled:
                iter_payloads = getattr(graph, "iter_runnable_bogvm_payloads", None)
                if callable(iter_payloads):
                    payloads = iter_payloads(
                        limit=max(0, int(self._config.bogvm_payloads_per_cycle))
                    )
                    if isinstance(payloads, list):
                        bogvm_jobs = payloads

        observation_artifacts: list[tuple[str, dict[str, Any]]] = []
        for job in bogvm_jobs:
            source_node_id = str(job.get("source_node_id", ""))
            payload = job.get("payload", {})
            artifact: dict[str, Any]
            try:
                if not isinstance(payload, dict):
                    raise ValueError("BOGVM payload job is malformed")
                if job.get("validation_error"):
                    artifact = {
                        "artifact_type": "bogvm_execution",
                        "program_id": payload.get("program_id"),
                        "program_hash": payload.get("program_hash"),
                        "source_graph_node": source_node_id,
                        "execution_status": "unsupported",
                        "execution_completed": False,
                        "exit_code": 1,
                        "vm_receipt_hash": None,
                        "vm_receipt": None,
                        "error": str(job["validation_error"]),
                        "state_commit_authorized": False,
                    }
                else:
                    artifact = execute_bogvm_assembly(
                        str(payload.get("assembly", "")),
                        program_hash=str(payload.get("program_hash", "")) or None,
                        max_steps=int(payload.get("max_steps", 0)),
                    )
                artifact["program_id"] = payload.get("program_id")
                artifact["source_graph_node"] = source_node_id
                artifact["target_claim"] = payload.get("target_claim")
                artifact["verifier_obligation_id"] = payload.get(
                    "verifier_obligation_id"
                )
                artifact["created_by"] = payload.get("created_by")
                artifact["provenance"] = payload.get("provenance")
            except Exception as exc:
                artifact = {
                    "artifact_type": "bogvm_execution",
                    "program_id": (
                        payload.get("program_id") if isinstance(payload, dict) else None
                    ),
                    "program_hash": (
                        payload.get("program_hash")
                        if isinstance(payload, dict)
                        else None
                    ),
                    "source_graph_node": source_node_id,
                    "execution_status": "error",
                    "execution_completed": False,
                    "exit_code": 1,
                    "vm_receipt_hash": None,
                    "error": str(exc),
                    "state_commit_authorized": False,
                }
            observation_artifacts.append((source_node_id, artifact))

        if observation_artifacts:
            record_observation = getattr(graph, "record_bogvm_observation", None)
            with graph_lock:
                for source_node_id, artifact in observation_artifacts:
                    if callable(record_observation):
                        record_observation(
                            source_node_id=source_node_id,
                            artifact=artifact,
                        )
                    if artifact.get("execution_completed"):
                        result["bogvm_payloads_executed"] += 1
                    else:
                        result["bogvm_payloads_failed"] += 1
                event_payload["bogvm_payloads_executed"] = result[
                    "bogvm_payloads_executed"
                ]
                event_payload["bogvm_payloads_failed"] = result["bogvm_payloads_failed"]
                event_payload["nodes"] = len(getattr(graph, "nodes", {}))
                result["nodes"] = event_payload["nodes"]

        if self._config.log_each_cycle:
            logger.info(
                (
                    "Wave cycle #%d | Tension: %.2f | Nodes: %d | "
                    "Strongest: %s | Pruned: %d | Emergence: %d | "
                    "BOGVM: %d ok / %d failed"
                ),
                cycle,
                tension_score,
                result["nodes"],
                strongest_label,
                pruned_count,
                len(emergent_ids),
                result["bogvm_payloads_executed"],
                result["bogvm_payloads_failed"],
            )

        bus.emit("wave_cycle", **event_payload)

        if self._config.auto_save:
            si = self._config.incremental_save_interval
            if si > 0 and cycle % si == 0:
                graph.save_incremental()
            elif si <= 0:
                graph.save_incremental()

        return result

    def _loop(self) -> None:
        if self._config.mode == "tension":
            if not self._stop_event.is_set():
                self.run_single_cycle()
            while not self._stop_event.is_set():
                idle = self._config.idle_heartbeat_seconds
                if idle is None:
                    tw = self._wake_event.wait(timeout=_LONG_IDLE_WAIT_S)
                else:
                    tw = self._wake_event.wait(timeout=float(idle))
                if self._stop_event.is_set():
                    break
                if tw:
                    self._wake_event.clear()
                    self.run_single_cycle()
                elif idle is not None:
                    self.run_single_cycle()
            return

        while not self._stop_event.is_set():
            if self._stop_event.wait(self._config.interval_seconds):
                break
            self.run_single_cycle()

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    @property
    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
