from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ts_reasoner.runtime_kernel import VerifierFirstRuntimeKernel


@dataclass(frozen=True)
class RuntimeReplayResult:
    case_id: str
    actions: list[str]
    final_state: dict[str, Any]
    audit: dict[str, Any]
    receipts: list[dict[str, Any]]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def replay_events(
    case_id: str,
    initial_state: dict[str, Any],
    events: list[dict[str, Any]],
) -> RuntimeReplayResult:
    kernel = VerifierFirstRuntimeKernel()
    state = deepcopy(initial_state)
    actions: list[str] = []
    receipts: list[dict[str, Any]] = []
    contamination = 0

    for index, event in enumerate(events):
        result = kernel.process_event(
            event=event,
            state=state,
            case_id=f"{case_id}__event_{index}",
        )
        actions.append(result.action)
        receipts.append(result.receipt)
        state = result.state
        contamination += result.candidate_graph_contamination_count

    audit = {
        "accepted_claim_count": len(state.get("accepted_claims", [])),
        "quarantined_claim_count": len(state.get("quarantined_claims", [])),
        "repair_target_count": len(state.get("repair_targets", [])),
        "branch_world_count": len(state.get("branch_worlds", [])),
        "patch_count": len(state.get("patches", [])),
        "candidate_graph_contamination_count": contamination,
    }

    return RuntimeReplayResult(
        case_id=case_id,
        actions=actions,
        final_state=state,
        audit=audit,
        receipts=receipts,
        candidate_graph_contamination_count=contamination,
        explanation="Runtime replay processed an ordered event sequence through the verifier-first kernel.",
    )


def evaluate_runtime_replay_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = replay_events(
            case_id=str(raw["case_id"]),
            initial_state=dict(raw["initial_state"]),
            events=[dict(event) for event in raw["events"]],
        )

        expected_actions = [str(action) for action in raw["expected_actions"]]
        expected_accepted = int(raw["expected_accepted_claim_count"])
        expected_quarantined = int(raw["expected_quarantined_claim_count"])
        expected_repairs = int(raw["expected_repair_target_count"])
        expected_branches = int(raw["expected_branch_world_count"])
        expected_patches = int(raw["expected_patch_count"])
        expected_contamination = int(
            raw["expected_candidate_graph_contamination_count"]
        )

        case_passed = (
            result.actions == expected_actions
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
        row["expected_actions"] = expected_actions
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v9.2.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "runtime_replay_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
