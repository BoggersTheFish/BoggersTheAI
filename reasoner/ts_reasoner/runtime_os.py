from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ts_reasoner.runtime_checkpoint_restore import build_checkpoint, restore_checkpoint
from ts_reasoner.runtime_policy_contracts import policy_contract_document
from ts_reasoner.runtime_recovery_drill import run_recovery_drill
from ts_reasoner.runtime_replay import replay_events

RUNTIME_OS_SCHEMA = "ts_reasoner_v10_runtime_session_v1"


@dataclass(frozen=True)
class RuntimeSessionResult:
    case_id: str
    schema: str
    actions: list[str]
    final_state: dict[str, Any]
    checkpoint: dict[str, Any]
    restored_state: dict[str, Any]
    receipt: dict[str, Any]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_runtime_session(
    case_id: str,
    initial_state: dict[str, Any],
    events: list[dict[str, Any]],
) -> RuntimeSessionResult:
    replay = replay_events(case_id=case_id, initial_state=initial_state, events=events)
    checkpoint_result = build_checkpoint(
        case_id=case_id, initial_state=initial_state, events=events
    )
    restored_state = restore_checkpoint(checkpoint_result.checkpoint)

    receipt = {
        "release": "v10.0.0",
        "schema": RUNTIME_OS_SCHEMA,
        "case_id": case_id,
        "runtime_replay_available": True,
        "tamper_evident_ledger_available": True,
        "checkpoint_restore_available": True,
        "policy_contracts_available": True,
        "unified_runtime_session": True,
        "checkpoint_valid": checkpoint_result.checkpoint_valid,
        "restore_valid": checkpoint_result.restore_valid,
        "candidate_graph_contamination_count": replay.candidate_graph_contamination_count,
        "generated_text_is_not_proof": True,
        "candidate_generation_is_not_proof": True,
        "model_confidence_is_not_proof": True,
        "typed_verifier_support_remains_proof_boundary": True,
    }

    return RuntimeSessionResult(
        case_id=case_id,
        schema=RUNTIME_OS_SCHEMA,
        actions=list(replay.actions),
        final_state=replay.final_state,
        checkpoint=checkpoint_result.checkpoint,
        restored_state=restored_state,
        receipt=receipt,
        candidate_graph_contamination_count=replay.candidate_graph_contamination_count,
        explanation="v10 packages replay, audit ledger, checkpoint, restore, contracts, and receipts into one runtime session.",
    )


def run_runtime_os_suite(
    case_id: str,
    initial_state: dict[str, Any],
    events: list[dict[str, Any]],
    continuation_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    session = run_runtime_session(
        case_id=case_id, initial_state=initial_state, events=events
    )
    recovery = run_recovery_drill(
        case_id=f"{case_id}__recovery",
        initial_state=initial_state,
        events=events,
        continuation_events=continuation_events or [],
    )

    return {
        "release": "v10.0.0",
        "schema": RUNTIME_OS_SCHEMA,
        "session": session.to_dict(),
        "policy_contracts": policy_contract_document(),
        "recovery": recovery.to_dict(),
        "all_gates_passed": (
            session.receipt["checkpoint_valid"] is True
            and session.receipt["restore_valid"] is True
            and recovery.corrupt_checkpoint_rejected
            and recovery.reordered_ledger_rejected
            and recovery.candidate_graph_contamination_count == 0
            and session.candidate_graph_contamination_count == 0
        ),
        "candidate_graph_contamination_count": (
            session.candidate_graph_contamination_count
            + recovery.candidate_graph_contamination_count
        ),
        "generated_text_is_not_proof": True,
        "candidate_generation_is_not_proof": True,
        "model_confidence_is_not_proof": True,
        "typed_verifier_support_remains_proof_boundary": True,
    }


def evaluate_runtime_os_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        suite = run_runtime_os_suite(
            case_id=str(raw["case_id"]),
            initial_state=dict(raw["initial_state"]),
            events=[dict(event) for event in raw["events"]],
            continuation_events=[
                dict(event) for event in raw.get("continuation_events", [])
            ],
        )

        expected_actions = [str(action) for action in raw["expected_actions"]]
        session = suite["session"]
        case_contamination = int(suite["candidate_graph_contamination_count"])
        case_passed = (
            suite["all_gates_passed"] is True
            and session["actions"] == expected_actions
            and session["schema"] == RUNTIME_OS_SCHEMA
            and case_contamination
            == int(raw["expected_candidate_graph_contamination_count"])
        )

        if case_passed:
            passed += 1

        contamination += case_contamination
        row = dict(suite)
        row["expected_actions"] = expected_actions
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v10.0.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "runtime_os_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
