from __future__ import annotations

from ts_metacompute.spectral.signed_graph import SignedEdge, SignedGraph


def node_index(graph: SignedGraph) -> dict[str, int]:
    return {node: idx for idx, node in enumerate(graph.nodes)}


def signed_laplacian(graph: SignedGraph) -> tuple[list[str], list[list[float]]]:
    """Return the signed Laplacian for support/conflict edge constraints.

    Energy is sum w * (x_u - sign(edge) * x_v)^2. Support edges want equal
    values, conflict edges want opposite values.
    """

    nodes = list(graph.nodes)
    index = node_index(graph)
    size = len(nodes)
    matrix = [[0.0 for _ in range(size)] for _ in range(size)]

    for edge in graph.edges:
        left = index[edge.source]
        right = index[edge.target]
        weight = float(edge.weight)
        sign = edge.sign
        matrix[left][left] += weight
        matrix[right][right] += weight
        matrix[left][right] -= sign * weight
        matrix[right][left] -= sign * weight

    return nodes, matrix


def edge_energy(edge: SignedEdge, vector: list[float], index: dict[str, int]) -> float:
    left = vector[index[edge.source]]
    right = vector[index[edge.target]]
    return float(edge.weight) * (left - edge.sign * right) ** 2


def total_energy(graph: SignedGraph, vector: list[float]) -> float:
    index = node_index(graph)
    return sum(edge_energy(edge, vector, index) for edge in graph.edges)
