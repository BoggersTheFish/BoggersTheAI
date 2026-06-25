from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from ts_metacompute.spectral.laplacian import edge_energy, node_index, signed_laplacian
from ts_metacompute.spectral.residuals import EdgeResidual, rank_edge_residuals
from ts_metacompute.spectral.signed_graph import SignedGraph


@dataclass(frozen=True)
class SpectralMode:
    mode_index: int
    eigenvalue: float
    node_values: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpectralRead:
    case_id: str
    node_count: int
    edge_count: int
    spectral_tension: float
    coherent: bool
    contradiction_detected: bool
    dominant_modes: tuple[SpectralMode, ...]
    residual_edges: tuple[EdgeResidual, ...]
    top_edge_id: str
    unique_top_residual: bool
    reader_decision: str
    accepted_truth: bool = False
    accepted_without_verifier_support_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "spectral_tension": self.spectral_tension,
            "coherent": self.coherent,
            "contradiction_detected": self.contradiction_detected,
            "dominant_modes": [mode.to_dict() for mode in self.dominant_modes],
            "residual_edges": [edge.to_dict() for edge in self.residual_edges],
            "top_edge_id": self.top_edge_id,
            "unique_top_residual": self.unique_top_residual,
            "reader_decision": self.reader_decision,
            "accepted_truth": self.accepted_truth,
            "accepted_without_verifier_support_count": self.accepted_without_verifier_support_count,
        }


def _identity(size: int) -> list[list[float]]:
    return [[1.0 if row == col else 0.0 for col in range(size)] for row in range(size)]


def jacobi_eigen_decomposition(
    matrix: list[list[float]],
    *,
    tolerance: float = 1e-10,
    max_sweeps: int = 200,
) -> tuple[list[float], list[list[float]]]:
    """Deterministic symmetric eigensolver for small stdlib-only graphs."""

    size = len(matrix)
    if size == 0:
        return [], []
    if size == 1:
        return [float(matrix[0][0])], [[1.0]]

    a = [[float(value) for value in row] for row in matrix]
    vectors = _identity(size)

    for _ in range(max_sweeps * size * size):
        pivot_row = 0
        pivot_col = 1
        pivot_value = abs(a[pivot_row][pivot_col])
        for row in range(size):
            for col in range(row + 1, size):
                value = abs(a[row][col])
                if value > pivot_value:
                    pivot_row = row
                    pivot_col = col
                    pivot_value = value

        if pivot_value < tolerance:
            break

        app = a[pivot_row][pivot_row]
        aqq = a[pivot_col][pivot_col]
        apq = a[pivot_row][pivot_col]
        tau = (aqq - app) / (2.0 * apq)
        if tau >= 0.0:
            tangent = 1.0 / (tau + math.sqrt(1.0 + tau * tau))
        else:
            tangent = -1.0 / (-tau + math.sqrt(1.0 + tau * tau))
        cosine = 1.0 / math.sqrt(1.0 + tangent * tangent)
        sine = tangent * cosine

        for row in range(size):
            if row in {pivot_row, pivot_col}:
                continue
            arp = a[row][pivot_row]
            arq = a[row][pivot_col]
            a[row][pivot_row] = cosine * arp - sine * arq
            a[pivot_row][row] = a[row][pivot_row]
            a[row][pivot_col] = sine * arp + cosine * arq
            a[pivot_col][row] = a[row][pivot_col]

        a[pivot_row][pivot_row] = cosine * cosine * app - 2.0 * sine * cosine * apq + sine * sine * aqq
        a[pivot_col][pivot_col] = sine * sine * app + 2.0 * sine * cosine * apq + cosine * cosine * aqq
        a[pivot_row][pivot_col] = 0.0
        a[pivot_col][pivot_row] = 0.0

        for row in range(size):
            vrp = vectors[row][pivot_row]
            vrq = vectors[row][pivot_col]
            vectors[row][pivot_row] = cosine * vrp - sine * vrq
            vectors[row][pivot_col] = sine * vrp + cosine * vrq

    pairs = []
    for col in range(size):
        vector = [vectors[row][col] for row in range(size)]
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        pairs.append((max(0.0, a[col][col]), [value / norm for value in vector]))
    pairs.sort(key=lambda item: (round(item[0], 12), item[1]))
    return [item[0] for item in pairs], [item[1] for item in pairs]


