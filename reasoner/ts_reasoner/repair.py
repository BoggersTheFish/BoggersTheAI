"""Repair suggestions guided by high-tension issues."""

from __future__ import annotations

import re
from typing import List

from .types import ReasoningChain, ReasoningStep, RepairSuggestion, TensionScore


class TensionRepairer:
    """Create traceable repair suggestions; v0 does not mutate hidden state."""

    def suggest(self, chain: ReasoningChain, score: TensionScore) -> List[RepairSuggestion]:
        repairs: List[RepairSuggestion] = []
        step_by_id = {step.step_id: step for step in chain.steps}
        for issue in score.issues:
            step = step_by_id.get(issue.step_id)
            if step is None:
                continue
            proposed, rationale, delta = self._proposal(step.text, issue.kind)
            repairs.append(
                RepairSuggestion(
                    repair_id=f"{chain.chain_id}:repair:{len(repairs) + 1}",
                    target_step_id=step.step_id,
                    issue_kind=issue.kind,
                    original_text=step.text,
                    proposed_text=proposed,
                    rationale=rationale,
                    expected_tension_delta=delta,
                )
            )
        return repairs

    def apply(self, chain: ReasoningChain, repair: RepairSuggestion) -> ReasoningChain:
        """Return a new chain with the target step text replaced by a repair."""
        repaired_steps: List[ReasoningStep] = []
        for step in chain.steps:
            if step.step_id != repair.target_step_id:
                repaired_steps.append(step)
                continue
            repaired_steps.append(
                ReasoningStep(
                    step_id=step.step_id,
                    text=repair.proposed_text,
                    kind=step.kind,
                    dependencies=self._dependencies_after_repair(step, repair),
                    confidence=min(step.confidence, 0.55),
                )
            )
        return ReasoningChain(
            chain_id=f"{chain.chain_id}:repaired",
            question=chain.question,
            premises=chain.premises,
            steps=repaired_steps,
            final_answer=self._answer_from_repair(chain, repair),
            generator=chain.generator,
        )

    def _proposal(self, text: str, issue_kind: str) -> tuple[str, str, float]:
        if issue_kind == "quantifier_jump":
            downgraded = re.sub(r"\ball\b", "some", text, count=1, flags=re.IGNORECASE)
            if downgraded == text:
                downgraded = "The universal conclusion should be downgraded; only a weaker existential claim may follow."
            return (
                downgraded,
                "A universal claim is too strong when the active support contains only an existential premise.",
                -0.5,
            )
        if issue_kind == "unsupported_conclusion":
            return (
                "The premises do not provide enough support for that conclusion.",
                "Unsupported claims should relax to insufficiency unless a missing premise is added.",
                -0.35,
            )
        if issue_kind == "contradiction":
            return (
                "The premise set contains a contradiction, so no stable conclusion follows without resolving it.",
                "Contradictory claims should be surfaced as graph instability rather than forced into an answer.",
                -0.55,
            )
        if issue_kind == "missing_premise":
            return (
                "Not enough information; more premises are needed before deriving the conclusion.",
                "The conclusion node lacks incoming support edges.",
                -0.4,
            )
        if issue_kind == "circular_reasoning":
            return (
                "Replace the circular step with independent premise support.",
                "Self-supporting cycles do not reduce tension in this toy CIG.",
                -0.45,
            )
        if issue_kind == "overconfidence":
            return (
                re.sub(
                    r"\bdefinitely\b",
                    "may",
                    re.sub(
                        r"\bcertainly\b",
                        "may",
                        re.sub(r"\bobviously\b", "possibly", text, flags=re.IGNORECASE),
                        flags=re.IGNORECASE,
                    ),
                    flags=re.IGNORECASE,
                ),
                "Surface confidence should match graph support.",
                -0.2,
            )
        return (
            "Review this step and add support or weaken the claim.",
            "Generic relaxation for unresolved high-tension issue.",
            -0.1,
        )

    def _answer_from_repair(self, chain: ReasoningChain, repair: RepairSuggestion) -> str:
        proposed = repair.proposed_text.strip()
        lower = proposed.lower()
        if "not provide enough support" in lower or "more premises are needed" in lower:
            return "Not enough information."
        if "contradiction" in lower:
            return "Contradiction detected; no stable answer follows."
        if proposed.lower().startswith("therefore "):
            return proposed[10:].strip()
        if repair.target_step_id.startswith("s"):
            return proposed
        return chain.final_answer

    def _dependencies_after_repair(self, step: ReasoningStep, repair: RepairSuggestion) -> List[str]:
        if repair.issue_kind == "circular_reasoning":
            return [dep for dep in step.dependencies if dep != step.step_id]
        return step.dependencies
