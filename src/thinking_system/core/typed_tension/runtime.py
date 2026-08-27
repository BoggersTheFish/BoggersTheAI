"""Runtime loop for typed tension channels."""

from __future__ import annotations

from typing import Any, Iterable

from .channels import TensionChannel
from .graph import GraphState
from .types import ChannelResult, RuntimeTrace


class TypedTensionRuntime:
    def __init__(self, channels: Iterable[TensionChannel]) -> None:
        self.channels = list(channels)

    def run(
        self, graph: GraphState, context: dict[str, Any] | None = None
    ) -> RuntimeTrace:
        ctx = context if context is not None else {}
        results: list[ChannelResult] = []
        events = []
        for channel in self.channels:
            activated = channel.activate(graph, ctx)
            if not activated:
                result = ChannelResult(channel=channel.name, activated=False)
                results.append(result)
                continue
            before = channel.measure(graph, ctx)
            event = channel.resolve(graph, ctx)
            after = channel.measure(graph, ctx)
            result = ChannelResult(
                channel=channel.name,
                activated=True,
                initial_tension=before.initial_tension,
                final_tension=after.final_tension,
                resolution=event.action,
                evidence=after.evidence or before.evidence,
                details={**before.details, **after.details, "event": event.to_dict()},
            )
            results.append(result)
            events.append(event)

        global_tension = round(
            sum(result.final_tension for result in results) / max(1, len(results)), 4
        )
        return RuntimeTrace(
            channel_results=results,
            resolver_events=events,
            global_tension=global_tension,
            settled=global_tension == 0.0,
            metadata={"channel_count": len(self.channels)},
        )
