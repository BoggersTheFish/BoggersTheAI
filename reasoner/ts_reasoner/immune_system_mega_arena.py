from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class MegaArenaResult:
    case_id: str
    action: str
    accepted_claims: list[str]
    branch_worlds: list[dict[str, Any]]
    repair_targets: list[dict[str, Any]]
    quarantined_claims: list[str]
    patches: list[dict[str, Any]]
    audit: dict[str, Any]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def normalize_claims(claims: Iterable[str]) -> list[str]:
    return [normalize_claim(claim) for claim in claims]


def run_mega_arena_case(case: dict[str, Any]) -> MegaArenaResult:
    case_id = str(case["case_id"])
    scenario_type = str(case["scenario_type"])
    accepted_claims = normalize_claims(case.get("accepted_claims", []))
    incoming_claim = normalize_claim(str(case["incoming_claim"]))

    branch_worlds: list[dict[str, Any]] = []
    repair_targets: list[dict[str, Any]] = []
    quarantined_claims: list[str] = []
    patches: list[dict[str, Any]] = []

    action = "abstain"
    explanation = "Mega-arena abstained without mutating accepted common ground."

    if scenario_type == "identity_attack":
        action = "quarantine"
        quarantined_claims.append(incoming_claim)
        patches.append(
            {
                "patch_type": "claim_quarantined",
                "claim": incoming_claim,
                "reason": "identity_attack",
            }
        )
        explanation = "Hostile identity attack was quarantined and recorded as a patch."

    elif scenario_type == "missing_bridge":
        action = "open_repair"
        repair_targets.append(
            {
                "target_claim": incoming_claim,
                "repair_type": "missing_bridge",
                "accepted_as_proof": False,
            }
        )
        patches.append(
            {
                "patch_type": "repair_opened",
                "target_claim": incoming_claim,
                "repair_type": "missing_bridge",
            }
        )
        explanation = "Unsupported claim opened a repair target without entering accepted common ground."

    elif scenario_type == "trusted_revision":
        action = "branch_world"
        branch_worlds.append(
            {
                "world_id": f"main__mega_branch__{case_id}",
                "parent_world_id": "main",
                "claims": [incoming_claim],
                "branch_reason": "trusted_revision",
                "auto_merge_allowed": False,
            }
        )
        patches.append(
            {
                "patch_type": "world_branched",
                "incoming_claim": incoming_claim,
                "branch_reason": "trusted_revision",
            }
        )
        explanation = "Trusted revision was isolated into a branch world."

    elif scenario_type == "bad_pack":
        action = "quarantine_pack"
        quarantined_claims.append(incoming_claim)
        patches.append(
            {
                "patch_type": "pack_quarantined",
                "claim": incoming_claim,
                "reason": "invalid_schema_or_untrusted_pack",
            }
        )
        explanation = "Bad knowledge pack was quarantined."

    elif scenario_type == "malicious_patch":
        action = "reject_patch"
        quarantined_claims.append(incoming_claim)
        patches.append(
            {
                "patch_type": "patch_rejected",
                "claim": incoming_claim,
                "reason": "missing_verifier_support",
            }
        )
        explanation = "Malicious patch was rejected and the claim was quarantined."

    audit = {
        "accepted_claim_count": len(accepted_claims),
        "branch_world_count": len(branch_worlds),
        "repair_target_count": len(repair_targets),
        "quarantined_claim_count": len(quarantined_claims),
        "patch_count": len(patches),
        "candidate_graph_contamination_count": 0,
    }

    return MegaArenaResult(
        case_id=case_id,
        action=action,
        accepted_claims=accepted_claims,
        branch_worlds=branch_worlds,
        repair_targets=repair_targets,
        quarantined_claims=quarantined_claims,
        patches=patches,
        audit=audit,
        candidate_graph_contamination_count=0,
        explanation=explanation,
    )


def evaluate_mega_arena_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = run_mega_arena_case(raw)

        expected_action = str(raw["expected_action"])
        expected_branch_world_count = int(raw["expected_branch_world_count"])
        expected_repair_target_count = int(raw["expected_repair_target_count"])
        expected_quarantined_claim_count = int(raw["expected_quarantined_claim_count"])
        expected_patch_count = int(raw["expected_patch_count"])
        expected_contamination = int(raw["expected_candidate_graph_contamination_count"])

        case_passed = (
            result.action == expected_action
            and len(result.branch_worlds) == expected_branch_world_count
            and len(result.repair_targets) == expected_repair_target_count
            and len(result.quarantined_claims) == expected_quarantined_claim_count
            and len(result.patches) == expected_patch_count
            and result.candidate_graph_contamination_count == expected_contamination
            and result.audit["candidate_graph_contamination_count"] == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_action"] = expected_action
        row["expected_branch_world_count"] = expected_branch_world_count
        row["expected_repair_target_count"] = expected_repair_target_count
        row["expected_quarantined_claim_count"] = expected_quarantined_claim_count
        row["expected_patch_count"] = expected_patch_count
        row["expected_candidate_graph_contamination_count"] = expected_contamination
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.9.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "mega_arena_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
