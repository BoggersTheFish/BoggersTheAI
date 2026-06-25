"""Shared helpers for reasoning channels."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable

try:
    from ts_core import Edge, GraphState
except ModuleNotFoundError:
    sibling = Path(__file__).resolve().parents[2].parent / "TS-Core"
    if sibling.exists():
        sys.path.insert(0, str(sibling))
    from ts_core import Edge, GraphState


def relation_edges(graph: GraphState, relation: str = "all") -> list[Edge]:
    return [edge for edge in graph.edges if edge.relation == relation]


def has_directed_path(graph: GraphState, source: str, target: str, relations: Iterable[str] = ("all",)) -> bool:
    allowed = set(relations)
    seen = set()
    frontier = [source]
    while frontier:
        node = frontier.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        frontier.extend(edge.target for edge in graph.outgoing(node) if edge.relation in allowed)
    return False
