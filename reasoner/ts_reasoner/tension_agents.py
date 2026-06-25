"""Coordinated tension-state agents for the v0.4 trace surface."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

from .types import CIGCheck, ReasoningChain, TensionAgentSignal, TensionScore, to_jsonable


DEFAULT_COUPLING_MATRIX: Dict[str, Dict[str, float]] = {
    "logic": {"repair": 0.9, "goal": 0.7},
    "goal": {"repair": 0.6, "logic": 0.2},
    "repair": {"goal": 0.2},
    "compression": {"goal": 0.4, "repair": 0.2},
}


class BaseTensionAgent:
    """Interface for deterministic constraint-specialist tension agents."""

    channel = "base"
    shares_with: Sequence[str] = ()

    def evaluate(self, chain: ReasoningChain, cig: CIGCheck, score: TensionScore) -> TensionAgentSignal:
        raise NotImplementedError

    def _issue_steps(self, score: TensionScore, kinds: set[str] | None = None) -> List[str]:
        return [
            issue.step_id
            for issue in score.issues
            if kinds is None or issue.kind in kinds
        ]

    def _issue_tension(self, score: TensionScore, kinds: set[str]) -> float:
        mass = sum(issue.severity for issue in score.issues if issue.kind in kinds)
        return round(min(1.0, mass), 4)


class LogicTensionAgent(BaseTensionAgent):
    channel = "logic"
    shares_with = ("repair", "goal")
    issue_kinds = {
        "contradiction",
        "unsupported_conclusion",
        "circular_reasoning",
        "quantifier_jump",
        "missing_premise",
    }

    def evaluate(self, chain: ReasoningChain, cig: CIGCheck, score: TensionScore) -> TensionAgentSignal:
        tension = self._issue_tension(score, self.issue_kinds)
        ops = ["CHECK_ENTAILMENT"] if tension else []
        if any(issue.kind in {"contradiction", "quantifier_jump"} for issue in score.issues):
            ops.append("LOCALIZE_FAILURE")
        if any(issue.kind == "missing_premise" for issue in score.issues):
            ops.append("REQUEST_PREMISE")
        return TensionAgentSignal(
            channel=self.channel,
            tension=tension,
            suspect_edges=self._issue_steps(score, self.issue_kinds),
            suggested_ops=ops,
            confidence=round(0.5 + min(0.49, tension * 0.45), 4) if tension else 0.9,
            shares_with=list(self.shares_with),
        )


class GoalTensionAgent(BaseTensionAgent):
    channel = "goal"
    shares_with = ("repair", "logic")

    def evaluate(self, chain: ReasoningChain, cig: CIGCheck, score: TensionScore) -> TensionAgentSignal:
        unresolved = score.global_tension
        if "not enough information" in chain.final_answer.lower() and not score.issues:
            unresolved = 0.0
        target = [chain.steps[-1].step_id] if chain.steps and unresolved else []
        ops = ["VERIFY_GOAL_SUPPORT"] if unresolved else []
        if unresolved >= 0.35:
            ops.append("LOCALIZE_FAILURE")
        return TensionAgentSignal(
            channel=self.channel,
            tension=round(unresolved, 4),
            suspect_edges=target,
            suggested_ops=ops,
            confidence=round(0.6 + min(0.35, unresolved * 0.35), 4) if unresolved else 0.85,
            shares_with=list(self.shares_with),
        )


class RepairTensionAgent(BaseTensionAgent):
    channel = "repair"
    shares_with = ("goal",)
    repairable_kinds = {
        "contradiction",
        "unsupported_conclusion",
        "circular_reasoning",
        "quantifier_jump",
        "missing_premise",
        "overconfidence",
    }

    def evaluate(self, chain: ReasoningChain, cig: CIGCheck, score: TensionScore) -> TensionAgentSignal:
        repair_mass = self._issue_tension(score, self.repairable_kinds)
        ops = []
        if repair_mass:
            ops.append("REPAIR_STEP")
        if any(issue.kind in {"quantifier_jump", "unsupported_conclusion"} for issue in score.issues):
            ops.append("SEARCH_ALTERNATIVE_RULE")
        if any(issue.kind == "contradiction" for issue in score.issues):
            ops.append("SPLIT_CONFLICTING_CLAIMS")
        return TensionAgentSignal(
            channel=self.channel,
            tension=repair_mass,
            suspect_edges=self._issue_steps(score, self.repairable_kinds),
            suggested_ops=ops,
            confidence=round(0.55 + min(0.4, repair_mass * 0.4), 4) if repair_mass else 0.8,
            shares_with=list(self.shares_with),
        )


class CompressionTensionAgent(BaseTensionAgent):
    channel = "compression"
    shares_with = ("goal", "repair")

    def evaluate(self, chain: ReasoningChain, cig: CIGCheck, score: TensionScore) -> TensionAgentSignal:
        repeated_claims = [
            claim
            for claim, count in Counter(claim.normalized for claim in cig.claims).items()
            if count > 1 and claim
        ]
        claim_source_ids = {claim.source_step_id for claim in cig.claims}
        dependency_free_nonpremises = [
            step.step_id
            for step in chain.steps
            if step.kind != "premise" and not step.dependencies and step.step_id in claim_source_ids and len(chain.steps) > 1
        ]
        bloat = 0.0
        bloat += min(0.45, 0.15 * len(repeated_claims))
        bloat += min(0.35, 0.1 * len(dependency_free_nonpremises))
        if len(chain.steps) > max(3, len(chain.premises) + 2):
            bloat += min(0.2, 0.04 * (len(chain.steps) - len(chain.premises) - 2))
        tension = round(min(1.0, bloat), 4)
        targets = dependency_free_nonpremises or [claim.source_step_id for claim in cig.claims if claim.normalized in repeated_claims]
        return TensionAgentSignal(
            channel=self.channel,
            tension=tension,
            suspect_edges=targets,
            suggested_ops=["COMPRESS_TRACE", "DEDUP_CLAIMS"] if tension else [],
            confidence=round(0.55 + min(0.35, tension * 0.35), 4) if tension else 0.75,
            shares_with=list(self.shares_with),
        )


class TensionCoordinator:
    """Combine specialist signals into a propagated tension field."""

    def __init__(
        self,
        agents: Sequence[BaseTensionAgent] | None = None,
        coupling_matrix: Mapping[str, Mapping[str, float]] | None = None,
    ) -> None:
        self.agents = list(agents) if agents is not None else [
            LogicTensionAgent(),
            GoalTensionAgent(),
            RepairTensionAgent(),
            CompressionTensionAgent(),
        ]
        self.coupling_matrix = {
            source: dict(targets)
            for source, targets in (coupling_matrix or DEFAULT_COUPLING_MATRIX).items()
        }

    @classmethod
    def from_json(cls, path: str | Path) -> "TensionCoordinator":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        matrix = payload.get("coupling_matrix", payload)
        return cls(coupling_matrix=matrix)

    def to_json(self, path: str | Path, metadata: dict[str, object] | None = None) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "model_type": "residual_coupling_matrix",
            "coupling_matrix": self.coupling_matrix,
            "metadata": metadata or {},
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    def coordinate(self, chain: ReasoningChain, cig: CIGCheck, score: TensionScore) -> Dict[str, object]:
        signals = [agent.evaluate(chain, cig, score) for agent in self.agents]
        raw = {signal.channel: signal.tension for signal in signals}
        propagated = dict(raw)
        for source, targets in self.coupling_matrix.items():
            source_tension = raw.get(source, 0.0)
            for target, weight in targets.items():
                propagated[target] = propagated.get(target, 0.0) + source_tension * weight
        coordinated = {channel: round(min(1.0, value), 4) for channel, value in propagated.items()}
        return {
            "agents": [to_jsonable(signal) for signal in signals],
            "coupling_matrix": self.coupling_matrix,
            "raw_tensions": raw,
            "coordinated_tensions": coordinated,
            "selected_next_op": self._select_next_op(signals, coordinated),
            "target": self._select_target(signals, coordinated),
        }

    def _select_next_op(self, signals: Sequence[TensionAgentSignal], coordinated: Mapping[str, float]) -> str:
        if not coordinated:
            return "ACCEPT_TRACE"
        active_channel, active_tension = max(coordinated.items(), key=lambda item: (item[1], item[0]))
        if active_tension <= 0.0:
            return "ACCEPT_TRACE"
        channel_signals = [signal for signal in signals if signal.channel == active_channel]
        if channel_signals and channel_signals[0].suggested_ops:
            return channel_signals[0].suggested_ops[0]
        return {
            "logic": "CHECK_ENTAILMENT",
            "goal": "VERIFY_GOAL_SUPPORT",
            "repair": "REPAIR_STEP",
            "compression": "COMPRESS_TRACE",
        }.get(active_channel, "LOCALIZE_FAILURE")

    def _select_target(self, signals: Sequence[TensionAgentSignal], coordinated: Mapping[str, float]) -> str | None:
        if not coordinated:
            return None
        active_channel, active_tension = max(coordinated.items(), key=lambda item: (item[1], item[0]))
        if active_tension <= 0.0:
            return None
        for signal in signals:
            if signal.channel == active_channel and signal.suspect_edges:
                return signal.suspect_edges[0]
        for signal in signals:
            if signal.suspect_edges:
                return signal.suspect_edges[0]
        return None
