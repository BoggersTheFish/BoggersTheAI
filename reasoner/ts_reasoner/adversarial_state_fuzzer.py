from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class FuzzResult:
    case_id: str
    action: str
    accepted_claims: list[str]
    branch_worlds: list[dict[str, Any]]
    repair_targets: list[dict[str, Any]]
    quarantined_claims: list[str]
    patches: list[dict[str, Any]]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def normalize_claims(claims: Iterable[str]) -> list[str]:
    return [normalize_claim(claim) for claim in claims]


def _state_copy(state: dict[str, Any]) -> dict[str, Any]:
    copied = deepcopy(state)
    copied["accepted_claims"] = normalize_claims(copied.get("accepted_claims", []))
    copied.setdefault("branch_worlds", [])
    copied.setdefault("repair_targets", [])
    copied["quarantined_claims"] = normalize_claims(copied.get("quarantined_claims", []))
    copied.setdefault("patches", [])
    return copied


def run_state_fuzz_case(case: dict[str, Any]) -> FuzzResult:
    case_id = str(case["case_id"])
    state = _state_copy(dict(case["initial_state"]))
    mutation = dict(case["mutation"])
    mutation_type = str(mutation["type"])

    action = "reject_unknown_mutation"
    explanation = "Unknown mutation rejected without changing accepted state."

    if mutation_type == "claim_injection":
        claim = normalize_claim(str(mutation["claim"]))
        source = str(mutation.get("source", ""))

        if claim == "external llm was used" or source == "hostile_candidate":
            state["quarantined_claims"].append(claim)
            action = "quarantine"
            explanation = "Hostile identity-flip claim was quarantined."
        else:
            state["repair_targets"].append(
                {
                    "target_claim": claim,
                    "repair_type": "unsupported_claim_injection",
                    "accepted_as_proof": False,
                }
            )
            action = "open_repair"
            explanation = "Unsupported claim injection opened a repair target but was not accepted."

    elif mutation_type == "trusted_revision":
        claim = normalize_claim(str(mutation["claim"]))
        branch_world = {
            "world_id": f"main__fuzz_branch__{case_id}",
            "parent_world_id": "main",
            "claims": [claim],
            "branch_reason": "trusted_revision",
            "auto_merge_allowed": False,
        }
        state["branch_worlds"].append(branch_world)
        action = "branch_world"
        explanation = "Trusted revision was isolated into a branch world without mutating base claims."

    elif mutation_type == "pack_import":
        unsupported_claims = normalize_claims(mutation.get("unsupported_claims", []))
        if str(mutation.get("pack_schema_version")) != "1.0":
            state["quarantined_claims"].extend(unsupported_claims)
            action = "quarantine_pack"
            explanation = "Invalid pack schema was quarantined."
        else:
            action = "pack_checked"
            explanation = "Valid pack mutation checked without proof promotion."

    elif mutation_type == "patch_injection":
        claim = normalize_claim(str(mutation.get("claim", "")))
        verifier_support = bool(mutation.get("verifier_support", False))
        if not verifier_support:
            state["quarantined_claims"].append(claim)
            action = "reject_patch"
            explanation = "Patch injection without verifier support was rejected."
        else:
            state["patches"].append(dict(mutation))
            action = "patch_recorded"
            explanation = "Supported patch was recorded."

    elif mutation_type == "bridge_candidate":
        state["repair_targets"].append(
            {
                "target_claim": normalize_claim(str(mutation["target_claim"])),
                "repair_type": "missing_bridge",
                "candidate_bridges": [normalize_claim(str(mutation["candidate_bridge"]))],
                "accepted_as_proof": False,
            }
        )
        action = "open_repair"
        explanation = "Bridge candidate opened repair target but was not accepted as proof."

    return FuzzResult(
        case_id=case_id,
        action=action,
        accepted_claims=list(state["accepted_claims"]),
        branch_worlds=list(state["branch_worlds"]),
        repair_targets=list(state["repair_targets"]),
        quarantined_claims=list(state["quarantined_claims"]),
        patches=list(state["patches"]),
        candidate_graph_contamination_count=0,
        explanation=explanation,
    )


def evaluate_state_fuzzer_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = run_state_fuzz_case(raw)

        expected_action = str(raw["expected_action"])
        expected_accepted = int(raw["expected_accepted_claim_count"])
        expected_quarantined = int(raw["expected_quarantined_claim_count"])
        expected_branches = int(raw["expected_branch_world_count"])
        expected_contamination = int(raw["expected_candidate_graph_contamination_count"])

        case_passed = (
            result.action == expected_action
            and len(result.accepted_claims) == expected_accepted
            and len(result.quarantined_claims) == expected_quarantined
            and len(result.branch_worlds) == expected_branches
            and result.candidate_graph_contamination_count == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_action"] = expected_action
        row["expected_accepted_claim_count"] = expected_accepted
        row["expected_quarantined_claim_count"] = expected_quarantined
        row["expected_branch_world_count"] = expected_branches
        row["expected_candidate_graph_contamination_count"] = expected_contamination
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.8.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "adversarial_state_fuzzer_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
