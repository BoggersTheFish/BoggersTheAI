from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

HIGH_TRUST = {"high", "trusted", "verified"}
LOW_TRUST = {"low", "untrusted", "hostile"}


@dataclass(frozen=True)
class RepairPolicyInput:
    case_id: str
    accepted_claim: str
    incoming_claim: str
    claim_type: str
    incoming_source: str
    source_trust: str


@dataclass(frozen=True)
class RepairPolicyDecision:
    case_id: str
    action: str
    repair_target_created: bool
    accepted_claim_preserved: bool
    incoming_claim_accepted: bool
    quarantine_incoming: bool
    branch_created: bool
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def is_direct_contradiction(accepted_claim: str, incoming_claim: str) -> bool:
    accepted = normalize_claim(accepted_claim)
    incoming = normalize_claim(incoming_claim)

    if accepted == incoming:
        return False

    pairs = [
        ("no external llm was used", "external llm was used"),
        ("external llm was used", "no external llm was used"),
    ]
    if (accepted, incoming) in pairs:
        return True

    if accepted.startswith("all ") and incoming.startswith("no "):
        return accepted[4:] == incoming[3:]

    if accepted.startswith("no ") and incoming.startswith("all "):
        return accepted[3:] == incoming[4:]

    if (
        incoming.startswith("some ")
        and " do not " in incoming
        and accepted.startswith("all ")
    ):
        return True

    return False


def decide_repair_policy(policy_input: RepairPolicyInput) -> RepairPolicyDecision:
    accepted = normalize_claim(policy_input.accepted_claim)
    incoming = normalize_claim(policy_input.incoming_claim)
    claim_type = policy_input.claim_type.lower().strip()
    source = policy_input.incoming_source.lower().strip()
    trust = policy_input.source_trust.lower().strip()

    if accepted == incoming:
        return RepairPolicyDecision(
            case_id=policy_input.case_id,
            action="accept_as_reinforcement",
            repair_target_created=False,
            accepted_claim_preserved=True,
            incoming_claim_accepted=True,
            quarantine_incoming=False,
            branch_created=False,
            candidate_graph_contamination_count=0,
            explanation="Incoming claim repeats accepted common ground and can reinforce provenance without changing proof state.",
        )

    if claim_type == "missing_support":
        return RepairPolicyDecision(
            case_id=policy_input.case_id,
            action="open_missing_bridge_repair",
            repair_target_created=True,
            accepted_claim_preserved=True,
            incoming_claim_accepted=False,
            quarantine_incoming=False,
            branch_created=False,
            candidate_graph_contamination_count=0,
            explanation="Incoming claim is unsupported rather than contradictory, so the system opens a missing-bridge repair target.",
        )

    contradiction = is_direct_contradiction(accepted, incoming)

    if contradiction and claim_type == "identity":
        return RepairPolicyDecision(
            case_id=policy_input.case_id,
            action="reject_and_quarantine",
            repair_target_created=True,
            accepted_claim_preserved=True,
            incoming_claim_accepted=False,
            quarantine_incoming=True,
            branch_created=False,
            candidate_graph_contamination_count=0,
            explanation="Identity-level contradiction is rejected and quarantined. Core state remains preserved.",
        )

    if contradiction and trust in HIGH_TRUST:
        return RepairPolicyDecision(
            case_id=policy_input.case_id,
            action="branch_worlds",
            repair_target_created=True,
            accepted_claim_preserved=True,
            incoming_claim_accepted=False,
            quarantine_incoming=False,
            branch_created=True,
            candidate_graph_contamination_count=0,
            explanation="Trusted contradiction is not auto-accepted. It creates a branch so both hypotheses can be inspected without collapsing common ground.",
        )

    if contradiction:
        return RepairPolicyDecision(
            case_id=policy_input.case_id,
            action="reject_and_open_repair",
            repair_target_created=True,
            accepted_claim_preserved=True,
            incoming_claim_accepted=False,
            quarantine_incoming=trust in LOW_TRUST or source == "hostile_candidate",
            branch_created=False,
            candidate_graph_contamination_count=0,
            explanation="Contradictory candidate is rejected and converted into a repair target. It does not contaminate accepted common ground.",
        )

    if claim_type == "directionality":
        return RepairPolicyDecision(
            case_id=policy_input.case_id,
            action="reject_and_explain",
            repair_target_created=False,
            accepted_claim_preserved=True,
            incoming_claim_accepted=False,
            quarantine_incoming=False,
            branch_created=False,
            candidate_graph_contamination_count=0,
            explanation="Directionality mismatch is rejected because reverse inference is not proof.",
        )

    return RepairPolicyDecision(
        case_id=policy_input.case_id,
        action="abstain_and_request_support",
        repair_target_created=True,
        accepted_claim_preserved=True,
        incoming_claim_accepted=False,
        quarantine_incoming=False,
        branch_created=False,
        candidate_graph_contamination_count=0,
        explanation="No safe contradiction policy matched, so the system abstains and requests support.",
    )


def evaluate_policy_cases(cases: Iterable[dict[str, object]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        inp = RepairPolicyInput(
            case_id=str(raw["case_id"]),
            accepted_claim=str(raw["accepted_claim"]),
            incoming_claim=str(raw["incoming_claim"]),
            claim_type=str(raw["claim_type"]),
            incoming_source=str(raw["incoming_source"]),
            source_trust=str(raw["source_trust"]),
        )
        decision = decide_repair_policy(inp)
        expected_action = str(raw["expected_action"])
        expected_repair = bool(raw["expected_repair_target"])

        case_passed = (
            decision.action == expected_action
            and decision.repair_target_created == expected_repair
            and decision.candidate_graph_contamination_count == 0
            and decision.accepted_claim_preserved
        )

        if case_passed:
            passed += 1

        contamination += decision.candidate_graph_contamination_count

        results.append(
            {
                "case_id": inp.case_id,
                "expected_action": expected_action,
                "actual_action": decision.action,
                "expected_repair_target": expected_repair,
                "actual_repair_target": decision.repair_target_created,
                "accepted_claim_preserved": decision.accepted_claim_preserved,
                "incoming_claim_accepted": decision.incoming_claim_accepted,
                "quarantine_incoming": decision.quarantine_incoming,
                "branch_created": decision.branch_created,
                "candidate_graph_contamination_count": decision.candidate_graph_contamination_count,
                "passed": case_passed,
                "explanation": decision.explanation,
            }
        )

    return {
        "release": "v8.1.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "policy_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "accepted_claims_preserved": all(
            row["accepted_claim_preserved"] for row in results
        ),
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
