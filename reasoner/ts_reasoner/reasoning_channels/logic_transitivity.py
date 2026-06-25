from __future__ import annotations

from ts_core import ChannelResult, Edge, GraphState, ResolverEvent, TensionChannel

from ._base import relation_edges


class LogicTransitivityChannel(TensionChannel):
    name = "logic_transitivity"
    version = "0.1.0"

    def _usable_edges(self, graph: GraphState):
        return [
            edge
            for edge in relation_edges(graph, "all")
            if edge.data.get("status", "premise") in {"premise", "inferred"}
        ]

    def _has_usable_edge(self, graph: GraphState, source: str, target: str) -> bool:
        return any(edge.source == source and edge.target == target for edge in self._usable_edges(graph))

    def _missing(self, graph: GraphState) -> list[tuple[str, str, str]]:
        missing = []
        edges = self._usable_edges(graph)
        for left in edges:
            for right in edges:
                if left.target == right.source and not self._has_usable_edge(graph, left.source, right.target):
                    missing.append((left.source, left.target, right.target))
        return missing

    def activate(self, graph: GraphState, context: dict) -> bool:
        return bool(self._missing(graph))

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        missing = self._missing(graph)
        tension = 1.0 if missing else 0.0
        return ChannelResult(
            channel=self.name,
            activated=bool(missing),
            initial_tension=tension,
            final_tension=tension,
            evidence=[f"{a}->{b}->{c}" for a, b, c in missing],
            details={"missing_inferences": len(missing)},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        missing = self._missing(graph)
        if not missing:
            return ResolverEvent(channel=self.name, action="no_op", status="settled")
        added = []
        while missing:
            source, via, target = missing[0]
            graph.add_edge(
                Edge(
                    source,
                    target,
                    relation="all",
                    weight=1.0,
                    data={"status": "inferred", "channel": self.name, "via": via},
                )
            )
            added.append((source, via, target))
            missing = self._missing(graph)
        return ResolverEvent(
            channel=self.name,
            action="added_inferred_edge",
            status="resolved",
            target=", ".join(f"{source}->{target}" for source, _via, target in added),
            tension_delta=-float(len(added)),
            evidence=[f"{source}->{via}->{target}" for source, via, target in added],
        )
