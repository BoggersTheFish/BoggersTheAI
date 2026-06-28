from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ..core.graph.pruning import PruningPolicy, apply_pruning_policy
from ..core.graph.rules_engine import spawn_emergence

if TYPE_CHECKING:
    from .runtime import BoggersRuntime

logger = logging.getLogger("boggers.runtime")


class AutonomousLoopManager:
    """Manages the autonomous OS-loop and background behaviours."""

    def __init__(self, runtime: BoggersRuntime) -> None:
        self.runtime = runtime
        self._os_loop_thread: threading.Thread | None = None
        self._os_stop_event = threading.Event()
        self._autonomous_mode_index = 0

    def start(self) -> None:
        if self._os_loop_thread and self._os_loop_thread.is_alive():
            return
        self._os_stop_event.clear()
        self._os_loop_thread = threading.Thread(
            target=self._os_loop,
            name="TS-OS-Main-Loop",
            daemon=True,
        )
        self._os_loop_thread.start()

    def stop(self) -> None:
        self._os_stop_event.set()
        if self._os_loop_thread and self._os_loop_thread.is_alive():
            self._os_loop_thread.join(timeout=2.0)

    def _os_loop(self) -> None:
        os_cfg = self.runtime.config.get("os_loop", {})
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
            
            # Check self-improvement triggers via runtime self_improvement service if configured
            si = getattr(self.runtime, "self_improvement", None)
            if si is not None:
                try:
                    si._auto_fine_tune_check(force=False)
                except Exception as exc:
                    logger.debug("Automatic fine tuning check failed: %s", exc)

            with self.runtime._state_lock:
                idle_seconds = time.time() - self.runtime._last_query_time
            if idle_seconds < idle_threshold_seconds:
                continue

            mode_name = autonomous_modes[
                self._autonomous_mode_index % len(autonomous_modes)
            ]
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
            self.runtime.config.get("autonomous", {}).get("exploration_strength", 0.3)
        )
        candidates = sorted(
            [node for node in self.runtime.graph.nodes.values() if not node.collapsed],
            key=lambda node: (node.activation * node.stability, node.base_strength),
        )
        for node in candidates[:2]:
            self.runtime.graph.update_activation(node.id, strength)
        self.runtime.graph.elect_strongest()
        self.runtime.graph.propagate()
        self.runtime.graph.relax()

        strongest = self.runtime.graph.strongest_node()
        strongest_topic = (
            strongest.topics[0]
            if strongest and strongest.topics
            else (strongest.id if strongest else "exploration")
        )
        created = 0
        explore_ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        for idx in range(2):
            node_id = f"auto:explore:{explore_ts}:{idx}"
            if node_id in self.runtime.graph.nodes:
                continue
            self.runtime.graph.add_node(
                node_id=node_id,
                content=f"Autonomous exploration spawned around {strongest_topic}",
                topics=[str(strongest_topic), "autonomous", "exploration"],
                activation=0.2 + (0.05 * idx),
                stability=0.65,
                base_strength=0.55,
            )
            if strongest is not None:
                self.runtime.graph.add_edge(strongest.id, node_id, weight=0.3)
            created += 1
        wave_status = self.runtime.graph.get_wave_status()
        logger.info(
            "OS Loop: exploration | tension: %.2f | spawned: %d",
            float(wave_status.get("tension", 0.0)),
            created,
        )

    def _autonomous_consolidation(self) -> None:
        if not self._is_user_idle():
            return
        nightly_hour = int(self.runtime.config.get("os_loop", {}).get("nightly_hour_utc", 3))
        self.run_nightly_consolidation(force=False)
        if datetime.now(timezone.utc).hour == nightly_hour:
            return
        prune_threshold = float(
            self.runtime.config.get("autonomous", {}).get("consolidation_prune_threshold", 0.2)
        )
        collapsed_count = 0
        for node in self.runtime.graph.nodes.values():
            if node.collapsed:
                continue
            if node.stability < prune_threshold:
                node.collapsed = True
                node.activation = 0.0
                collapsed_count += 1

        topic_map: dict[str, list[str]] = {}
        for node in self.runtime.graph.nodes.values():
            if node.collapsed or not node.topics:
                continue
            topic_map.setdefault(node.topics[0].lower(), []).append(node.id)

        merged_count = 0
        for topic, ids in topic_map.items():
            if len(ids) < 2:
                continue
            keeper_id = ids[0]
            keeper = self.runtime.graph.get_node(keeper_id)
            if keeper is None:
                continue
            for other_id in ids[1:]:
                other = self.runtime.graph.get_node(other_id)
                if other is None or other.collapsed:
                    continue
                keeper.content = f"{keeper.content}\n\n{other.content}"
                keeper.activation = max(keeper.activation, other.activation)
                keeper.stability = max(keeper.stability, other.stability)
                other.collapsed = True
                other.activation = 0.0
                merged_count += 1
            keeper.attributes["merged_topic"] = topic

        policy = PruningPolicy(min_stability=prune_threshold)
        policy_pruned = apply_pruning_policy(
            self.runtime.graph.nodes, policy, current_wave=self.runtime.graph._wave_cycle_count
        )
        self.runtime.graph.prune(threshold=prune_threshold)
        self.runtime.graph.save()
        wave_status = self.runtime.graph.get_wave_status()
        logger.info(
            (
                "OS Loop: consolidation | tension: %.2f | pruned: %d | "
                "merged: %d | policy_pruned: %d"
            ),
            float(wave_status.get("tension", 0.0)),
            collapsed_count,
            merged_count,
            len(policy_pruned),
        )

    def run_nightly_consolidation(self, force: bool = False) -> None:
        if not force:
            nightly_hour = int(
                self.runtime.config.get("os_loop", {}).get("nightly_hour_utc", 3)
            )
            if datetime.now(timezone.utc).hour != nightly_hour:
                return
        prune_threshold = 0.15
        collapsed_count = 0
        for node in self.runtime.graph.nodes.values():
            if node.collapsed:
                continue
            if node.stability < prune_threshold:
                node.collapsed = True
                node.activation = 0.0
                collapsed_count += 1

        topic_map: dict[str, list[str]] = {}
        for node in self.runtime.graph.nodes.values():
            if node.collapsed:
                continue
            for topic in node.topics:
                topic_map.setdefault(topic.lower(), []).append(node.id)

        merged_count = 0
        for topic, ids in topic_map.items():
            if len(ids) < 2:
                continue
            keeper = self.runtime.graph.get_node(ids[0])
            if keeper is None:
                continue
            for other_id in ids[1:]:
                other = self.runtime.graph.get_node(other_id)
                if other is None or other.collapsed:
                    continue
                keeper.content = f"{keeper.content}\n\n{other.content}"
                keeper.activation = max(keeper.activation, other.activation)
                keeper.stability = max(keeper.stability, other.stability)
                other.collapsed = True
                other.activation = 0.0
                merged_count += 1
            keeper.attributes["nightly_merged_topic"] = topic

        nightly_policy = PruningPolicy(min_stability=prune_threshold, max_age_waves=300)
        apply_pruning_policy(
            self.runtime.graph.nodes, nightly_policy, current_wave=self.runtime.graph._wave_cycle_count
        )
        self.runtime.graph.prune(threshold=prune_threshold)

        graph_nodes = {
            node_id: self.runtime.graph._to_graph_node(node)  # noqa: SLF001
            for node_id, node in self.runtime.graph.nodes.items()
            if not node.collapsed
        }
        edge_tuples = [(edge.src, edge.dst, edge.weight) for edge in self.runtime.graph.edges]
        tensions = self.runtime.graph.detect_tensions()
        
        # Determine rules engine spawn limit dynamically from config/graph size
        wave_cfg = self.runtime.config.get("wave", {})
        config_max_spawn = int(wave_cfg.get("emergence_max_spawn", 5))
        max_spawn = max(2, min(config_max_spawn, len(graph_nodes) // 200))

        emergent_ids = spawn_emergence(
            graph_nodes,
            tensions,
            edge_tuples,
            evolve_fn=self.runtime.graph._evolve_fn,
            max_spawn=max_spawn
        )
        self.runtime.graph._apply_graph_node_updates(graph_nodes)  # noqa: SLF001
        self.runtime.graph._sync_edges_from_tuples(edge_tuples)  # noqa: SLF001
        self.runtime.graph.save()
        recon: dict[str, int] = {}
        if bool(self.runtime.config.get("os_loop", {}).get("reconciliation_wave", True)):
            from ..core.graph.source_stability import SourceStabilityTracker

            recon = SourceStabilityTracker(self.runtime.graph).reconcile_nightly()
        wave_status = self.runtime.graph.get_wave_status()
        logger.info(
            (
                "OS Loop: nightly_consolidation | tension: %.2f | pruned: %d | "
                "merged: %d | emergence: %d | reconciliation: %s"
            ),
            float(wave_status.get("tension", 0.0)),
            collapsed_count,
            merged_count,
            len(emergent_ids),
            recon,
        )

    def _autonomous_insight_generation(self) -> None:
        if not self._is_user_idle():
            return
        min_tension = float(
            self.runtime.config.get("autonomous", {}).get("insight_min_tension", 0.8)
        )
        tensions = self.runtime.graph.detect_tensions()
        if not tensions:
            wave_status = self.runtime.graph.get_wave_status()
            logger.info(
                "OS Loop: insight | tension: %.2f | skipped: no_tension",
                float(wave_status.get("tension", 0.0)),
            )
            return
        strongest_tension = max(tensions.values())
        if strongest_tension < min_tension:
            wave_status = self.runtime.graph.get_wave_status()
            logger.info(
                "OS Loop: insight | tension: %.2f | skipped: below_threshold",
                float(wave_status.get("tension", 0.0)),
            )
            return

        highest_tension_node_id = max(tensions, key=tensions.get)
        node = self.runtime.graph.get_node(highest_tension_node_id)
        topic = node.topics[0] if node and node.topics else highest_tension_node_id
        query = f"Autonomous insight synthesis for {topic}"
        response = self.runtime.query_processor.process_query(query)
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
        wave_status = self.runtime.graph.get_wave_status()
        logger.info(
            "OS Loop: insight | tension: %.2f | topic: %s",
            float(wave_status.get("tension", 0.0)),
            topic,
        )

    def _is_user_idle(self) -> bool:
        idle_threshold = float(
            self.runtime.config.get("os_loop", {}).get("idle_threshold_seconds", 120)
        )
        with self.runtime._state_lock:
            return (time.time() - self.runtime._last_query_time) >= idle_threshold
