"""Feature extraction for candidate-chain tension ranking."""

from __future__ import annotations

from typing import Dict, Iterable

from .generator import extract_relations
from .types import CIGCheck, ReasoningChain, TensionIssue


FEATURE_NAMES = [
    "bias",
    "step_count",
    "premise_count",
    "claim_count",
    "dependency_edge_count",
    "contradiction_count",
    "unsupported_claim_count",
    "circular_step_count",
    "conclusion_all_count",
    "conclusion_some_count",
    "premise_some_count",
    "premise_no_count",
    "missing_premise_flag",
    "insufficiency_answer_flag",
    "contradiction_answer_flag",
    "direct_candidate_flag",
    "cautious_candidate_flag",
    "issue_contradiction_count",
    "issue_unsupported_conclusion_count",
    "issue_circular_reasoning_count",
    "issue_quantifier_jump_count",
    "issue_missing_premise_count",
    "issue_overconfidence_count",
]

CIG_FEATURE_NAMES = [
    "claim_count",
    "dependency_edge_count",
    "contradiction_count",
    "unsupported_claim_count",
    "circular_step_count",
]

ISSUE_KIND_FEATURE_NAMES = [
    "issue_contradiction_count",
    "issue_unsupported_conclusion_count",
    "issue_circular_reasoning_count",
    "issue_quantifier_jump_count",
    "issue_missing_premise_count",
    "issue_overconfidence_count",
]


def extract_chain_features(
    chain: ReasoningChain,
    cig_check: CIGCheck,
    issues: Iterable[TensionIssue] | None = None,
) -> Dict[str, float]:
    """Extract deterministic numeric features for learned ranker experiments."""
    conclusion_relations = [
        relation
        for step in chain.steps
        if step.kind == "conclusion"
        for relation in extract_relations(step.text)
    ]
    premise_relations = [
        relation
        for premise in chain.premises
        for relation in extract_relations(premise)
    ]
    final_lower = chain.final_answer.lower()
    issue_counts = {name: 0.0 for name in ISSUE_KIND_FEATURE_NAMES}
    for issue in issues or []:
        key = f"issue_{issue.kind}_count"
        if key in issue_counts:
            issue_counts[key] += 1.0
    return {
        "bias": 1.0,
        "step_count": float(len(chain.steps)),
        "premise_count": float(len(chain.premises)),
        "claim_count": float(len(cig_check.claims)),
        "dependency_edge_count": float(sum(len(step.dependencies) for step in chain.steps)),
        "contradiction_count": float(len(cig_check.contradiction_pairs)),
        "unsupported_claim_count": float(len(cig_check.unsupported_claim_ids)),
        "circular_step_count": float(len(cig_check.circular_step_ids)),
        "conclusion_all_count": float(sum(1 for relation in conclusion_relations if relation.quantifier == "all")),
        "conclusion_some_count": float(sum(1 for relation in conclusion_relations if relation.quantifier == "some")),
        "premise_some_count": float(sum(1 for relation in premise_relations if relation.quantifier == "some")),
        "premise_no_count": float(sum(1 for relation in premise_relations if relation.quantifier == "no")),
        "missing_premise_flag": 1.0 if not chain.premises else 0.0,
        "insufficiency_answer_flag": 1.0 if "not enough" in final_lower or "more information" in final_lower else 0.0,
        "contradiction_answer_flag": 1.0 if "contradiction" in final_lower else 0.0,
        "direct_candidate_flag": 1.0 if "direct" in chain.chain_id else 0.0,
        "cautious_candidate_flag": 1.0 if "cautious" in chain.chain_id else 0.0,
        **issue_counts,
    }


def mask_features(
    features: Dict[str, float],
    without_cig: bool = False,
    without_issue_kinds: bool = False,
) -> Dict[str, float]:
    masked = dict(features)
    if without_cig:
        for name in CIG_FEATURE_NAMES:
            masked[name] = 0.0
    if without_issue_kinds:
        for name in ISSUE_KIND_FEATURE_NAMES:
            masked[name] = 0.0
    return masked