def _connected_components(graph: SignedGraph) -> list[list[str]]:
    neighbors = {node: set() for node in graph.nodes}
    for edge in graph.edges:
        neighbors[edge.source].add(edge.target)
        neighbors[edge.target].add(edge.source)

    components: list[list[str]] = []
    seen: set[str] = set()
    for node in graph.nodes:
        if node in seen:
            continue
        frontier = [node]
        seen.add(node)
        component: list[str] = []
        while frontier:
            current = frontier.pop(0)
            component.append(current)
            for neighbor in sorted(neighbors[current]):
                if neighbor not in seen:
                    seen.add(neighbor)
                    frontier.append(neighbor)
        components.append(component)
    return components


def _component_graph(graph: SignedGraph, nodes: list[str]) -> SignedGraph:
    node_set = set(nodes)
    return SignedGraph(
        case_id=graph.case_id,
        nodes=tuple(nodes),
        edges=tuple(edge for edge in graph.edges if edge.source in node_set and edge.target in node_set),
        metadata=dict(graph.metadata or {}),
    )


def _component_read_basis(component: SignedGraph) -> tuple[float, list[str], list[float], list[float], list[list[float]]]:
    nodes, matrix = signed_laplacian(component)
    eigenvalues, eigenvectors = jacobi_eigen_decomposition(matrix)
    if not eigenvalues:
        return 0.0, nodes, [0.0 for _ in nodes], [], []
    return float(eigenvalues[0]), nodes, list(eigenvectors[0]), eigenvalues, eigenvectors


def _same_pressure_ambiguous(component: SignedGraph) -> bool:
    if len(component.edges) < len(component.nodes):
        return False
    weights = {round(edge.weight, 6) for edge in component.edges}
    provenance = {round(edge.provenance_weight, 6) for edge in component.edges}
    statuses = {edge.status for edge in component.edges}
    return len(weights) == 1 and len(provenance) == 1 and statuses == {"accepted"}


def read_spectral_tension(
    graph: SignedGraph,
    *,
    tension_threshold: float = 0.08,
    tie_tolerance: float = 1e-5,
    mode_count: int = 3,
) -> SpectralRead:
    full_nodes = list(graph.nodes)
    selected_graph = graph
    selected_nodes = full_nodes
    selected_vector = [0.0 for _ in full_nodes]
    selected_eigenvalues: list[float] = []
    selected_eigenvectors: list[list[float]] = []
    selected_tension = 0.0

    for component_nodes in _connected_components(graph):
        component = _component_graph(graph, component_nodes)
        tension, nodes, vector, eigenvalues, eigenvectors = _component_read_basis(component)
        if tension > selected_tension or not selected_eigenvalues:
            selected_tension = tension
            selected_graph = component
            selected_nodes = nodes
            selected_vector = vector
            selected_eigenvalues = eigenvalues
            selected_eigenvectors = eigenvectors

    full_index = {node: idx for idx, node in enumerate(full_nodes)}
    reader_vector = [0.0 for _ in full_nodes]
    for node, value in zip(selected_nodes, selected_vector):
        reader_vector[full_index[node]] = value
    spectral_tension = round(float(selected_tension), 6)

    modes: list[SpectralMode] = []
    for idx, (eigenvalue, vector) in enumerate(zip(selected_eigenvalues[:mode_count], selected_eigenvectors[:mode_count])):
        modes.append(
            SpectralMode(
                mode_index=idx,
                eigenvalue=round(float(eigenvalue), 6),
                node_values={node: round(float(value), 6) for node, value in zip(selected_nodes, vector)},
            )
        )

    residuals = tuple(rank_edge_residuals(graph, reader_vector))
    if residuals:
        top = residuals[0]
        second = residuals[1] if len(residuals) > 1 else None
        unique_top = second is None or (top.residual - second.residual) > tie_tolerance
        top_edge_id = top.edge_id
    else:
        unique_top = False
        top_edge_id = ""

    contradiction = spectral_tension > tension_threshold
    coherent = not contradiction
    structurally_ambiguous = contradiction and _same_pressure_ambiguous(selected_graph)
    if not contradiction:
        decision = "coherent_or_low_tension"
    elif structurally_ambiguous or not unique_top:
        decision = "abstain_no_unique_culprit"
        unique_top = False
    else:
        decision = "suggest_repair_target"

    # Force edge-energy calculation through the public helper during reads.
    # This catches node-index drift in tests and downstream adapters.
    index = node_index(graph)
    for edge in graph.edges:
        edge_energy(edge, reader_vector, index)

    return SpectralRead(
        case_id=graph.case_id,
        node_count=len(full_nodes),
        edge_count=len(graph.edges),
        spectral_tension=spectral_tension,
        coherent=coherent,
        contradiction_detected=contradiction,
        dominant_modes=tuple(modes),
        residual_edges=residuals,
        top_edge_id=top_edge_id,
        unique_top_residual=unique_top,
        reader_decision=decision,
    )
