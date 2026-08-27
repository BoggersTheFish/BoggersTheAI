"""Typed tension channel interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .graph import GraphState
from .types import ChannelResult, ResolverEvent


class TensionChannel(ABC):
    """A typed operational route for measuring and resolving one tension kind."""

    name = "unnamed"
    version = "0.1.0"

    @abstractmethod
    def activate(self, graph: GraphState, context: dict[str, Any]) -> bool:
        """Return true when this channel has work to measure or resolve."""

    @abstractmethod
    def measure(self, graph: GraphState, context: dict[str, Any]) -> ChannelResult:
        """Measure this channel's unresolved pressure."""

    @abstractmethod
    def resolve(self, graph: GraphState, context: dict[str, Any]) -> ResolverEvent:
        """Apply this channel's resolver operation to the graph or context."""

    def serialize(self) -> dict[str, Any]:
        return {"name": self.name, "version": self.version}
