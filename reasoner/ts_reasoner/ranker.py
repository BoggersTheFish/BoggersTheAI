"""Heuristic tension scoring for candidate reasoning chains."""

from __future__ import annotations

from typing import Dict, List

from .cig_checker import CIGChecker
from .generator import extract_relations
from .proof_chain import has_universal_bridge
from .types import CIGCheck, ReasoningChain, TensionIssue, TensionScore


class HeuristicTensionRanker:
    """Score local and global instability in a reasoning chain."""

    def __init__(self) -> None:
        self.cig_checker = CIGChecker()

    def score(self, chain: ReasoningChain, cig_check: CIGCheck | None = None) -> TensionScore:
        cig = cig_check or self.cig_checker.check(chain)
        local: Dict[str, float] = {step.step_id: 0.0 for step in chain.steps}
        issues: List[TensionIssue] = []

        def add(step_id: str, kind: str, severity: float, message: str, evidence: List[str], suggestion: str) -> None:
            local[step_id] = min(1.0, local.get(step_id, 0.0) + severity)
            issues.append(
                TensionIssue(
                    issue_id=f"{chain.chain_id}:{len(issues) + 1}",
                    step_id=step_id,
                    kind=kind,
                    severity=severity,
                    message=message,
                    evidence=evidence,
                    suggestion=suggestion,
                )
            )

        self._check_contradictions(cig, add)
        self._check_unsupported_claims(cig, add)
        self._check_circularity(cig, add)
        self._check_quantifier_jumps(chain, add)
        self._check_missing_premises(chain, add)
        self._check_overconfidence(chain, add)

        issue_mass = sum(issue.severity for issue in issues)
        base = issue_mass / max(1, len(chain.steps))
        global_tension = round(min(1.0, base), 4)
        stability = round(1.0 - global_tension, 4)
        return TensionScore(
            chain_id=chain.chain_id,
            local_tension={key: round(value, 4) for key, value in local.items()},
            global_tension=global_tension,
            issues=issues,
            stability=stability,
        )

    def _check_contradictions(self, cig: CIGCheck, add) -> None:
        for pair in cig.contradiction_pairs:
            target = pair[-1].split(":")[0]
            add(
                target,
                "contradiction",
                0.55,
                "Claim conflicts with another claim in the chain.",
                pair,
                "Separate inconsistent premises or answer that the premise set is unstable.",
            )

    def _check_unsupported_claims(self, cig: CIGCheck, add) -> None:
        for claim_id in cig.unsupported_claim_ids:
            target = claim_id.split(":")[0]
            add(
                target,
                "unsupported_conclusion",
                0.35,
                "Conclusion claim is not supported by direct or transitive premise evidence.",
                [claim_id],
                "Downgrade the answer to insufficiency or add the missing premise.",
            )

    def _check_circularity(self, cig: CIGCheck, add) -> None:
        for step_id in cig.circular_step_ids:
            add(
                step_id,
                "circular_reasoning",
                0.45,
                "Step depends on itself or assumes its own conclusion.",
                [step_id],
                "Replace circular support with independent premise support.",
            )

    def _check_quantifier_jumps(self, chain: ReasoningChain, add) -> None:
        premise_relations = [relation for premise in chain.premises for relation in extract_relations(premise)]
        conclusion_steps = [step for step in chain.steps if step.kind == "conclusion"]
        for step in conclusion_steps:
            conclusion_relations = extract_relations(step.text)
            for conclusion in conclusion_relations:
                if conclusion.quantifier != "all":
                    continue
                has_some_source = any(
                    relation.quantifier == "some"
                    and relation.subject.lower() == conclusion.subject.lower()
                    for relation in premise_relations
                )
                has_all_support = self._has_all_support(premise_relations, conclusion.subject, conclusion.predicate)
                if has_some_source and not has_all_support:
                    add(
                        step.step_id,
                        "quantifier_jump",
                        0.5,
                        "Conclusion upgrades a some/existence premise into an all/universal claim.",
                        [relation.text for relation in premise_relations],
                        "Downgrade from 'all' to a weaker claim or answer that the universal does not follow.",
                    )

    def _check_missing_premises(self, chain: ReasoningChain, add) -> None:
        if chain.premises:
            return
        for step in chain.steps:
            if step.kind == "conclusion" and "not enough" not in step.text.lower():
                add(
                    step.step_id,
                    "missing_premise",
                    0.4,
                    "Conclusion was attempted without explicit premises.",
                    [step.text],
                    "Request premises or return an insufficiency answer.",
                )

    def _check_overconfidence(self, chain: ReasoningChain, add) -> None:
        markers = ("definitely", "certainly", "always", "obviously", "must be true")
        unsupported_targets = {issue.step_id for issue in self.score_unsupported_only(chain)}
        for step in chain.steps:
            lower = step.text.lower()
            if any(marker in lower for marker in markers) and (
                step.step_id in unsupported_targets or step.confidence >= 0.9
            ):
                add(
                    step.step_id,
                    "overconfidence",
                    0.2,
                    "Surface confidence is higher than the available support.",
                    [step.text],
                    "Use calibrated language tied to premise support.",
                )

    def score_unsupported_only(self, chain: ReasoningChain) -> List[TensionIssue]:
        cig = self.cig_checker.check(chain)
        return [
            TensionIssue(
                issue_id=f"{chain.chain_id}:unsupported:{claim_id}",
                step_id=claim_id.split(":")[0],
                kind="unsupported_conclusion",
                severity=0.0,
                message="",
            )
            for claim_id in cig.unsupported_claim_ids
        ]

    def _has_all_support(self, relations, subject: str, predicate: str) -> bool:
        return has_universal_bridge(relations, subject, predicate)
