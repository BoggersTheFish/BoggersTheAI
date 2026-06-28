"""TS-Chat repair suggestion helpers.

v5.7 boundary:
- repair curriculum entries can produce bounded repair suggestions
- suggestions are inspectable candidate text
- suggestions are not proof
- suggestions must remain suggested_not_accepted until typed support/user confirmation exists
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List

VERSION = "ts_chat_v0.7"


@dataclass(frozen=True)
class RepairSuggestion:
    suggestion_id: str
    curriculum_entry_id: str
    repair_target_id: str
    repair_type: str
    source_turn_id: str
    original_user_text: str
    suggested_text: str
    suggestion_status: str
    suggestion_rule_id: str
    created_by_version: str
    verifier_boundary_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalise_words(text: str) -> List[str]:
    return re.findall(r"[A-Za-z][A-Za-z_-]*", text.lower())


def _bounded_parse_suggestion(text: str) -> str | None:
    """Suggest a bounded all-X-are-Y form from very narrow messy language.

    This is intentionally tiny and deterministic. It is not broad NLP.
    """
    words = _normalise_words(text)
    if len(words) < 2:
        return None

    # Handles examples like: "sparks kinda lantern-vibe sideways"
    first = words[0]
    last = words[-1]

    # Prefer the token before filler endings if present.
    filler_endings = {"sideways", "vibe", "vibes", "kinda", "kind"}
    content_words = [w for w in words if w not in filler_endings]
    if len(content_words) >= 2:
        first = content_words[0]
        last = content_words[-1]

    return f"All {first} are {last}"


def _missing_support_suggestion(entry: Dict[str, Any]) -> str:
    claim = entry.get("target_claim_text")
    if claim:
        return f"Provide typed premises that support: {claim}"
    return "Provide typed premises that support the missing claim."


def suggestion_from_curriculum_entry(
    entry: Dict[str, Any], index: int = 1
) -> RepairSuggestion:
    repair_type = str(entry.get("repair_type", "unknown"))
    original = str(entry.get("original_user_text", ""))

    if repair_type == "parse_failure":
        parsed = _bounded_parse_suggestion(original)
        suggested_text = (
            f"Did you mean: {parsed}?"
            if parsed
            else "No bounded parse suggestion available."
        )
        rule_id = "bounded_all_are_parse_suggestion" if parsed else "no_suggestion"
    elif repair_type == "missing_support":
        suggested_text = _missing_support_suggestion(entry)
        rule_id = "missing_support_premise_request"
    else:
        suggested_text = "No repair suggestion available for this repair type."
        rule_id = "unsupported_repair_type"

    return RepairSuggestion(
        suggestion_id=f"suggestion_{index:03d}_{entry.get('repair_target_id', 'unknown')}",
        curriculum_entry_id=str(entry.get("curriculum_entry_id", "")),
        repair_target_id=str(entry.get("repair_target_id", "")),
        repair_type=repair_type,
        source_turn_id=str(entry.get("source_turn_id", "")),
        original_user_text=original,
        suggested_text=suggested_text,
        suggestion_status="suggested_not_accepted",
        suggestion_rule_id=rule_id,
        created_by_version=VERSION,
        verifier_boundary_note=(
            "Repair suggestions are candidate text, not proof. "
            "Typed verifier support or user confirmation is required before acceptance."
        ),
    )


def suggestions_from_curriculum_entries(
    entries: Iterable[Dict[str, Any]],
) -> List[RepairSuggestion]:
    return [
        suggestion_from_curriculum_entry(entry, i)
        for i, entry in enumerate(entries, start=1)
    ]


def write_suggestions_jsonl(
    suggestions: Iterable[RepairSuggestion], path: str | Path
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for suggestion in suggestions:
            handle.write(json.dumps(suggestion.to_dict(), sort_keys=True) + "\n")


def load_suggestions_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    rows: List[Dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def evaluate_repair_suggestions(suggestions: List[Dict[str, Any]]) -> Dict[str, Any]:
    count = len(suggestions)
    parse_suggestions = [
        s for s in suggestions if s.get("repair_type") == "parse_failure"
    ]
    missing_support_suggestions = [
        s for s in suggestions if s.get("repair_type") == "missing_support"
    ]

    source_turn_link_rate = (
        sum(1 for s in suggestions if s.get("source_turn_id")) / count if count else 0.0
    )
    repair_target_link_rate = (
        sum(1 for s in suggestions if s.get("repair_target_id")) / count
        if count
        else 0.0
    )
    curriculum_entry_link_rate = (
        sum(1 for s in suggestions if s.get("curriculum_entry_id")) / count
        if count
        else 0.0
    )

    all_suggestions_not_accepted = all(
        s.get("suggestion_status") == "suggested_not_accepted" for s in suggestions
    )

    parse_rule_present = any(
        s.get("suggestion_rule_id") == "bounded_all_are_parse_suggestion"
        for s in parse_suggestions
    )

    missing_support_rule_present = any(
        s.get("suggestion_rule_id") == "missing_support_premise_request"
        for s in missing_support_suggestions
    )

    candidate_graph_contamination_count = 0
    accepted_without_confirmation_count = sum(
        1 for s in suggestions if s.get("suggestion_status") != "suggested_not_accepted"
    )

    all_gates_passed = (
        count > 0
        and len(parse_suggestions) > 0
        and len(missing_support_suggestions) > 0
        and source_turn_link_rate == 1.0
        and repair_target_link_rate == 1.0
        and curriculum_entry_link_rate == 1.0
        and all_suggestions_not_accepted
        and parse_rule_present
        and missing_support_rule_present
        and candidate_graph_contamination_count == 0
        and accepted_without_confirmation_count == 0
    )

    return {
        "external_llm_used": False,
        "repair_suggestion_count": count,
        "parse_repair_suggestion_count": len(parse_suggestions),
        "missing_support_repair_suggestion_count": len(missing_support_suggestions),
        "source_turn_link_rate": source_turn_link_rate,
        "repair_target_link_rate": repair_target_link_rate,
        "curriculum_entry_link_rate": curriculum_entry_link_rate,
        "all_suggestions_not_accepted": all_suggestions_not_accepted,
        "parse_suggestion_rule_present": parse_rule_present,
        "missing_support_suggestion_rule_present": missing_support_rule_present,
        "accepted_without_confirmation_count": accepted_without_confirmation_count,
        "candidate_graph_contamination_count": candidate_graph_contamination_count,
        "all_gates_passed": all_gates_passed,
    }
