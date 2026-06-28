from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ts_reasoner.runtime_checkpoint_restore import build_checkpoint, restore_checkpoint
from ts_reasoner.runtime_replay import replay_events
from ts_reasoner.tamper_evident_runtime_ledger import verify_hash_chain


@dataclass(frozen=True)
class RuntimeRecoveryDrillResult:
    case_id: str
    base_actions: list[str]
    continued_actions: list[str]
    checkpoint_valid: bool
    restore_valid: bool
    corrupt_checkpoint_rejected: bool
    reordered_ledger_rejected: bool
    missing_event_replay_diverged: bool
    restored_then_continued: bool
    final_state: dict[str, Any]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def run_recovery_drill(
    case_id: str,
    initial_state: dict[str, Any],
    events: list[dict[str, Any]],
    continuation_events: list[dict[str, Any]],
) -> RuntimeRecoveryDrillResult:
    checkpoint_result = build_checkpoint(
        case_id=case_id, initial_state=initial_state, events=events
    )
    checkpoint = checkpoint_result.checkpoint
    restored_state = restore_checkpoint(checkpoint)

    corrupt = deepcopy(checkpoint)
    corrupt["head_hash"] = "corrupted_head_hash"
    try:
        restore_checkpoint(corrupt)
        corrupt_checkpoint_rejected = False
    except ValueError:
        corrupt_checkpoint_rejected = True

    reordered = deepcopy(checkpoint["ledger"])
    if len(reordered) > 1:
        reordered = [reordered[1], reordered[0], *reordered[2:]]
        reordered_ledger_rejected = not verify_hash_chain(reordered)
    else:
        reordered_ledger_rejected = True

    full_replay = replay_events(
        case_id=f"{case_id}__full", initial_state=initial_state, events=events
    )
    if events:
        missing_replay = replay_events(
            case_id=f"{case_id}__missing",
            initial_state=initial_state,
            events=events[:-1],
        )
        missing_event_replay_diverged = (
            missing_replay.final_state != full_replay.final_state
        )
    else:
        missing_event_replay_diverged = True

    continued = replay_events(
        case_id=f"{case_id}__continued",
        initial_state=restored_state,
        events=continuation_events,
    )
    total_contamination = (
        checkpoint_result.candidate_graph_contamination_count
        + continued.candidate_graph_contamination_count
    )

    return RuntimeRecoveryDrillResult(
        case_id=case_id,
        base_actions=list(checkpoint_result.actions),
        continued_actions=list(continued.actions),
        checkpoint_valid=checkpoint_result.checkpoint_valid,
        restore_valid=checkpoint_result.restore_valid,
        corrupt_checkpoint_rejected=corrupt_checkpoint_rejected,
        reordered_ledger_rejected=reordered_ledger_rejected,
        missing_event_replay_diverged=missing_event_replay_diverged,
        restored_then_continued=True,
        final_state=continued.final_state,
        candidate_graph_contamination_count=total_contamination,
        explanation="Recovery drill restores verified state, rejects corrupt state, and continues runtime processing.",
    )


def evaluate_recovery_drill_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = run_recovery_drill(
            case_id=str(raw["case_id"]),
            initial_state=dict(raw["initial_state"]),
            events=[dict(event) for event in raw["events"]],
            continuation_events=[dict(event) for event in raw["continuation_events"]],
        )

        expected_base_actions = [str(action) for action in raw["expected_base_actions"]]
        expected_continued_actions = [
            str(action) for action in raw["expected_continued_actions"]
        ]
        expected_contamination = int(
            raw["expected_candidate_graph_contamination_count"]
        )

        case_passed = (
            result.base_actions == expected_base_actions
            and result.continued_actions == expected_continued_actions
            and result.checkpoint_valid
            and result.restore_valid
            and result.corrupt_checkpoint_rejected
            and result.reordered_ledger_rejected
            and result.missing_event_replay_diverged
            and result.restored_then_continued
            and result.candidate_graph_contamination_count == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count
        row = result.to_dict()
        row["expected_base_actions"] = expected_base_actions
        row["expected_continued_actions"] = expected_continued_actions
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v9.9.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "runtime_recovery_drill_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
