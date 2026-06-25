"""Operation routing and bounded tension-control loops."""

from __future__ import annotations

from typing import Dict, List

from .cig_checker import CIGChecker
from .ranker import HeuristicTensionRanker
from .repair import TensionRepairer
from .tension_agents import TensionCoordinator
from .types import CIGCheck, ReasoningChain, ReasoningStep, RepairSuggestion, TensionScore


class OperationRouter:
    """Apply bounded state transitions selected by the tension coordinator."""

    def __init__(
        self,
        checker: CIGChecker | None = None,
        ranker: HeuristicTensionRanker | None = None,
        repairer: TensionRepairer | None = None,
        coordinator: TensionCoordinator | None = None,
    ) -> None:
        self.checker = checker or CIGChecker()
        self.ranker = ranker or HeuristicTensionRanker()
        self.repairer = repairer or TensionRepairer()
        self.coordinator = coordinator or TensionCoordinator()

    def run_once(
        self,
        chain: ReasoningChain,
        cig: CIGCheck,
        score: TensionScore,
        field: Dict[str, object],
    ) -> Dict[str, object]:
        op = str(field.get("selected_next_op", "ACCEPT_TRACE"))
        target = field.get("target")

        if op == "ACCEPT_TRACE":
            return self._stationary_transition("accepted", op, target, chain, cig, score, field)
        if op == "COMPRESS_TRACE":
            compressed_chain = self._compress_trace(chain)
            if compressed_chain is chain:
                return self._stationary_transition("no_compression_available", op, target, chain, cig, score, field)
            return self._transition_from_chain(op, target, chain, cig, score, field, compressed_chain, "compressed")
        if op == "LOCALIZE_FAILURE":
            return self._stationary_transition("localized", op, target, chain, cig, score, field)
        if op == "VERIFY_GOAL_SUPPORT":
            status = "goal_verified" if score.global_tension == 0.0 else "goal_unstable"
            return self._stationary_transition(status, op, target, chain, cig, score, field)

        return self._repair_transition(op, target, chain, cig, score, field)

    def run_until_stable(
        self,
        chain: ReasoningChain,
        max_steps: int = 5,
    ) -> Dict[str, object]:
        current_chain = chain
        current_cig = self.checker.check(current_chain)
        current_score = self.ranker.score(current_chain, current_cig)
        current_field = self.coordinator.coordinate(current_chain, current_cig, current_score)
        initial_snapshot = self._snapshot(current_score, current_field)
        cycles: List[Dict[str, object]] = []
        status = "max_steps_reached"

        for cycle_index in range(1, max_steps + 1):
            transition = self.run_once(current_chain, current_cig, current_score, current_field)
            cycle_trace = self.transition_trace(transition)
            cycle_trace["cycle"] = cycle_index
            cycles.append(cycle_trace)
            current_chain = transition["chain"]
            current_cig = transition["cig"]
            current_score = transition["score"]
            current_field = transition["field"]
            status = str(transition["status"])
            if status in {"accepted", "no_repair_available", "no_compression_available", "repair_rejected", "goal_unstable"}:
                break
            if transition["after"]["global_tension"] <= 0.0 and transition["after"]["selected_next_op"] == "ACCEPT_TRACE":
                status = "settled"
                break

        return {
            "status": status,
            "cycles": cycles,
            "cycle_count": len(cycles),
            "initial": initial_snapshot,
            "final": self._snapshot(current_score, current_field),
            "chain": current_chain,
            "cig": current_cig,
            "score": current_score,
            "field": current_field,
            "settled": current_score.global_tension <= 0.0 and current_field["selected_next_op"] == "ACCEPT_TRACE",
        }

    def transition_trace(self, transition: dict) -> dict:
        return {
            "status": transition["status"],
            "selected_op": transition["selected_op"],
            "target": transition["target"],
            "repair": self._jsonable_repair(transition["repair"]),
            "before": transition["before"],
            "after": transition["after"],
            "residual": transition["residual"],
        }

    def _repair_transition(
        self,
        op: str,
        target: object,
        chain: ReasoningChain,
        cig: CIGCheck,
        score: TensionScore,
        field: Dict[str, object],
    ) -> Dict[str, object]:
        repairs = self.repairer.suggest(chain, score)
        selected_repair = self._select_repair(repairs, target)
        if selected_repair is None:
            return self._stationary_transition("no_repair_available", op, target, chain, cig, score, field)
        repaired_chain = self.repairer.apply(chain, selected_repair)
        return self._transition_from_chain(op, target, chain, cig, score, field, repaired_chain, "repaired", selected_repair)

    def _transition_from_chain(
        self,
        op: str,
        target: object,
        chain: ReasoningChain,
        cig: CIGCheck,
        score: TensionScore,
        field: Dict[str, object],
        new_chain: ReasoningChain,
        success_status: str,
        repair: RepairSuggestion | None = None,
    ) -> Dict[str, object]:
        new_cig = self.checker.check(new_chain)
        new_score = self.ranker.score(new_chain, new_cig)
        new_field = self.coordinator.coordinate(new_chain, new_cig, new_score)
        accepted = new_score.global_tension <= score.global_tension
        return {
            "status": success_status if accepted else f"{success_status}_rejected",
            "selected_op": op,
            "target": target,
            "repair": repair,
            "before": self._snapshot(score, field),
            "after": self._snapshot(new_score, new_field),
            "residual": self._residual(field, new_field),
            "chain": new_chain if accepted else chain,
            "cig": new_cig if accepted else cig,
            "score": new_score if accepted else score,
            "field": new_field if accepted else field,
        }

    def _stationary_transition(
        self,
        status: str,
        op: str,
        target: object,
        chain: ReasoningChain,
        cig: CIGCheck,
        score: TensionScore,
        field: Dict[str, object],
    ) -> Dict[str, object]:
        return {
            "status": status,
            "selected_op": op,
            "target": target,
            "repair": None,
            "before": self._snapshot(score, field),
            "after": self._snapshot(score, field),
            "residual": self._residual(field, field),
            "chain": chain,
            "cig": cig,
            "score": score,
            "field": field,
        }

    def _compress_trace(self, chain: ReasoningChain) -> ReasoningChain:
        seen = set()
        seen_claims = set()
        compressed_steps: List[ReasoningStep] = []
        removed = set()
        cig = self.checker.check(chain)
        has_claims = bool(cig.claims)
        claims_by_step: Dict[str, set[str]] = {}
        for claim in cig.claims:
            claims_by_step.setdefault(claim.source_step_id, set()).add(claim.normalized)
        for step in chain.steps:
            signature = (step.kind, step.text.strip().lower(), tuple(step.dependencies))
            step_claims = claims_by_step.get(step.step_id, set())
            redundant_claim = bool(step_claims) and step_claims.issubset(seen_claims)
            if step.kind != "premise" and (
                signature in seen
                or redundant_claim
                or (not step.dependencies and not has_claims)
            ):
                removed.add(step.step_id)
                continue
            seen.add(signature)
            seen_claims.update(step_claims)
            compressed_steps.append(step)
        if not removed:
            return chain
        rewritten_steps = [
            ReasoningStep(
                step_id=step.step_id,
                text=step.text,
                kind=step.kind,
                dependencies=[dep for dep in step.dependencies if dep not in removed],
                confidence=step.confidence,
            )
            for step in compressed_steps
        ]
        return ReasoningChain(
            chain_id=f"{chain.chain_id}:compressed",
            question=chain.question,
            premises=chain.premises,
            steps=rewritten_steps,
            final_answer=chain.final_answer,
            generator=chain.generator,
        )

    def _select_repair(
        self,
        repairs: List[RepairSuggestion],
        target: object,
    ) -> RepairSuggestion | None:
        if target is not None:
            matching = [repair for repair in repairs if repair.target_step_id == target]
            if matching:
                return min(matching, key=lambda repair: repair.expected_tension_delta)
        return repairs[0] if repairs else None

    def _snapshot(self, score: TensionScore, field: Dict[str, object]) -> Dict[str, object]:
        return {
            "global_tension": score.global_tension,
            "stability": score.stability,
            "issue_kinds": [issue.kind for issue in score.issues],
            "coordinated_tensions": field["coordinated_tensions"],
            "selected_next_op": field["selected_next_op"],
            "target": field["target"],
        }

    def _jsonable_repair(self, repair: RepairSuggestion | None) -> dict | None:
        if repair is None:
            return None
        return {
            "repair_id": repair.repair_id,
            "target_step_id": repair.target_step_id,
            "issue_kind": repair.issue_kind,
            "original_text": repair.original_text,
            "proposed_text": repair.proposed_text,
            "rationale": repair.rationale,
            "expected_tension_delta": repair.expected_tension_delta,
            "status": repair.status,
        }

    def _residual(self, before: Dict[str, object], after: Dict[str, object]) -> Dict[str, float]:
        before_tensions = before.get("coordinated_tensions", {})
        after_tensions = after.get("coordinated_tensions", {})
        if not isinstance(before_tensions, dict) or not isinstance(after_tensions, dict):
            return {}
        channels = set(before_tensions) | set(after_tensions)
        return {
            channel: round(float(after_tensions.get(channel, 0.0)) - float(before_tensions.get(channel, 0.0)), 4)
            for channel in sorted(channels)
        }
