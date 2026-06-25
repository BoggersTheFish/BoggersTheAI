from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from ts_metacompute.spectral.laplacian import edge_energy, node_index
from ts_metacompute.spectral.signed_graph import SignedGraph


@dataclass(frozen=True)
class EdgeResidual:
    edge_id: str
    source: str
    target: str
    relation: str
    residual: float
    weight: float
    provenance_weight: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def rank_edge_residuals(graph: SignedGraph, vector: list[float]) -> list[EdgeResidual]:
    index = node_index(graph)
    rows = [
        EdgeResidual(
            edge_id=edge.edge_id,
            source=edge.source,
            target=edge.target,
            relation=edge.relation,
            residual=round(edge_energy(edge, vector, index), 6),
            weight=round(float(edge.weight), 6),
            provenance_weight=round(float(edge.provenance_weight), 6),
            status=edge.status,
        )
        for edge in graph.edges
    ]
    rows.sort(key=lambda row: (-row.residual, row.provenance_weight, row.edge_id))
    return rows
