from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


STATE_CHANGING_PATCHES = {
    "claim_added",
    "repair_resolved",
    "pack_imported",
}

VERIFIER_REQUIRED_PATCHES = {
    "claim_added",
    "repair_resolved",
}


@dataclass(frozen=True)
class ReasoningPatch:
    patch_id: str
    case_id: str
    patch_type: str
    before_claims: list[str]
    after_claims: list[str]
    payload: dict[str, Any]
    state_changed: bool
    requires_verifier_support: bool
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def normalize_claims(claims: Iterable[str]) -> list[str]:
    return [normalize_claim(claim) for claim in claims]


def make_reasoning_patch(case: dict[str, Any]) -> ReasoningPatch:
    case_id = str(case["case_id"])
    event_type = str(case["event_type"])

    before_claims = normalize_claims(case.get("before_claims", []))
    after_claims = normalize_claims(case.get("after_claims", []))
    payload = dict(case.get("payload", {}))

    state_changed = before_claims != after_claims or event_type in STATE_CHANGING_PATCHES
    requires_verifier_support = event_type in VERIFIER_REQUIRED_PATCHES

    if event_type == "claim_quarantined":
        state_changed = False
        requires_verifier_support = False

    if event_type == "repair_opened":
        state_changed = False
        requires_verifier_support = False

    if event_type == "world_branched":
        state_changed = False
        requires_verifier_support = False

    return ReasoningPatch(
        patch_id=f"patch__{case_id}",
        case_id=case_id,
        patch_type=event_type,
        before_claims=before_claims,
        after_claims=after_claims,
        payload=payload,
        state_changed=state_changed,
        requires_verifier_support=requires_verifier_support,
        candidate_graph_contamination_count=0,
        explanation="Reasoning patch records a typed state transition without treating candidate text as proof.",
    )


def evaluate_reasoning_patch_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        patch = make_reasoning_patch(raw)

        expected_patch_type = str(raw["expected_patch_type"])
        expected_state_changed = bool(raw["expected_state_changed"])
        expected_requires_verifier_support = bool(raw["expected_requires_verifier_support"])

        case_passed = (
            patch.patch_type == expected_patch_type
            and patch.state_changed == expected_state_changed
            and patch.requires_verifier_support == expected_requires_verifier_support
            and patch.candidate_graph_contamination_count == 0
        )

        if case_passed:
            passed += 1

        contamination += patch.candidate_graph_contamination_count

        row = patch.to_dict()
        row["expected_patch_type"] = expected_patch_type
        row["expected_state_changed"] = expected_state_changed
        row["expected_requires_verifier_support"] = expected_requires_verifier_support
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.6.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "reasoning_patch_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
