from __future__ import annotations

from pydantic import BaseModel, Field

from thinking_system.graph.cig.edge import Edge
from thinking_system.graph.cig.graph import Graph


class EdgeTension(BaseModel):
    edge_index: int
    source: str
    target: str
    relation: str
    value: float = Field(ge=0.0)


class TensionReport(BaseModel):
    edge_tensions: list[EdgeTension] = Field(default_factory=list)
    total: float = Field(default=0.0, ge=0.0)

    @property
    def coherence(self) -> float:
        """Simple coherence score in [0, 1] derived from total tension."""
        return 1.0 / (1.0 + self.total)


def edge_tension(graph: Graph, edge: Edge) -> float:
    """Return tau_ij = weight * (a_j - expected_ratio * a_i)^2."""
    source_activation = graph.get_node(edge.source).activation
    target_activation = graph.get_node(edge.target).activation
    expected = edge.expected_ratio * source_activation
    return float(edge.weight * (target_activation - expected) ** 2)


def total_tension(graph: Graph) -> float:
    return float(sum(edge_tension(graph, edge) for edge in graph.edges))


def tension_report(graph: Graph, top_k: int = 10) -> dict:
    if top_k < 0:
        raise ValueError("top_k must be non-negative")

    edge_reports = []
    for index, edge in enumerate(graph.edges):
        source_activation = graph.get_node(edge.source).activation
        target_activation = graph.get_node(edge.target).activation
        expected = edge.expected_ratio * source_activation
        edge_reports.append(
            {
                "edge_index": index,
                "source": edge.source,
                "target": edge.target,
                "relation": edge.relation,
                "weight": edge.weight,
                "expected_ratio": edge.expected_ratio,
                "source_activation": source_activation,
                "target_activation": target_activation,
                "expected_target_activation": expected,
                "tension": edge_tension(graph, edge),
            }
        )

    edge_reports.sort(key=lambda item: (-item["tension"], item["edge_index"]))
    return {
        "total": total_tension(graph),
        "top_edges": edge_reports[:top_k],
    }


def detect_tension(graph: Graph) -> TensionReport:
    """Compatibility wrapper returning the older Pydantic report shape."""
    edge_tensions = [
        EdgeTension(
            edge_index=index,
            source=edge.source,
            target=edge.target,
            relation=edge.relation,
            value=edge_tension(graph, edge),
        )
        for index, edge in enumerate(graph.edges)
    ]
    return TensionReport(edge_tensions=edge_tensions, total=total_tension(graph))
