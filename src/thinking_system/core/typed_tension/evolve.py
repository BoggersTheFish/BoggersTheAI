"""Break/Evolve hook protocol for typed tension runtimes."""

from __future__ import annotations

from typing import Protocol

from .graph import GraphState
from .types import ResolverEvent


class EvolveHook(Protocol):
    def __call__(self, graph: GraphState, event: ResolverEvent) -> None: ...


def apply_evolve_hooks(
    graph: GraphState, events: list[ResolverEvent], hooks: list[EvolveHook]
) -> None:
    for event in events:
        for hook in hooks:
            hook(graph, event)
