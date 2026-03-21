from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..events import bus
from .rules_engine import detect_tension, spawn_emergence

if TYPE_CHECKING:
    from .universal_living_graph import UniversalLivingGraph

logger = logging.getLogger("boggers.wave_runner")


@dataclass
class WaveConfig:
    interval_seconds: float = 30.0
    log_each_cycle: bool = True
    auto_save: bool = True
    incremental_save_interval: int = 5


class WaveCycleRunner:
    """Owns the step order of a wave cycle; delegates data ops to the graph."""

    def __init__(self, graph: UniversalLivingGraph, config: WaveConfig) -> None:
        self._graph = graph
        self._config = config
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._cycle_count = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name="TS-OS-Wave-Engine",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def run_single_cycle(self) -> dict:
        graph = self._graph

        guardrail = graph._check_guardrails()
        if guardrail:
            logger.warning("Wave cycle skipped: %s", guardrail)
            return {"skipped": guardrail}

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

        if self._config.log_each_cycle:
            strongest_label = (
                strongest.topics[0]
                if strongest and strongest.topics
                else (strongest.id if strongest else "none")
            )
            logger.info(
                (
                    "Wave cycle #%d | Tension: %.2f | Nodes: %d | "
                    "Strongest: %s | Pruned: %d | Emergence: %d"
                ),
                self._cycle_count,
                tension_score,
                len(graph.nodes),
                strongest_label,
                pruned_count,
                len(emergent_ids),
            )

        bus.emit(
            "wave_cycle",
            cycle=self._cycle_count,
            tension=graph._last_tension,
            nodes=len(graph.nodes),
            pruned=pruned_count,
            emergent=len(emergent_ids),
        )

        if self._config.auto_save:
            si = self._config.incremental_save_interval
            if si > 0 and self._cycle_count % si == 0:
                graph.save_incremental()
            elif si <= 0:
                graph.save_incremental()

        return {
            "cycle": self._cycle_count,
            "tension": tension_score,
            "nodes": len(graph.nodes),
            "pruned": pruned_count,
            "emergent": len(emergent_ids),
        }

    def _loop(self) -> None:
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
