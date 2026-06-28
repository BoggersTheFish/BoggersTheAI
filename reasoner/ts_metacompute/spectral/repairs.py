from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ts_metacompute.spectral.modes import SpectralRead, read_spectral_tension
from ts_metacompute.spectral.signed_graph import SignedEdge, SignedGraph


@dataclass(frozen=True)
class RepairCandidate:
    edge_id: str
    action: str
    relation: str
    relief: float
    rank_score: float
    proof_effect: str = "candidate_only"
    verifier_required_for_acceptance: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _action_for_edge(edge: SignedEdge, action: str) -> str:
    if edge.repair_hint in {"split", "branch"} and action == "remove":
        return "split_context_candidate"
    if action == "remove":
        return "remove_edge_candidate"
    if action == "flip":
        return "flip_relation_candidate"
    return "inspect_edge_candidate"


def rank_repair_candidates(
    graph: SignedGraph, read: SpectralRead | None = None
) -> list[RepairCandidate]:
    read = read or read_spectral_tension(graph)
    original_tension = read.spectral_tension
    by_id = {edge.edge_id: edge for edge in graph.edges}
    candidates: list[RepairCandidate] = []

    for residual in read.residual_edges:
        edge = by_id[residual.edge_id]
        removed = read_spectral_tension(
            graph.without_edge(edge.edge_id)
        ).spectral_tension
        flipped = read_spectral_tension(
            graph.with_flipped_edge(edge.edge_id)
        ).spectral_tension
        actions = (
            (("remove", removed),)
            if edge.repair_hint in {"split", "branch"}
            else (("remove", removed), ("flip", flipped))
        )
        for action, after_tension in actions:
            relief = max(0.0, original_tension - after_tension)
            provenance_pressure = max(0.1, 2.0 - float(edge.provenance_weight))
            candidate_pressure = 1.25 if edge.status == "candidate" else 1.0
            rank_score = (
                relief * provenance_pressure * candidate_pressure
                + residual.residual * 0.01
            )
            candidates.append(
                RepairCandidate(
                    edge_id=edge.edge_id,
                    action=_action_for_edge(edge, action),
                    relation=edge.relation,
                    relief=round(relief, 6),
                    rank_score=round(rank_score, 6),
                )
            )

    candidates.sort(
        key=lambda row: (-row.rank_score, -row.relief, row.edge_id, row.action)
    )
    return candidates
