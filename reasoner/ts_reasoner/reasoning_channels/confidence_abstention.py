from __future__ import annotations

from ts_core import ChannelResult, GraphState, ResolverEvent, TensionChannel


class ConfidenceAbstentionChannel(TensionChannel):
    name = "confidence_abstention"
    version = "0.1.0"

    def _needs_abstention(self, context: dict) -> bool:
        chain = context.get("chain")
        if chain is None:
            return False
        answer = chain.final_answer.lower()
        if "not enough" in answer or "unsupported" in answer:
            return True
        conclusion_steps = [step for step in chain.steps if step.kind == "conclusion"]
        return any(step.confidence < 0.5 for step in conclusion_steps)

    def activate(self, graph: GraphState, context: dict) -> bool:
        return True

    def measure(self, graph: GraphState, context: dict) -> ChannelResult:
        needs = self._needs_abstention(context)
        tension = 0.0 if context.get("abstention") is not None else (1.0 if needs else 0.0)
        return ChannelResult(
            channel=self.name,
            activated=True,
            initial_tension=tension,
            final_tension=tension,
            evidence=[context.get("chain").final_answer] if needs and context.get("chain") else [],
            details={"decision": "abstain" if needs else "answer"},
        )

    def resolve(self, graph: GraphState, context: dict) -> ResolverEvent:
        needs = self._needs_abstention(context)
        context["abstention"] = bool(needs)
        return ResolverEvent(
            channel=self.name,
            action="abstained_or_answered",
            status="resolved",
            tension_delta=-1.0 if needs else 0.0,
            details={"abstained": bool(needs)},
        )
