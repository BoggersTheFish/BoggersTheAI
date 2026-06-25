from __future__ import annotations

from ts_core import ChannelResult, GraphState, ResolverEvent, TensionChannel

from ._base import has_directed_path


class IdentityPreservationChannel(TensionChannel):
    name = "identity_preservation"
    version = "0.1.0"

    def _query_pair(self, context: dict):
        query = context.get("query_relation")
        if query is None:
            return None
        return query.subject, query.predicate

    def activate(self, graph: GraphState, context: dict) -> bool:
        pair = self._query_pair(context)
        return bool(pair and pair[0] != pair[1] and has_directed_path(graph, pair[0], pair[1]))

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        pair = self._query_pair(context)
        marker = f"{pair[0]}!={pair[1]}" if pair else ""
        active = self.activate(graph, context)
        tension = 0.0 if marker in context.get("blocked_equalities", []) else (1.0 if active else 0.0)
        return ChannelResult(
            channel=self.name,
            activated=active,
            initial_tension=tension,
            final_tension=tension,
            evidence=[str(pair)] if active else [],
            details={"protects_against": "relation_identity_collapse"},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        pair = self._query_pair(context)
        if pair is None:
            return ResolverEvent(channel=self.name, action="no_op", status="settled")
        marker = f"{pair[0]}!={pair[1]}"
        context.setdefault("blocked_equalities", []).append(marker)
        return ResolverEvent(
            channel=self.name,
            action="preserved_distinct_nodes",
            status="resolved",
            target=marker,
            tension_delta=-1.0,
            evidence=[marker],
        )
