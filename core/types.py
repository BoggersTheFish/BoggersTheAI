from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(slots=True)
class Node:
    id: str
    content: str
    topics: List[str] = field(default_factory=list)
    activation: float = 0.0
    stability: float = 1.0
    base_strength: float = 0.5
    last_wave: int = 0
    collapsed: bool = False
    attributes: Dict[str, object] = field(default_factory=dict)
    embedding: List[float] = field(default_factory=list)


@dataclass(slots=True)
class Edge:
    src: str
    dst: str
    weight: float = 1.0
    relation: str = "relates"


@dataclass(slots=True)
class Tension:
    node_id: str
    score: float
    violations: List[str] = field(default_factory=list)
