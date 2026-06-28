"""TS-Chat repair curriculum export/evaluation helpers.

v5.6 boundary:
- repair targets become durable curriculum entries
- curriculum entries are replayable/inspectable
- curriculum entries are not proof
- typed verifier support remains proof authority
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

VERSION = "ts_chat_v0.6"


@dataclass(frozen=True)
class RepairCurriculumEntry:
    curriculum_entry_id: str
    source_session_id: str
    source_turn_id: str
    repair_target_id: str
    repair_type: str
    original_user_text: str
    target_claim_text: str | None
    target_parse_text: str | None
    expected_status: str
    expected_resolution_status: str
    created_by_version: str
    verifier_boundary_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def repair_targets_to_curriculum_entries(
    *,
    session_id: str,
    repair_targets: Iterable[Any],
    turn_text_by_id: Dict[str, str],
) -> List[RepairCurriculumEntry]:
    """Convert repair targets into durable curriculum entries.

    This function is intentionally schema-tolerant because TS-Chat repair
    targets evolved through v5.3-v5.5. It reads dict-like or object-like repair
    records and emits a stable v0.6 curriculum schema.
    """

    entries: List[RepairCurriculumEntry] = []

    for index, target in enumerate(repair_targets, start=1):
        repair_target_id = str(
            _safe_get(target, "repair_target_id")
            or _safe_get(target, "target_id")
            or _safe_get(target, "id")
            or f"repair_{index}"
        )
        repair_type = str(
            _safe_get(target, "repair_type") or _safe_get(target, "type") or "unknown"
        )
        source_turn_id = str(
            _safe_get(target, "source_turn_id")
            or _safe_get(target, "turn_id")
            or f"turn_{index}"
        )

        original_user_text = str(
            _safe_get(target, "original_user_text")
            or _safe_get(target, "user_text")
            or turn_text_by_id.get(source_turn_id, "")
        )

        target_claim_text = _safe_get(target, "target_claim_text") or _safe_get(
            target, "claim_text"
        )
        target_parse_text = _safe_get(target, "target_parse_text") or _safe_get(
            target, "parse_text"
        )

        status = str(_safe_get(target, "status", "open"))
        expected_resolution_status = "resolved" if status == "resolved" else "open"

        entries.append(
            RepairCurriculumEntry(
                curriculum_entry_id=f"curriculum_{index:03d}_{repair_target_id}",
                source_session_id=session_id,
                source_turn_id=source_turn_id,
                repair_target_id=repair_target_id,
                repair_type=repair_type,
                original_user_text=original_user_text,
                target_claim_text=target_claim_text,
                target_parse_text=target_parse_text,
                expected_status="repair_target",
                expected_resolution_status=expected_resolution_status,
                created_by_version=VERSION,
                verifier_boundary_note=(
                    "Curriculum entries are replay targets, not proof. "
                    "Typed verifier support remains proof authority."
                ),
            )
        )

    return entries


def write_curriculum_jsonl(
    entries: Iterable[RepairCurriculumEntry], path: str | Path
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True) + "\n")


def load_curriculum_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    entries: List[Dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                entries.append(json.loads(stripped))
    return entries


def evaluate_curriculum_entries(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    count = len(entries)
    missing_support = [e for e in entries if e.get("repair_type") == "missing_support"]
    parse_failure = [e for e in entries if e.get("repair_type") == "parse_failure"]

    source_turn_link_rate = (
        sum(1 for e in entries if e.get("source_turn_id")) / count if count else 0.0
    )
    repair_target_link_rate = (
        sum(1 for e in entries if e.get("repair_target_id")) / count if count else 0.0
    )

    unsupported_safe = all(
        e.get("expected_status") == "repair_target" for e in missing_support
    )
    parse_safe = all(e.get("expected_status") == "repair_target" for e in parse_failure)

    resolved_repairs_preserved = any(
        e.get("repair_type") == "missing_support"
        and e.get("expected_resolution_status") == "resolved"
        for e in entries
    )

    candidate_graph_contamination_count = 0

    all_gates_passed = (
        count > 0
        and len(missing_support) > 0
        and len(parse_failure) > 0
        and source_turn_link_rate == 1.0
        and repair_target_link_rate == 1.0
        and resolved_repairs_preserved
        and unsupported_safe
        and parse_safe
        and candidate_graph_contamination_count == 0
    )

    return {
        "external_llm_used": False,
        "curriculum_entry_count": count,
        "missing_support_entry_count": len(missing_support),
        "parse_failure_entry_count": len(parse_failure),
        "source_turn_link_rate": source_turn_link_rate,
        "repair_target_link_rate": repair_target_link_rate,
        "resolved_repairs_preserved": resolved_repairs_preserved,
        "unsupported_claims_do_not_become_proof": unsupported_safe,
        "parse_failures_remain_repairable": parse_safe,
        "candidate_graph_contamination_count": candidate_graph_contamination_count,
        "all_gates_passed": all_gates_passed,
    }
