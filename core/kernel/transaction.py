"""Transaction request, workspace and result types."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from ..types import Edge, Node
from .ir import TSIRDocument, VerifierObligation, stable_hash


class CommitDecision(str, Enum):
    COMMIT = "commit"
    REJECT = "reject"
    QUARANTINE = "quarantine"
    REPAIR = "repair"
    BRANCH = "branch"
    ABSTAIN = "abstain"


@dataclass(frozen=True, slots=True)
class TransactionRequest:
    raw_input: str
    provenance: str = "user"
    render_language: bool = True
    use_bogvm: bool = True


@dataclass(slots=True)
class TransactionWorkspace:
    base_graph_hash: str
    document: TSIRDocument
    base_nodes: dict[str, Node]
    base_edges: list[Edge]
    obligations: list[VerifierObligation] = field(default_factory=list)
    proof_objects: list[Any] = field(default_factory=list)
    verification_results: list[Any] = field(default_factory=list)
    bogvm_artifacts: list[dict[str, Any]] = field(default_factory=list)
    derived_claims: list[Any] = field(default_factory=list)
    rejected_claims: list[str] = field(default_factory=list)
    committed_graph_delta: dict[str, Any] = field(
        default_factory=lambda: {"nodes": [], "edges": []}
    )

    def is_required_obligation(self, obligation_id: str) -> bool:
        for obligation in self.obligations:
            if obligation.id == obligation_id:
                return obligation.required
        return False

    def add_obligation(self, obligation: VerifierObligation) -> None:
        if any(existing.id == obligation.id for existing in self.obligations):
            return
        self.obligations.append(obligation)


@dataclass(frozen=True, slots=True)
class TransactionResult:
    decision: CommitDecision
    receipt: Any
    rendered: str


def graph_snapshot(graph: Any) -> tuple[dict[str, Node], list[Edge]]:
    if hasattr(graph, "snapshot_read"):
        return graph.snapshot_read()
    return (
        {node_id: copy.deepcopy(node) for node_id, node in graph.nodes.items()},
        [copy.deepcopy(edge) for edge in graph.edges],
    )


def graph_state_hash_from_parts(nodes: dict[str, Node], edges: list[Edge]) -> str:
    payload = {
        "nodes": sorted(
            (asdict(node) for node in nodes.values()), key=lambda x: x["id"]
        ),
        "edges": sorted(
            (asdict(edge) for edge in edges),
            key=lambda x: (x["src"], x["dst"], x["relation"], x["weight"]),
        ),
    }
    return stable_hash(payload)


def graph_state_hash(graph: Any) -> str:
    nodes, edges = graph_snapshot(graph)
    return graph_state_hash_from_parts(nodes, edges)
