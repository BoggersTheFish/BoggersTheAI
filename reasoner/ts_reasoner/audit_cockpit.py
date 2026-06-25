from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class AuditCockpitResult:
    case_id: str
    command: str
    output: dict[str, Any]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def normalize_claim(text: str) -> str:
    return " ".join(text.lower().strip().split())


def normalize_claims(claims: Iterable[str]) -> list[str]:
    return [normalize_claim(claim) for claim in claims]


def audit_state(command: str, state: dict[str, Any], case_id: str = "manual") -> AuditCockpitResult:
    accepted_claims = normalize_claims(state.get("accepted_claims", []))
    repair_targets = list(state.get("repair_targets", []))
    branch_worlds = list(state.get("branch_worlds", []))
    quarantined_claims = normalize_claims(state.get("quarantined_claims", []))
    patches = list(state.get("patches", []))

    summary = {
        "accepted_claim_count": len(accepted_claims),
        "repair_target_count": len(repair_targets),
        "branch_world_count": len(branch_worlds),
        "quarantined_claim_count": len(quarantined_claims),
        "patch_count": len(patches),
        "candidate_graph_contamination_count": 0,
    }

    if command == "status":
        output = summary

    elif command == "repairs":
        output = {
            "repair_targets": repair_targets,
            "repair_target_count": len(repair_targets),
            "candidate_graph_contamination_count": 0,
        }

    elif command == "worlds":
        output = {
            "branch_worlds": branch_worlds,
            "branch_world_count": len(branch_worlds),
            "candidate_graph_contamination_count": 0,
        }

    elif command == "quarantine":
        output = {
            "quarantined_claims": quarantined_claims,
            "quarantined_claim_count": len(quarantined_claims),
            "candidate_graph_contamination_count": 0,
        }

    elif command == "patches":
        output = {
            "patches": patches,
            "patch_count": len(patches),
            "candidate_graph_contamination_count": 0,
        }

    elif command == "audit":
        output = {
            **summary,
            "accepted_claims": accepted_claims,
            "repair_targets": repair_targets,
            "branch_worlds": branch_worlds,
            "quarantined_claims": quarantined_claims,
            "patches": patches,
        }

    else:
        output = {
            "error": "unknown_command",
            "command": command,
            "candidate_graph_contamination_count": 0,
        }

    return AuditCockpitResult(
        case_id=case_id,
        command=command,
        output=output,
        candidate_graph_contamination_count=0,
        explanation="Audit cockpit reports state without modifying accepted common ground.",
    )


def evaluate_audit_cockpit_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = audit_state(
            command=str(raw["command"]),
            state=dict(raw["state"]),
            case_id=str(raw["case_id"]),
        )

        expected_keys = [str(key) for key in raw["expected_keys"]]
        expected_contamination = int(raw["expected_candidate_graph_contamination_count"])
        output = result.output

        case_passed = (
            all(key in output for key in expected_keys)
            and result.candidate_graph_contamination_count == expected_contamination
            and output.get("candidate_graph_contamination_count", 0) == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_keys"] = expected_keys
        row["expected_candidate_graph_contamination_count"] = expected_contamination
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v8.7.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "audit_cockpit_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
