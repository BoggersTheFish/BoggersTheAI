from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

SUPPORT_RELATIONS = frozenset({"support", "supports", "entails", "align"})
CONFLICT_RELATIONS = frozenset({"conflict", "conflicts", "contradicts", "anti_align"})
NON_PROOF_STATUSES = frozenset({"candidate", "unsupported", "rejected", "abstained"})


def normalize_node(value: str) -> str:
    return " ".join(str(value).strip().split())


def relation_sign(relation: str) -> int:
    normalized = str(relation).strip().lower()
    if normalized in SUPPORT_RELATIONS:
        return 1
    if normalized in CONFLICT_RELATIONS:
        return -1
    raise ValueError(f"unknown signed relation: {relation!r}")


@dataclass(frozen=True)
class SignedEdge:
    edge_id: str
    source: str
    target: str
    relation: str
    weight: float = 1.0
    status: str = "accepted"
    provenance_weight: float = 1.0
    repair_hint: str = ""

    @property
    def sign(self) -> int:
        return relation_sign(self.relation)

    @property
    def is_proof_edge(self) -> bool:
        return self.status == "accepted"

    def flipped(self) -> "SignedEdge":
        relation = "conflict" if self.sign > 0 else "support"
        return SignedEdge(
            edge_id=self.edge_id,
            source=self.source,
            target=self.target,
            relation=relation,
            weight=self.weight,
            status=self.status,
            provenance_weight=self.provenance_weight,
            repair_hint=self.repair_hint,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["sign"] = self.sign
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SignedEdge":
        edge = cls(
            edge_id=str(payload["edge_id"]),
            source=normalize_node(str(payload["source"])),
            target=normalize_node(str(payload["target"])),
            relation=str(payload.get("relation", "support")).strip().lower(),
            weight=float(payload.get("weight", 1.0)),
            status=str(payload.get("status", "accepted")).strip().lower(),
            provenance_weight=float(payload.get("provenance_weight", 1.0)),
            repair_hint=str(payload.get("repair_hint", "")).strip().lower(),
        )
        if edge.weight <= 0.0:
            raise ValueError(f"edge {edge.edge_id!r} weight must be positive")
        if edge.provenance_weight < 0.0:
            raise ValueError(
                f"edge {edge.edge_id!r} provenance_weight must be non-negative"
            )
        relation_sign(edge.relation)
        return edge


@dataclass(frozen=True)
class SignedGraph:
    case_id: str
    nodes: tuple[str, ...]
    edges: tuple[SignedEdge, ...]
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SignedGraph":
        edges = tuple(SignedEdge.from_dict(edge) for edge in payload.get("edges", []))
        node_order: list[str] = []
        for raw in payload.get("nodes", []):
            node = normalize_node(str(raw))
            if node and node not in node_order:
                node_order.append(node)
        for edge in edges:
            for node in (edge.source, edge.target):
                if node and node not in node_order:
                    node_order.append(node)
        if not node_order:
            raise ValueError("signed graph must contain at least one node")
        return cls(
            case_id=str(payload.get("case_id", "")),
            nodes=tuple(node_order),
            edges=edges,
            metadata=dict(payload.get("metadata", {})),
        )

    @classmethod
    def from_edges(
        cls,
        case_id: str,
        edges: Iterable[SignedEdge],
        *,
        nodes: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> "SignedGraph":
        return cls.from_dict(
            {
                "case_id": case_id,
                "nodes": list(nodes),
                "edges": [edge.to_dict() for edge in edges],
                "metadata": metadata or {},
            }
        )

    def without_edge(self, edge_id: str) -> "SignedGraph":
        return SignedGraph(
            case_id=self.case_id,
            nodes=self.nodes,
            edges=tuple(edge for edge in self.edges if edge.edge_id != edge_id),
            metadata=dict(self.metadata or {}),
        )

    def with_flipped_edge(self, edge_id: str) -> "SignedGraph":
        return SignedGraph(
            case_id=self.case_id,
            nodes=self.nodes,
            edges=tuple(
                edge.flipped() if edge.edge_id == edge_id else edge
                for edge in self.edges
            ),
            metadata=dict(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "nodes": list(self.nodes),
            "edges": [edge.to_dict() for edge in self.edges],
            "metadata": dict(self.metadata or {}),
        }

    def candidate_edge_count(self) -> int:
        return sum(1 for edge in self.edges if edge.status in NON_PROOF_STATUSES)
