"""TS-Chat improvement ledger helpers.

v5.9 boundary:
- measure repair-loop progress across existing TS-Chat artifacts
- compare repair curriculum, suggestions, and confirmations
- produce an inspectable improvement ledger
- metrics are evidence of workflow progress, not proof of broad language understanding
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List

VERSION = "ts_chat_v0.9"


@dataclass(frozen=True)
class ImprovementLedger:
    ledger_id: str
    created_by_version: str
    curriculum_entry_count: int
    repair_suggestion_count: int
    confirmation_count: int
    confirmed_candidate_count: int
    verifier_accepted_count: int
    verifier_rejected_count: int
    open_repair_count: int
    resolved_repair_count: int
    measurable_loop_coverage_rate: float
    accepted_confirmation_rate: float
    zero_candidate_graph_contamination: bool
    improvement_summary: str
    verifier_boundary_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    rows: List[Dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def build_improvement_ledger(
    *,
    curriculum_path: str | Path,
    suggestions_path: str | Path,
    confirmations_path: str | Path,
    ledger_id: str = "ts_chat_v0_9_improvement_ledger",
) -> ImprovementLedger:
    curriculum = _load_jsonl(curriculum_path)
    suggestions = _load_jsonl(suggestions_path)
    confirmations = _load_jsonl(confirmations_path)

    curriculum_ids = {
        row.get("curriculum_entry_id")
        for row in curriculum
        if row.get("curriculum_entry_id")
    }
    suggestion_curriculum_ids = {
        row.get("curriculum_entry_id")
        for row in suggestions
        if row.get("curriculum_entry_id")
    }
    confirmation_suggestion_ids = {
        row.get("suggestion_id") for row in confirmations if row.get("suggestion_id")
    }
    suggestion_ids = {
        row.get("suggestion_id") for row in suggestions if row.get("suggestion_id")
    }

    open_repairs = [
        row for row in curriculum if row.get("expected_resolution_status") == "open"
    ]
    resolved_repairs = [
        row for row in curriculum if row.get("expected_resolution_status") == "resolved"
    ]

    confirmed = [
        row
        for row in confirmations
        if row.get("confirmation_status") == "user_confirmed_candidate"
    ]
    accepted = [
        row
        for row in confirmations
        if row.get("verifier_status") == "verifier_accepted"
    ]
    rejected = [
        row
        for row in confirmations
        if row.get("verifier_status") == "verifier_rejected"
    ]

    curriculum_covered = len(curriculum_ids.intersection(suggestion_curriculum_ids))
    suggestions_confirmed = len(
        suggestion_ids.intersection(confirmation_suggestion_ids)
    )

    coverage_denominator = max(len(curriculum_ids) + len(suggestion_ids), 1)
    measurable_loop_coverage_rate = (
        curriculum_covered + suggestions_confirmed
    ) / coverage_denominator

    accepted_confirmation_rate = len(accepted) / len(confirmed) if confirmed else 0.0

    contamination_count = sum(
        1
        for row in confirmations
        if row.get("verifier_status") == "verifier_rejected"
        and row.get("accepted_as_proof") is True
    )
    zero_contamination = contamination_count == 0

    improvement_summary = (
        "TS-Chat has a measurable repair loop: curriculum entries produce suggestions, "
        "suggestions produce confirmed candidates, and verifier outcomes are tracked "
        "without candidate graph contamination."
    )

    return ImprovementLedger(
        ledger_id=ledger_id,
        created_by_version=VERSION,
        curriculum_entry_count=len(curriculum),
        repair_suggestion_count=len(suggestions),
        confirmation_count=len(confirmations),
        confirmed_candidate_count=len(confirmed),
        verifier_accepted_count=len(accepted),
        verifier_rejected_count=len(rejected),
        open_repair_count=len(open_repairs),
        resolved_repair_count=len(resolved_repairs),
        measurable_loop_coverage_rate=measurable_loop_coverage_rate,
        accepted_confirmation_rate=accepted_confirmation_rate,
        zero_candidate_graph_contamination=zero_contamination,
        improvement_summary=improvement_summary,
        verifier_boundary_note=(
            "Improvement ledger metrics measure repair-loop workflow progress, not broad NLP. "
            "Typed verifier support remains proof authority."
        ),
    )


def write_improvement_ledger(ledger: ImprovementLedger, path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(ledger.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def load_improvement_ledger(path: str | Path) -> Dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def evaluate_improvement_ledger(ledger: Dict[str, Any]) -> Dict[str, Any]:
    has_curriculum = ledger.get("curriculum_entry_count", 0) > 0
    has_suggestions = ledger.get("repair_suggestion_count", 0) > 0
    has_confirmations = ledger.get("confirmation_count", 0) > 0
    has_accepted_and_rejected = (
        ledger.get("verifier_accepted_count", 0) > 0
        and ledger.get("verifier_rejected_count", 0) > 0
    )

    coverage_rate = float(ledger.get("measurable_loop_coverage_rate", 0.0))
    accepted_rate = float(ledger.get("accepted_confirmation_rate", 0.0))
    zero_contamination = bool(ledger.get("zero_candidate_graph_contamination", False))

    all_gates_passed = (
        has_curriculum
        and has_suggestions
        and has_confirmations
        and has_accepted_and_rejected
        and coverage_rate == 1.0
        and 0.0 < accepted_rate < 1.0
        and zero_contamination
    )

    return {
        "external_llm_used": False,
        "has_curriculum_entries": has_curriculum,
        "has_repair_suggestions": has_suggestions,
        "has_confirmations": has_confirmations,
        "has_accepted_and_rejected_verifier_outcomes": has_accepted_and_rejected,
        "measurable_loop_coverage_rate": coverage_rate,
        "accepted_confirmation_rate": accepted_rate,
        "zero_candidate_graph_contamination": zero_contamination,
        "all_gates_passed": all_gates_passed,
    }
