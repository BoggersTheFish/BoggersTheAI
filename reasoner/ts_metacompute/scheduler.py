from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ts_metacompute.spectral.modes import read_spectral_tension
from ts_metacompute.spectral.signed_graph import SignedGraph


@dataclass(frozen=True)
class SchedulerTask:
    task_type: str
    graph: SignedGraph
    verifier_required: bool = True
    metadata: dict[str, Any] | None = None


class MetacomputeScheduler:
    """Minimal substrate scheduler for verifier-first metacompute.

    The v0.1 scheduler only has a spectral implementation. The interface is
    explicit so later phase/grid/field kernels can compete without inheriting
    proof authority.
    """

    def choose_substrate(self, task: SchedulerTask) -> str:
        if task.task_type in {
            "coherence_read",
            "contradiction_localization",
            "repair_ranking",
            "mode_read",
        }:
            return "spectral"
        if task.task_type in {"photonic_state_read", "photonic_interference"}:
            return "photonic_sim"
        if task.task_type in {"retrocausal_fuzz", "temporal_tension_bridge"}:
            return "temporal_bridge"
        if task.task_type in {"resonance_telemetry", "spectral_coupling"}:
            return "resonance_network"
        if task.task_type in {"unified_field_resolution", "lazy_universe_resolution"}:
            return "unified_field"
        return "symbolic_verifier"

    def run(self, task: SchedulerTask) -> dict[str, Any]:
        substrate = self.choose_substrate(task)
        if substrate == "spectral":
            read = read_spectral_tension(task.graph)
            payload = read.to_dict()
        elif substrate == "photonic_sim":
            from ts_reasoner.cognitive_physics_engine import PhotonicStateLedger

            ledger = PhotonicStateLedger()
            payload = ledger.encode_graph(task.graph)
            if task.task_type == "photonic_interference":
                payload["interference"] = ledger.interference_gate(task.graph)
        elif substrate == "temporal_bridge":
            from ts_reasoner.cognitive_physics_engine import (
                RetrocausalFuzzer,
                TemporalTensionBridge,
            )

            metadata = task.metadata or {}
            if task.task_type == "retrocausal_fuzz":
                payload = RetrocausalFuzzer().fuzz(task.graph)
            else:
                payload = TemporalTensionBridge().propagate(
                    task.graph,
                    assumption_priors=metadata.get("assumption_priors"),
                    contradiction_step=metadata.get("contradiction_step"),
                )
        elif substrate == "resonance_network":
            from ts_reasoner.cognitive_physics_engine import (
                ResonanceNode,
                SpectralCouplingTelepathy,
            )

            metadata = task.metadata or {}
            nodes = metadata.get("nodes") or [
                ResonanceNode(
                    "node_london",
                    "London",
                    {"logic": {"logic": 1.0}},
                    harmonic_frequency=1.0,
                ),
                ResonanceNode(
                    "node_tokyo",
                    "Tokyo",
                    {"logic": {"logic": 0.5}},
                    harmonic_frequency=1.0,
                ),
            ]
            solved_node_id = metadata.get("solved_node_id", nodes[0].node_id)
            payload = SpectralCouplingTelepathy().align(
                nodes, solved_node_id, task.graph
            )
        elif substrate == "unified_field":
            from ts_reasoner.cognitive_physics_engine import (
                LazyUniverseEngine,
                UnifiedFieldKernel,
            )

            metadata = task.metadata or {}
            question = metadata.get("question", task.graph.case_id or "resolve graph")
            if task.task_type == "lazy_universe_resolution":
                payload = LazyUniverseEngine().run(question, task.graph)
            else:
                payload = UnifiedFieldKernel().resolve(
                    question,
                    task.graph,
                    candidate_text=metadata.get("candidate_text"),
                )
        else:
            payload = {
                "status": "abstained",
                "reason": "no_non_symbolic_substrate_selected",
                "accepted_truth": False,
            }

        payload["selected_substrate"] = substrate
        payload["verifier_required_for_acceptance"] = task.verifier_required
        payload["accepted_without_verifier_support_count"] = 0
        return payload
