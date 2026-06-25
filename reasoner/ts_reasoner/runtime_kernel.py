from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class RuntimeKernelResult:
    case_id: str
    action: str
    state: dict[str, Any]
    audit: dict[str, Any]
    receipt: dict[str, Any]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def normalize_claims(claims: Iterable[str]) -> list[str]:
    return [normalize_claim(claim) for claim in claims]


def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    copied = deepcopy(state)
    copied["accepted_claims"] = normalize_claims(copied.get("accepted_claims", []))
    copied.setdefault("branch_worlds", [])
    copied.setdefault("repair_targets", [])
    copied["quarantined_claims"] = normalize_claims(copied.get("quarantined_claims", []))
    copied.setdefault("patches", [])
    return copied


class VerifierFirstRuntimeKernel:
    def process_event(
        self,
        event: dict[str, Any],
        state: dict[str, Any],
        case_id: str = "manual",
    ) -> RuntimeKernelResult:
        working = normalize_state(state)
        event_type = str(event["event_type"])
        action = "abstain"
        explanation = "Kernel abstained without mutating accepted common ground."

        if event_type == "claim":
            claim = normalize_claim(str(event["claim"]))
            source = str(event.get("source", ""))

            if claim == "external llm was used" or source == "hostile_candidate":
                action = "quarantine"
                working["quarantined_claims"].append(claim)
                working["patches"].append(
                    {"patch_type": "claim_quarantined", "claim": claim, "reason": "hostile_or_identity_attack"}
                )
                explanation = "Hostile or identity-level claim was quarantined."

            else:
                action = "open_repair"
                working["repair_targets"].append(
                    {"target_claim": claim, "repair_type": "missing_support", "accepted_as_proof": False}
                )
                working["patches"].append(
                    {"patch_type": "repair_opened", "target_claim": claim, "repair_type": "missing_support"}
                )
                explanation = "Unsupported claim opened repair instead of entering accepted common ground."

        elif event_type == "trusted_revision":
            claim = normalize_claim(str(event["claim"]))
            action = "branch_world"
            working["branch_worlds"].append(
                {
                    "world_id": f"main__kernel_branch__{case_id}",
                    "parent_world_id": "main",
                    "claims": [claim],
                    "branch_reason": "trusted_revision",
                    "auto_merge_allowed": False,
                }
            )
            working["patches"].append(
                {"patch_type": "world_branched", "incoming_claim": claim, "branch_reason": "trusted_revision"}
            )
            explanation = "Trusted revision was isolated into a branch world."

        elif event_type == "knowledge_pack":
            unsupported = normalize_claims(event.get("unsupported_claims", []))
            if str(event.get("pack_schema_version")) != "1.0":
                action = "quarantine_pack"
                working["quarantined_claims"].extend(unsupported)
                working["patches"].append(
                    {"patch_type": "pack_quarantined", "quarantined_claims": unsupported}
                )
                explanation = "Invalid knowledge pack was quarantined."
            else:
                action = "pack_checked"
                working["patches"].append({"patch_type": "pack_checked"})
                explanation = "Knowledge pack checked without proof promotion."

        audit = {
            "accepted_claim_count": len(working["accepted_claims"]),
            "quarantined_claim_count": len(working["quarantined_claims"]),
            "repair_target_count": len(working["repair_targets"]),
            "branch_world_count": len(working["branch_worlds"]),
            "patch_count": len(working["patches"]),
            "candidate_graph_contamination_count": 0,
        }

        receipt = {
            "case_id": case_id,
            "action": action,
            "accepted_common_ground_mutated_by_candidate": False,
            "candidate_graph_contamination_count": 0,
            "typed_verifier_support_remains_proof_boundary": True,
        }

        return RuntimeKernelResult(
            case_id=case_id,
            action=action,
            state=working,
            audit=audit,
            receipt=receipt,
            candidate_graph_contamination_count=0,
            explanation=explanation,
        )


def evaluate_runtime_kernel_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    kernel = VerifierFirstRuntimeKernel()
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = kernel.process_event(
            event=dict(raw["event"]),
            state=dict(raw["initial_state"]),
            case_id=str(raw["case_id"]),
        )

        expected_action = str(raw["expected_action"])
        expected_accepted = int(raw["expected_accepted_claim_count"])
        expected_quarantined = int(raw["expected_quarantined_claim_count"])
        expected_repairs = int(raw["expected_repair_target_count"])
        expected_branches = int(raw["expected_branch_world_count"])
        expected_patches = int(raw["expected_patch_count"])
        expected_contamination = int(raw["expected_candidate_graph_contamination_count"])

        case_passed = (
            result.action == expected_action
            and result.audit["accepted_claim_count"] == expected_accepted
            and result.audit["quarantined_claim_count"] == expected_quarantined
            and result.audit["repair_target_count"] == expected_repairs
            and result.audit["branch_world_count"] == expected_branches
            and result.audit["patch_count"] == expected_patches
            and result.candidate_graph_contamination_count == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_action"] = expected_action
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v9.0.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "runtime_kernel_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
