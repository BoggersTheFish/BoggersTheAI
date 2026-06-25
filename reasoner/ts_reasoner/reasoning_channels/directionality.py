from __future__ import annotations

from ts_core import ChannelResult, GraphState, ResolverEvent, TensionChannel

from ._base import has_directed_path


class DirectionalityChannel(TensionChannel):
    name = "directionality"
    version = "0.1.0"

    def _unsupported_reverse(self, graph: GraphState, context: dict) -> tuple[str, str] | None:
        query = context.get("query_relation")
        if query is None:
            return None
        source, target = query.subject, query.predicate
        if graph.has_edge(source, target, query.quantifier):
            return None
        if has_directed_path(graph, target, source):
            return source, target
        return None

    def activate(self, graph: GraphState, context: dict) -> bool:
        return self._unsupported_reverse(graph, context) is not None

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        pair = self._unsupported_reverse(graph, context)
        blocked = f"{pair[0]}->{pair[1]}" if pair else ""
        tension = 0.0 if blocked in context.get("blocked_edges", []) else (1.0 if pair else 0.0)
        return ChannelResult(
            channel=self.name,
            activated=pair is not None,
            initial_tension=tension,
            final_tension=tension,
            evidence=[f"{pair[0]}->{pair[1]}"] if pair else [],
            details={"protects_against": "converse_fallacy"},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        pair = self._unsupported_reverse(graph, context)
        if pair is None:
            return ResolverEvent(channel=self.name, action="no_op", status="settled")
        blocked = f"{pair[0]}->{pair[1]}"
        context.setdefault("blocked_edges", []).append(blocked)
        return ResolverEvent(
            channel=self.name,
            action="blocked_reverse_inference",
            status="resolved",
            target=blocked,
            tension_delta=-1.0,
            evidence=[blocked],
        )
