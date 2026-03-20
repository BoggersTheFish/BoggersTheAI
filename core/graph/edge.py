from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GraphEdge:
    src: str
    dst: str
    weight: float = 1.0
    relation: str = "relates"
