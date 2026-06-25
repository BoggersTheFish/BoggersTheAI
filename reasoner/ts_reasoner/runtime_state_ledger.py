from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ts_reasoner.runtime_kernel import VerifierFirstRuntimeKernel


@dataclass(frozen=True)
class LedgerEntry:
    index: int
    case_id: str
    action: str
    event: dict[str, Any]
    receipt: dict[str, Any]
    audit: dict[str, Any]
    candidate_graph_contamination_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class RuntimeLedgerResult:
    case_id: str
    actions: list[str]
    final_state: dict[str, Any]
    ledger: list[LedgerEntry]
    append_only: bool
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["ledger"] = [entry.to_dict() for entry in self.ledger]
        return data


def run_runtime_ledger(
    case_id: str,
    initial_state: dict[str, Any],
    events: list[dict[str, Any]],
) -> RuntimeLedgerResult:
    kernel = VerifierFirstRuntimeKernel()
    state = deepcopy(initial_state)
    ledger: list[LedgerEntry] = []
    actions: list[str] = []
    contamination = 0

    previous_lengths: list[int] = []

    for index, event in enumerate(events):
        previous_lengths.append(len(ledger))

        result = kernel.process_event(
            event=event,
            state=state,
            case_id=f"{case_id}__ledger_{index}",
        )

        actions.append(result.action)
        state = result.state
        contamination += result.candidate_graph_contamination_count

        ledger.append(
            LedgerEntry(
                index=index,
                case_id=f"{case_id}__ledger_{index}",
                action=result.action,
                event=deepcopy(event),
                receipt=deepcopy(result.receipt),
                audit=deepcopy(result.audit),
                candidate_graph_contamination_count=result.candidate_graph_contamination_count,
            )
        )

    append_only = all(after == before + 1 for before, after in zip(previous_lengths, range(1, len(ledger) + 1)))

    return RuntimeLedgerResult(
        case_id=case_id,
        actions=actions,
        final_state=state,
        ledger=ledger,
        append_only=append_only,
        candidate_graph_contamination_count=contamination,
        explanation="Runtime ledger records each event result as an append-only audit entry.",
    )


def evaluate_runtime_ledger_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = run_runtime_ledger(
            case_id=str(raw["case_id"]),
            initial_state=dict(raw["initial_state"]),
            events=[dict(event) for event in raw["events"]],
        )

        expected_entry_count = int(raw["expected_ledger_entry_count"])
        expected_actions = [str(action) for action in raw["expected_actions"]]
        expected_append_only = bool(raw["expected_append_only"])
        expected_contamination = int(raw["expected_candidate_graph_contamination_count"])

        case_passed = (
            len(result.ledger) == expected_entry_count
            and result.actions == expected_actions
            and result.append_only == expected_append_only
            and result.candidate_graph_contamination_count == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_ledger_entry_count"] = expected_entry_count
        row["expected_actions"] = expected_actions
        row["expected_append_only"] = expected_append_only
        row["expected_candidate_graph_contamination_count"] = expected_contamination
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v9.4.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "runtime_state_ledger_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
