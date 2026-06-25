from __future__ import annotations

from ts_core import ChannelResult, GraphState, ResolverEvent, TensionChannel


class ContradictionChannel(TensionChannel):
    name = "contradiction"
    version = "0.1.0"

    def _pairs(self, context: dict) -> list[list[str]]:
        cig = context.get("cig_check")
        return list(getattr(cig, "contradiction_pairs", []) or [])

    def activate(self, graph: GraphState, context: dict) -> bool:
        return bool(self._pairs(context))

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        pairs = self._pairs(context)
        tension = 0.0 if context.get("contradiction_flagged") else (1.0 if pairs else 0.0)
        return ChannelResult(
            channel=self.name,
            activated=bool(pairs),
            initial_tension=tension,
            final_tension=tension,
            evidence=["|".join(pair) for pair in pairs],
            details={"contradiction_pairs": len(pairs)},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        pairs = self._pairs(context)
        if not pairs:
            return ResolverEvent(channel=self.name, action="no_op", status="settled")
        context["contradiction_flagged"] = True
        return ResolverEvent(
            channel=self.name,
            action="flagged_contradiction",
            status="resolved",
            tension_delta=-1.0,
            evidence=["|".join(pair) for pair in pairs],
        )
