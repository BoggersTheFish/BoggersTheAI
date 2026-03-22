from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class NodeSynthesizer(Protocol):
    """Contract for graph-native or hybrid node-level synthesis (TS primary path)."""

    def synthesize(self, context: str, query: str) -> str: ...
