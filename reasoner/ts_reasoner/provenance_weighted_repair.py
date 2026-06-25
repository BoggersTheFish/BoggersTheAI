from __future__ import annotations

from dataclasses import asdict, dataclass
from collections import defaultdict
from typing import Iterable


@dataclass(frozen=True)
class ProvenanceSource:
    source_id: str
    claim: str
    trust: float
    cluster: str
    role: str


@dataclass(frozen=True)
class ProvenanceRepairInput:
    case_id: str
    accepted_claim: str
    incoming_claim: str
    claim_type: str
    sources: list[ProvenanceSource]


@dataclass(frozen=True)
class ProvenanceRepairDecision:
    case_id: str
    winning_claim: str
    action: str
    accepted_claim_preserved: bool
    incoming_claim_accepted: bool
    dependency_penalty_applied: bool
    candidate_graph_contamination_count: int
    claim_scores: dict[str, float]
    cluster_counts: dict[str, int]
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def claim_is_revision(claim_type: str, source: ProvenanceSource) -> bool:
    return source.role in {"revision", "trusted_revision"} or claim_type == "revision"


def score_claims(sources: Iterable[ProvenanceSource]) -> tuple[dict[str, float], dict[str, int], bool]:
    cluster_counts: dict[str, int] = defaultdict(int)
    cluster_claims: dict[str, set[str]] = defaultdict(set)

    for src in sources:
        cluster_counts[src.cluster] += 1
        cluster_claims[src.cluster].add(normalize_claim(src.claim))

    penalty_applied = any(count > 1 for count in cluster_counts.values())

    scores: dict[str, float] = defaultdict(float)
    for src in sources:
        claim = normalize_claim(src.claim)
        cluster_size = cluster_counts[src.cluster]
        dependency_weight = 1.0 / cluster_size
        role_bonus = 0.25 if src.role == "authority" else 0.0
        scores[claim] += (float(src.trust) * dependency_weight) + role_bonus

    return dict(scores), dict(cluster_counts), penalty_applied


def decide_provenance_weighted_repair(inp: ProvenanceRepairInput) -> ProvenanceRepairDecision:
    accepted = normalize_claim(inp.accepted_claim)
    incoming = normalize_claim(inp.incoming_claim)

    scores, cluster_counts, dependency_penalty_applied = score_claims(inp.sources)

    if not scores:
        winning_claim = accepted
    else:
        winning_claim = max(scores.items(), key=lambda item: (item[1], item[0]))[0]

    incoming_sources = [src for src in inp.sources if normalize_claim(src.claim) == incoming]
    incoming_revision_trusted = any(src.trust >= 0.75 and src.role == "revision" for src in incoming_sources)

    if winning_claim == accepted and inp.claim_type == "identity":
        action = "reject_and_quarantine"
        incoming_accepted = False
        preserved = True
        explanation = "Canonical or higher-weight accepted identity claim wins; contradictory incoming claim is quarantined."

    elif winning_claim == accepted:
        action = "reject_and_open_repair"
        incoming_accepted = False
        preserved = True
        explanation = "Accepted claim has stronger independent provenance; incoming contradiction becomes a repair target."

    elif winning_claim == incoming and incoming_revision_trusted:
        action = "branch_worlds"
        incoming_accepted = False
        preserved = True
        explanation = "Trusted independent revision wins provenance pressure but is branched rather than directly accepted."

    elif winning_claim == incoming:
        action = "reject_and_open_repair"
        incoming_accepted = False
        preserved = True
        explanation = "Incoming claim has pressure but is still candidate data, so it opens repair rather than entering common ground."

    else:
        action = "abstain_and_request_support"
        incoming_accepted = False
        preserved = True
        explanation = "No safe provenance-weighted action resolved the conflict."

    return ProvenanceRepairDecision(
        case_id=inp.case_id,
        winning_claim=winning_claim,
        action=action,
        accepted_claim_preserved=preserved,
        incoming_claim_accepted=incoming_accepted,
        dependency_penalty_applied=dependency_penalty_applied,
        candidate_graph_contamination_count=0,
        claim_scores=scores,
        cluster_counts=cluster_counts,
        explanation=explanation,
    )


def evaluate_provenance_cases(cases: Iterable[dict[str, object]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        sources = [
            ProvenanceSource(
                source_id=str(src["source_id"]),
                claim=str(src["claim"]),
                trust=float(src["trust"]),
                cluster=str(src["cluster"]),
                role=str(src["role"]),
            )
            for src in raw["sources"]
        ]

        inp = ProvenanceRepairInput(
            case_id=str(raw["case_id"]),
            accepted_claim=str(raw["accepted_claim"]),
            incoming_claim=str(raw["incoming_claim"]),
            claim_type=str(raw["claim_type"]),
            sources=sources,
        )

        decision = decide_provenance_weighted_repair(inp)
        expected_winning_claim = normalize_claim(str(raw["expected_winning_claim"]))
        expected_action = str(raw["expected_action"])
        expected_dependency_penalty = bool(raw["expected_dependency_penalty_applied"])

        case_passed = (
            decision.winning_claim == expected_winning_claim
            and decision.action == expected_action
            and decision.dependency_penalty_applied == expected_dependency_penalty
            and decision.candidate_graph_contamination_count == 0
            and decision.accepted_claim_preserved
            and not decision.incoming_claim_accepted
        )

        if case_passed:
            passed += 1

        contamination += decision.candidate_graph_contamination_count

        row = decision.to_dict()
        row["expected_winning_claim"] = expected_winning_claim
        row["expected_action"] = expected_action
        row["expected_dependency_penalty_applied"] = expected_dependency_penalty
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.3.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "provenance_decision_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "accepted_claims_preserved": all(row["accepted_claim_preserved"] for row in results),
        "incoming_claims_not_auto_accepted": all(not row["incoming_claim_accepted"] for row in results),
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
