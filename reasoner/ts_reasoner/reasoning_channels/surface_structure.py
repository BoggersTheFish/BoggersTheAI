from __future__ import annotations

from ts_core import ChannelResult, GraphState, ResolverEvent, TensionChannel


class SurfaceStructureChannel(TensionChannel):
    name = "surface_structure"
    version = "0.1.0"

    def activate(self, graph: GraphState, context: dict) -> bool:
        return any(edge.data.get("status") in {"premise", "candidate", "inferred"} for edge in graph.edges)

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        untagged = [
            f"{edge.source}->{edge.target}"
            for edge in graph.edges
            if edge.relation in {"all", "some", "no"} and "status" not in edge.data
        ]
        return ChannelResult(
            channel=self.name,
            activated=self.activate(graph, context),
            initial_tension=1.0 if untagged else 0.0,
            final_tension=1.0 if untagged else 0.0,
            evidence=untagged,
            details={"untagged_claim_edges": len(untagged)},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        tags = {}
        for edge in graph.edges:
            status = edge.data.get("status")
            if status:
                tags[f"{edge.source}->{edge.target}:{edge.relation}"] = status
        context["surface_tags"] = tags
        return ResolverEvent(
            channel=self.name,
            action="tagged_premise_inferred_candidate_edges",
            status="resolved",
            tension_delta=-1.0,
            details={"tag_count": len(tags)},
        )
