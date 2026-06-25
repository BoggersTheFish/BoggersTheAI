from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ts_reasoner.tamper_evident_runtime_ledger import (
    GENESIS_HASH,
    build_tamper_evident_ledger,
    verify_hash_chain,
)


@dataclass(frozen=True)
class RuntimeCheckpointResult:
    case_id: str
    actions: list[str]
    checkpoint: dict[str, Any]
    restored_state: dict[str, Any]
    checkpoint_valid: bool
    restore_valid: bool
    head_hash_present: bool
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_checkpoint(case_id: str, initial_state: dict[str, Any], events: list[dict[str, Any]]) -> RuntimeCheckpointResult:
    result = build_tamper_evident_ledger(
        case_id=case_id,
        initial_state=initial_state,
        events=events,
    )

    ledger = [entry.to_dict() for entry in result.hashed_ledger]
    head_hash = ledger[-1]["entry_hash"] if ledger else GENESIS_HASH

    checkpoint = {
        "schema": "ts_reasoner_runtime_checkpoint_v1",
        "case_id": case_id,
        "state": deepcopy(result.final_state),
        "actions": list(result.actions),
        "ledger": ledger,
        "head_hash": head_hash,
        "candidate_graph_contamination_count": result.candidate_graph_contamination_count,
    }

    checkpoint_valid = (
        checkpoint["schema"] == "ts_reasoner_runtime_checkpoint_v1"
        and isinstance(checkpoint["state"], dict)
        and isinstance(checkpoint["actions"], list)
        and isinstance(checkpoint["ledger"], list)
        and isinstance(checkpoint["head_hash"], str)
        and verify_hash_chain(ledger)
        and (head_hash == GENESIS_HASH if not ledger else head_hash == ledger[-1]["entry_hash"])
        and checkpoint["candidate_graph_contamination_count"] == 0
    )

    restored_state = restore_checkpoint(checkpoint)
    restore_valid = restored_state == checkpoint["state"] and checkpoint_valid

    return RuntimeCheckpointResult(
        case_id=case_id,
        actions=list(result.actions),
        checkpoint=checkpoint,
        restored_state=restored_state,
        checkpoint_valid=checkpoint_valid,
        restore_valid=restore_valid,
        head_hash_present=bool(head_hash),
        candidate_graph_contamination_count=result.candidate_graph_contamination_count,
        explanation="Runtime checkpoint stores state, actions, ledger, and head hash for safe restore.",
    )


def restore_checkpoint(checkpoint: dict[str, Any]) -> dict[str, Any]:
    if checkpoint.get("schema") != "ts_reasoner_runtime_checkpoint_v1":
        raise ValueError("invalid checkpoint schema")

    ledger = checkpoint.get("ledger")
    if not isinstance(ledger, list) or not verify_hash_chain(ledger):
        raise ValueError("invalid checkpoint ledger")

    head_hash = checkpoint.get("head_hash")
    expected_head = ledger[-1]["entry_hash"] if ledger else GENESIS_HASH
    if head_hash != expected_head:
        raise ValueError("invalid checkpoint head hash")

    state = checkpoint.get("state")
    if not isinstance(state, dict):
        raise ValueError("invalid checkpoint state")

    return deepcopy(state)


def evaluate_runtime_checkpoint_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = build_checkpoint(
            case_id=str(raw["case_id"]),
            initial_state=dict(raw["initial_state"]),
            events=[dict(event) for event in raw["events"]],
        )

        expected_actions = [str(action) for action in raw["expected_actions"]]
        expected_checkpoint_valid = bool(raw["expected_checkpoint_valid"])
        expected_restore_valid = bool(raw["expected_restore_valid"])
        expected_head_hash_present = bool(raw["expected_head_hash_present"])
        expected_contamination = int(raw["expected_candidate_graph_contamination_count"])

        case_passed = (
            result.actions == expected_actions
            and result.checkpoint_valid == expected_checkpoint_valid
            and result.restore_valid == expected_restore_valid
            and result.head_hash_present == expected_head_hash_present
            and result.candidate_graph_contamination_count == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_actions"] = expected_actions
        row["expected_checkpoint_valid"] = expected_checkpoint_valid
        row["expected_restore_valid"] = expected_restore_valid
        row["expected_head_hash_present"] = expected_head_hash_present
        row["expected_candidate_graph_contamination_count"] = expected_contamination
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v9.6.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "runtime_checkpoint_restore_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
