from __future__ import annotations

from ts_core import ChannelResult, GraphState, ResolverEvent, TensionChannel


class QuantifierScopeChannel(TensionChannel):
    name = "quantifier_scope"
    version = "0.1.0"

    def _unsupported_some_all(self, graph: GraphState, context: dict) -> bool:
        query = context.get("query_relation")
        if query is None or query.quantifier != "all":
            return False
        some_edges = [edge for edge in graph.edges if edge.relation == "some" and edge.source == query.subject]
        has_direct_all = graph.has_edge(query.subject, query.predicate, "all")
        return bool(some_edges and not has_direct_all)

    def activate(self, graph: GraphState, context: dict) -> bool:
        return self._unsupported_some_all(graph, context)

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        active = self.activate(graph, context)
        tension = 0.0 if context.get("quantifier_scope_blocked") else (1.0 if active else 0.0)
        return ChannelResult(
            channel=self.name,
            activated=active,
            initial_tension=tension,
            final_tension=tension,
            evidence=["some/all scope conflict"] if active else [],
            details={"protects_against": "overgeneralisation"},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        if not self.activate(graph, context):
            return ResolverEvent(channel=self.name, action="no_op", status="settled")
        context["quantifier_scope_blocked"] = True
        return ResolverEvent(
            channel=self.name,
            action="blocked_some_to_all_upgrade",
            status="resolved",
            tension_delta=-1.0,
            evidence=["some premise cannot force universal conclusion"],
        )
