from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from thinking_system.graph.cig.graph import CIGraph


def load_graph(path: str | Path) -> CIGraph:
    """Load a CIGraph from a YAML file."""
    with Path(path).open("r", encoding="utf-8") as handle:
        payload: dict[str, Any] = yaml.safe_load(handle) or {}
    return graph_from_mapping(payload)


def save_graph(graph: CIGraph, path: str | Path) -> None:
    """Save a CIGraph to a YAML file."""
    payload = graph_to_mapping(graph)
    with Path(path).open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False)


def load_graph_yaml(path: str | Path) -> CIGraph:
    """Compatibility alias for load_graph."""
    return load_graph(path)


def graph_from_mapping(payload: dict[str, Any]) -> CIGraph:
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])
    if not isinstance(nodes, list):
        raise TypeError("nodes must be a list")
    if not isinstance(edges, list):
        raise TypeError("edges must be a list")
    return CIGraph.from_records(nodes=nodes, edges=edges)


def graph_to_mapping(graph: CIGraph) -> dict[str, list[dict[str, Any]]]:
    return {
        "nodes": [node.model_dump(mode="json") for node in graph.nodes.values()],
        "edges": [edge.model_dump(mode="json") for edge in graph.edges],
    }
