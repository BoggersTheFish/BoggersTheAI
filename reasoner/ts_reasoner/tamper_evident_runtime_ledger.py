from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Any, Iterable

from ts_reasoner.runtime_state_ledger import run_runtime_ledger


GENESIS_HASH = "GENESIS"


@dataclass(frozen=True)
class HashedLedgerEntry:
    index: int
    previous_hash: str
    entry_hash: str
    entry: dict[str, Any]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class TamperEvidentLedgerResult:
    case_id: str
    actions: list[str]
    hashed_ledger: list[HashedLedgerEntry]
    chain_valid: bool
    tamper_detected: bool
    final_state: dict[str, Any]
    candidate_graph_contamination_count: int
    explanation: str

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["hashed_ledger"] = [entry.to_dict() for entry in self.hashed_ledger]
        return data


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_payload(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def make_entry_hash(previous_hash: str, entry: dict[str, Any]) -> str:
    return sha256_payload(
        {
            "previous_hash": previous_hash,
            "entry": entry,
        }
    )


def verify_hash_chain(entries: list[dict[str, Any]]) -> bool:
    previous_hash = GENESIS_HASH

    for expected_index, wrapped in enumerate(entries):
        if int(wrapped.get("index", -1)) != expected_index:
            return False

        if str(wrapped.get("previous_hash")) != previous_hash:
            return False

        entry = wrapped.get("entry")
        if not isinstance(entry, dict):
            return False

        expected_hash = make_entry_hash(previous_hash, entry)
        if str(wrapped.get("entry_hash")) != expected_hash:
            return False

        previous_hash = expected_hash

    return True


def build_tamper_evident_ledger(
    case_id: str,
    initial_state: dict[str, Any],
    events: list[dict[str, Any]],
) -> TamperEvidentLedgerResult:
    replay = run_runtime_ledger(
        case_id=case_id,
        initial_state=initial_state,
        events=events,
    )

    previous_hash = GENESIS_HASH
    hashed_entries: list[HashedLedgerEntry] = []

    for entry in replay.ledger:
        entry_payload = entry.to_dict()
        entry_hash = make_entry_hash(previous_hash, entry_payload)

        hashed_entries.append(
            HashedLedgerEntry(
                index=entry.index,
                previous_hash=previous_hash,
                entry_hash=entry_hash,
                entry=entry_payload,
            )
        )

        previous_hash = entry_hash

    chain_dicts = [entry.to_dict() for entry in hashed_entries]
    chain_valid = verify_hash_chain(chain_dicts)

    tamper_detected = False
    if chain_dicts:
        tampered = deepcopy(chain_dicts)
        tampered[0]["entry"]["action"] = "tampered_action"
        tamper_detected = not verify_hash_chain(tampered)

    return TamperEvidentLedgerResult(
        case_id=case_id,
        actions=replay.actions,
        hashed_ledger=hashed_entries,
        chain_valid=chain_valid,
        tamper_detected=tamper_detected,
        final_state=replay.final_state,
        candidate_graph_contamination_count=replay.candidate_graph_contamination_count,
        explanation="Runtime ledger is hash-chained so edits, deletions, or reordering invalidate verification.",
    )


def evaluate_tamper_evident_ledger_cases(cases: Iterable[dict[str, Any]]) -> dict[str, object]:
    results = []
    passed = 0
    total = 0
    contamination = 0

    for raw in cases:
        total += 1
        result = build_tamper_evident_ledger(
            case_id=str(raw["case_id"]),
            initial_state=dict(raw["initial_state"]),
            events=[dict(event) for event in raw["events"]],
        )

        expected_actions = [str(action) for action in raw["expected_actions"]]
        expected_chain_valid = bool(raw["expected_chain_valid"])
        expected_tamper_detected = bool(raw["expected_tamper_detected"])
        expected_entry_count = int(raw["expected_entry_count"])
        expected_contamination = int(raw["expected_candidate_graph_contamination_count"])

        case_passed = (
            result.actions == expected_actions
            and result.chain_valid == expected_chain_valid
            and result.tamper_detected == expected_tamper_detected
            and len(result.hashed_ledger) == expected_entry_count
            and result.candidate_graph_contamination_count == expected_contamination
        )

        if case_passed:
            passed += 1

        contamination += result.candidate_graph_contamination_count

        row = result.to_dict()
        row["expected_actions"] = expected_actions
        row["expected_chain_valid"] = expected_chain_valid
        row["expected_tamper_detected"] = expected_tamper_detected
        row["expected_entry_count"] = expected_entry_count
        row["expected_candidate_graph_contamination_count"] = expected_contamination
        row["passed"] = case_passed
        results.append(row)

    return {
        "release": "v9.5.0",
        "case_count": total,
        "passed_cases": passed,
        "failed_cases": total - passed,
        "tamper_evident_ledger_accuracy": passed / total if total else 0.0,
        "candidate_graph_contamination_count": contamination,
        "all_gates_passed": total > 0 and passed == total and contamination == 0,
        "results": results,
    }
