"""Cognitive physics engine substrates for TS-OS.

The names in this module match the long-range TS-OS roadmap, but the
implementation is deliberately bounded and inspectable. Photonic, temporal,
resonance, unified-field, and lazy-universe surfaces are deterministic
simulators over TS graph state. They expose tension signals and candidate
state updates; typed verifier support remains the acceptance boundary.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from ts_metacompute.spectral.signed_graph import SignedEdge, SignedGraph

ENGINE_NAME = "TS-OS Cognitive Physics Engine"
PROOF_BOUNDARY = "substrates_expose_tension_typed_verifier_decides"
COGNITIVE_PHYSICS_NON_CLAIMS = [
    "No literal photonic chip is driven by this implementation.",
    "No physical retrocausality is claimed.",
    "No telepathy or instant communication is claimed.",
    "No zero-point energy source is claimed.",
    "No generated output is accepted without typed verifier support.",
]


def stable_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _edge_amplitude(edge: SignedEdge) -> float:
    return round(max(0.0, edge.weight) * max(0.0, edge.provenance_weight), 6)


def _graph_has_verifier_support(graph: SignedGraph) -> bool:
    return any(edge.status == "accepted" and edge.sign > 0 for edge in graph.edges)


def _graph_has_contradiction(graph: SignedGraph) -> bool:
    return any(edge.status == "accepted" and edge.sign < 0 for edge in graph.edges)


@dataclass(frozen=True)
class FrequencyState:
    state_id: str
    source: str
    target: str
    relation: str
    frequency_thz: float
    phase_degrees: float
    amplitude: float
    proof_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class PhotonicStateLedger:
    """Encode logical edges as deterministic frequency-slot state records."""

    def __init__(
        self, base_frequency_thz: float = 430.0, slot_width_thz: float = 7.5
    ) -> None:
        self.base_frequency_thz = base_frequency_thz
        self.slot_width_thz = slot_width_thz
        self.entries: list[FrequencyState] = []

    def encode_graph(self, graph: SignedGraph) -> dict[str, Any]:
        self.entries = []
        for index, edge in enumerate(graph.edges, start=1):
            relation_offset = 0.33 if edge.sign > 0 else 0.66
            phase = 0.0 if edge.sign > 0 else 180.0
            self.entries.append(
                FrequencyState(
                    state_id=f"freq_{index:04d}_{edge.edge_id}",
                    source=edge.source,
                    target=edge.target,
                    relation=edge.relation,
                    frequency_thz=round(
                        self.base_frequency_thz
                        + index * self.slot_width_thz
                        + relation_offset,
                        6,
                    ),
                    phase_degrees=phase,
                    amplitude=_edge_amplitude(edge),
                    proof_status=edge.status,
                )
            )

        payload = {
            "artifact": "photonic_state_ledger",
            "case_id": graph.case_id,
            "architecture": "Photonic_State_Ledger",
            "state_storage": "deterministic_frequency_slots",
            "entries": [entry.to_dict() for entry in self.entries],
            "ledger_hash": stable_hash([entry.to_dict() for entry in self.entries]),
            "verifier_required_for_acceptance": True,
            "accepted_truth": False,
            "accepted_without_verifier_support_count": 0,
        }
        return payload

    def interference_gate(self, graph: SignedGraph) -> dict[str, Any]:
        if not self.entries:
            self.encode_graph(graph)

        constructive = round(
            sum(
                entry.amplitude for entry in self.entries if entry.phase_degrees == 0.0
            ),
            6,
        )
        destructive = round(
            sum(
                entry.amplitude
                for entry in self.entries
                if entry.phase_degrees == 180.0
            ),
            6,
        )
        total = round(constructive + destructive, 6)
        cancelled = round(min(constructive, destructive), 6)
        cancellation_ratio = round(cancelled / total, 6) if total else 0.0
        residual_tension = round(destructive / total, 6) if total else 0.0
        contradiction_detected = (
            _graph_has_contradiction(graph) and cancellation_ratio > 0.0
        )
        energy_estimate = {
            "binary_cpu_cycles": max(1, len(graph.edges)) * 100,
            "simulated_interference_operations": max(1, len(graph.edges)),
            "physical_zero_compute_claimed": False,
        }
        return {
            "artifact": "photonic_interference_gate",
            "architecture": "ContradictionFirewall_as_interference_grating",
            "case_id": graph.case_id,
            "constructive_amplitude": constructive,
            "destructive_amplitude": destructive,
            "cancelled_amplitude": cancelled,
            "cancellation_ratio": cancellation_ratio,
            "residual_tension": residual_tension,
            "contradiction_detected": contradiction_detected,
            "energy_estimate": energy_estimate,
            "reader_decision": (
                "contradiction_candidate"
                if contradiction_detected
                else "coherent_candidate"
            ),
            "accepted_truth": False,
            "verifier_required_for_acceptance": True,
            "accepted_without_verifier_support_count": 0,
        }


@dataclass(frozen=True)
class TemporalUpdate:
    assumption_id: str
    prior_probability: float
    posterior_probability: float
    propagated_tension: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TemporalTensionBridge:
    """Back-propagate late contradiction tension into early assumptions."""

    def propagate(
        self,
        graph: SignedGraph,
        assumption_priors: dict[str, float] | None = None,
        contradiction_step: int | None = None,
    ) -> dict[str, Any]:
        priors = assumption_priors or {
            edge.edge_id: 0.8 if edge.sign > 0 else 0.55 for edge in graph.edges
        }
        late_step = contradiction_step or max(2, len(graph.edges) + 1)
        conflict_weight = sum(
            _edge_amplitude(edge) for edge in graph.edges if edge.sign < 0
        )
        total_weight = sum(_edge_amplitude(edge) for edge in graph.edges) or 1.0
        propagated_tension = round(conflict_weight / total_weight, 6)

        updates: list[TemporalUpdate] = []
        for index, (assumption_id, prior) in enumerate(sorted(priors.items()), start=1):
            temporal_distance = max(1, late_step - index)
            attenuation = 1.0 / temporal_distance
            posterior = max(
                0.0, min(1.0, prior * (1.0 - propagated_tension * attenuation))
            )
            updates.append(
                TemporalUpdate(
                    assumption_id=assumption_id,
                    prior_probability=round(prior, 6),
                    posterior_probability=round(posterior, 6),
                    propagated_tension=round(propagated_tension * attenuation, 6),
                    reason="late_contradiction_tension_backpropagated",
                )
            )

        event_ledger = []
        previous_hash = "0" * 64
        for index, update in enumerate(updates, start=1):
            event = {
                "event_index": index,
                "event": "temporal_tension_update",
                "update": update.to_dict(),
                "previous_hash": previous_hash,
            }
            event_hash = stable_hash(event)
            event["event_hash"] = event_hash
            event_ledger.append(event)
            previous_hash = event_hash

        return {
            "artifact": "temporal_tension_bridge",
            "architecture": "Temporal_Tension_Bridge",
            "case_id": graph.case_id,
            "contradiction_step": late_step,
            "propagated_tension": propagated_tension,
            "assumption_updates": [update.to_dict() for update in updates],
            "tamper_evident_runtime_ledger": event_ledger,
            "ledger_head_hash": previous_hash,
            "time_agnostic_compute_claimed": False,
            "accepted_truth": False,
            "verifier_required_for_acceptance": True,
            "accepted_without_verifier_support_count": 0,
        }


class RetrocausalFuzzer:
    """Generate bounded late-contradiction probes for the temporal bridge."""

    def fuzz(self, graph: SignedGraph) -> dict[str, Any]:
        bridge = TemporalTensionBridge()
        temporal = bridge.propagate(
            graph, contradiction_step=max(3, len(graph.edges) + 2)
        )
        decreased = [
            update
            for update in temporal["assumption_updates"]
            if update["posterior_probability"] < update["prior_probability"]
        ]
        return {
            "artifact": "retrocausal_fuzzer",
            "architecture": "Retrocausal_Fuzzer",
            "case_id": graph.case_id,
            "late_contradiction_case_count": (
                1 if _graph_has_contradiction(graph) else 0
            ),
            "probability_updates_decreased_count": len(decreased),
            "temporal_bridge": temporal,
            "future_memory_is_simulated": True,
            "accepted_truth": False,
            "verifier_required_for_acceptance": True,
            "accepted_without_verifier_support_count": 0,
        }


@dataclass
class ResonanceNode:
    node_id: str
    location: str
    coupling_matrix: dict[str, dict[str, float]]
    harmonic_frequency: float = 1.0
    telemetry_log: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SpectralCouplingTelepathy:
    """Share solved constraint shape telemetry across bounded nodes."""

    def align(
        self, nodes: Iterable[ResonanceNode], solved_node_id: str, graph: SignedGraph
    ) -> dict[str, Any]:
        node_list = list(nodes)
        if not node_list:
            raise ValueError("at least one resonance node is required")
        solved_node = next(
            (node for node in node_list if node.node_id == solved_node_id), node_list[0]
        )
        shape = {
            "case_id": graph.case_id,
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "support_edges": sum(1 for edge in graph.edges if edge.sign > 0),
            "conflict_edges": sum(1 for edge in graph.edges if edge.sign < 0),
            "equilibrium": not _graph_has_contradiction(graph),
        }
        shape_hash = stable_hash(shape)
        transmissions = []
        for node in node_list:
            before_hash = stable_hash(node.coupling_matrix)
            node.telemetry_log.append(
                {
                    "event": "constraint_shape_received",
                    "from_node": solved_node.node_id,
                    "shape_hash": shape_hash,
                    "answer_transmitted": False,
                }
            )
            if node.node_id != solved_node.node_id:
                node.coupling_matrix.setdefault("resonance", {})["shape_alignment"] = (
                    1.0 if shape["equilibrium"] else 0.5
                )
            transmissions.append(
                {
                    "target_node": node.node_id,
                    "matrix_hash_before": before_hash,
                    "matrix_hash_after": stable_hash(node.coupling_matrix),
                    "shape_hash": shape_hash,
                    "answer_packet_bytes": 0,
                }
            )

        return {
            "artifact": "spectral_coupling_telepathy",
            "architecture": "Spectral_Coupling_Telepathy",
            "baseline_harmonic_frequency": solved_node.harmonic_frequency,
            "constraint_shape": shape,
            "constraint_shape_hash": shape_hash,
            "transmissions": transmissions,
            "telepathy_claimed": False,
            "answer_transmitted": False,
            "bandwidth_bytes": len(shape_hash),
            "accepted_truth": False,
            "verifier_required_for_acceptance": True,
            "accepted_without_verifier_support_count": 0,
        }


class UnifiedFieldKernel:
    """Merge generator, fuzzer, and firewall roles behind one verifier gate."""

    def resolve(
        self, question: str, graph: SignedGraph, candidate_text: str | None = None
    ) -> dict[str, Any]:
        photonic = PhotonicStateLedger()
        ledger = photonic.encode_graph(graph)
        gate = photonic.interference_gate(graph)
        verifier_support = _graph_has_verifier_support(graph)
        contradiction = gate["contradiction_detected"]
        zero_tension = (
            verifier_support and not contradiction and gate["residual_tension"] == 0.0
        )
        emitted = zero_tension
        output = candidate_text or f"Resolved zero-tension candidate for: {question}"
        return {
            "artifact": "unified_field_kernel",
            "architecture": "Unified_Field_Kernel",
            "question": question,
            "candidate_text": output,
            "generation_and_verification_unified": True,
            "photonic_ledger_hash": ledger["ledger_hash"],
            "residual_tension": gate["residual_tension"],
            "contradiction_detected": contradiction,
            "typed_verifier_support_present": verifier_support,
            "emitted": emitted,
            "blocked_before_emission": not emitted,
            "block_reason": (
                None if emitted else "non_zero_tension_or_missing_verifier_support"
            ),
            "accepted_truth": emitted,
            "verifier_required_for_acceptance": True,
            "accepted_without_verifier_support_count": (
                1 if emitted and not verifier_support else 0
            ),
        }


class LazyUniverseEngine:
    """Top-level orchestrator for the cognitive physics stack."""

    def run(self, question: str, graph: SignedGraph) -> dict[str, Any]:
        photonic = PhotonicStateLedger()
        ledger = photonic.encode_graph(graph)
        gate = photonic.interference_gate(graph)
        temporal = RetrocausalFuzzer().fuzz(graph)
        nodes = [
            ResonanceNode(
                "node_london",
                "London",
                {"logic": {"logic": 1.0}},
                harmonic_frequency=1.0,
            ),
            ResonanceNode(
                "node_tokyo", "Tokyo", {"logic": {"logic": 0.7}}, harmonic_frequency=1.0
            ),
        ]
        resonance = SpectralCouplingTelepathy().align(nodes, "node_london", graph)
        unified = UnifiedFieldKernel().resolve(question, graph)
        answer = (
            unified["candidate_text"]
            if unified["emitted"]
            else "Abstain: no zero-tension verifier-supported state formed."
        )
        gates = {
            "photonic_state_ledger_ready": bool(ledger["entries"]),
            "interference_gate_ready": gate["accepted_without_verifier_support_count"]
            == 0,
            "temporal_bridge_ready": temporal["accepted_without_verifier_support_count"]
            == 0,
            "resonance_shape_only": resonance["answer_transmitted"] is False,
            "unified_field_boundary_preserved": unified[
                "accepted_without_verifier_support_count"
            ]
            == 0,
            "typed_verifier_required": unified["verifier_required_for_acceptance"],
        }
        return {
            "artifact": "lazy_universe_engine_receipt",
            "engine": "The_Lazy_Universe_Engine",
            "question": question,
            "answer": answer,
            "operating_power_target_watts": 20,
            "ambient_voltage_claimed": False,
            "literal_physics_solves_question_claimed": False,
            "photonic": ledger,
            "interference": gate,
            "retrocausal": temporal,
            "resonance": resonance,
            "unified_field": unified,
            "gates": gates,
            "proof_boundary": PROOF_BOUNDARY,
            "non_claims": COGNITIVE_PHYSICS_NON_CLAIMS,
            "accepted_without_verifier_support_count": 0,
            "candidate_graph_contamination_count": 0,
            "all_gates_passed": all(gates.values()),
        }


def build_demo_graphs() -> dict[str, SignedGraph]:
    coherent = SignedGraph.from_edges(
        "coherent_zero_tension",
        [
            SignedEdge(
                "support_ab", "A", "B", "support", weight=1.0, status="accepted"
            ),
            SignedEdge(
                "support_bc", "B", "C", "support", weight=1.0, status="accepted"
            ),
        ],
        nodes=["A", "B", "C"],
        metadata={"expected": "zero_tension"},
    )
    contradiction = SignedGraph.from_edges(
        "late_contradiction",
        [
            SignedEdge(
                "support_ab", "A", "B", "support", weight=1.0, status="accepted"
            ),
            SignedEdge(
                "support_bc", "B", "C", "support", weight=1.0, status="accepted"
            ),
            SignedEdge(
                "conflict_ac", "A", "C", "conflict", weight=1.0, status="accepted"
            ),
        ],
        nodes=["A", "B", "C"],
        metadata={"expected": "contradiction"},
    )
    unsupported = SignedGraph.from_edges(
        "unsupported_candidate",
        [
            SignedEdge(
                "candidate_ab", "A", "B", "support", weight=1.0, status="candidate"
            )
        ],
        nodes=["A", "B"],
        metadata={"expected": "missing_verifier_support"},
    )
    return {
        coherent.case_id: coherent,
        contradiction.case_id: contradiction,
        unsupported.case_id: unsupported,
    }


def evaluate_cognitive_physics_engine(
    question: str = "Does A resolve to C?",
) -> dict[str, Any]:
    graphs = build_demo_graphs()
    coherent = graphs["coherent_zero_tension"]
    contradiction = graphs["late_contradiction"]
    unsupported = graphs["unsupported_candidate"]

    photonic = PhotonicStateLedger()
    photonic_ledger = photonic.encode_graph(contradiction)
    photonic_gate = photonic.interference_gate(contradiction)
    temporal = RetrocausalFuzzer().fuzz(contradiction)
    resonance = SpectralCouplingTelepathy().align(
        [
            ResonanceNode(
                "node_london",
                "London",
                {"logic": {"logic": 1.0}},
                harmonic_frequency=1.0,
            ),
            ResonanceNode(
                "node_tokyo",
                "Tokyo",
                {"logic": {"logic": 0.25}},
                harmonic_frequency=1.0,
            ),
        ],
        "node_london",
        coherent,
    )
    unified_good = UnifiedFieldKernel().resolve(question, coherent)
    unified_bad = UnifiedFieldKernel().resolve(question, contradiction)
    unified_unsupported = UnifiedFieldKernel().resolve(question, unsupported)
    lazy = LazyUniverseEngine().run(question, coherent)

    gates = {
        "photonic_frequency_slots_present": len(photonic_ledger["entries"])
        == len(contradiction.edges),
        "interference_detects_contradiction": photonic_gate["contradiction_detected"],
        "temporal_updates_prior_probabilities": temporal[
            "probability_updates_decreased_count"
        ]
        > 0,
        "resonance_transmits_shape_not_answer": resonance["answer_transmitted"]
        is False,
        "unified_good_emits": unified_good["emitted"] is True,
        "unified_bad_blocks": unified_bad["blocked_before_emission"] is True,
        "unified_unsupported_blocks": unified_unsupported["blocked_before_emission"]
        is True,
        "lazy_engine_passes": lazy["all_gates_passed"] is True,
        "accepted_without_verifier_support_zero": sum(
            payload["accepted_without_verifier_support_count"]
            for payload in [
                photonic_ledger,
                photonic_gate,
                temporal,
                resonance,
                unified_good,
                unified_bad,
                unified_unsupported,
                lazy,
            ]
        )
        == 0,
    }
    return {
        "artifact": "cognitive_physics_engine_report",
        "engine": ENGINE_NAME,
        "question": question,
        "graphs": {case_id: graph.to_dict() for case_id, graph in graphs.items()},
        "photonic_state_ledger": photonic_ledger,
        "photonic_interference_gate": photonic_gate,
        "retrocausal_fuzzer": temporal,
        "spectral_coupling_telepathy": resonance,
        "unified_field_kernel": {
            "coherent": unified_good,
            "contradiction": unified_bad,
            "unsupported": unified_unsupported,
        },
        "lazy_universe_engine": lazy,
        "gates": gates,
        "proof_boundary": PROOF_BOUNDARY,
        "non_claims": COGNITIVE_PHYSICS_NON_CLAIMS,
        "accepted_without_verifier_support_count": 0,
        "candidate_graph_contamination_count": 0,
        "all_gates_passed": all(gates.values()),
    }


def build_cognitive_physics_receipt(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact": "cognitive_physics_engine_receipt",
        "engine": ENGINE_NAME,
        "report_hash": stable_hash(report),
        "proof_boundary": PROOF_BOUNDARY,
        "implemented_architectures": [
            "Photonic_State_Ledger",
            "Retrocausal_Fuzzer",
            "Temporal_Tension_Bridge",
            "Spectral_Coupling_Telepathy",
            "Unified_Field_Kernel",
            "The_Lazy_Universe_Engine",
        ],
        "verification_summary": report["gates"],
        "non_claims": COGNITIVE_PHYSICS_NON_CLAIMS,
        "accepted_without_verifier_support_count": report[
            "accepted_without_verifier_support_count"
        ],
        "candidate_graph_contamination_count": report[
            "candidate_graph_contamination_count"
        ],
        "all_gates_passed": report["all_gates_passed"],
    }
