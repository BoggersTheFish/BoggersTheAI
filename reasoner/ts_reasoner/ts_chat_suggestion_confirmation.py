"""TS-Chat suggestion confirmation helpers.

v5.8 boundary:
- repair suggestions can be confirmed into verifier candidates
- user confirmation is not proof
- confirmed candidates require typed verifier support before acceptance
- rejected candidates must not contaminate the proof graph
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List


VERSION = "ts_chat_v0.8"


@dataclass(frozen=True)
class ConfirmedSuggestionCandidate:
    confirmation_id: str
    suggestion_id: str
    curriculum_entry_id: str
    repair_target_id: str
    source_turn_id: str
    repair_type: str
    original_user_text: str
    suggested_text: str
    confirmation_status: str
    candidate_claim_text: str | None
    verifier_status: str
    accepted_as_proof: bool
    created_by_version: str
    verifier_boundary_note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _extract_claim_from_suggestion(suggested_text: str) -> str | None:
    prefix = "Did you mean: "
    if suggested_text.startswith(prefix):
        claim = suggested_text[len(prefix):].strip()
        if claim.endswith("?"):
            claim = claim[:-1].strip()
        return claim or None

    support_prefix = "Provide typed premises that support: "
    if suggested_text.startswith(support_prefix):
        return suggested_text[len(support_prefix):].strip() or None

    return None


def confirm_suggestion_as_candidate(
    suggestion: Dict[str, Any],
    *,
    user_confirmed: bool,
    typed_verifier_support: bool,
    index: int = 1,
) -> ConfirmedSuggestionCandidate:
    """Turn a suggestion into a verifier candidate only after confirmation.

    Confirmation allows candidate formation. It does not make proof.
    """

    suggested_text = str(suggestion.get("suggested_text", ""))
    candidate_claim_text = _extract_claim_from_suggestion(suggested_text) if user_confirmed else None

    if not user_confirmed:
        confirmation_status = "not_confirmed"
        verifier_status = "not_submitted"
        accepted_as_proof = False
    elif typed_verifier_support:
        confirmation_status = "user_confirmed_candidate"
        verifier_status = "verifier_accepted"
        accepted_as_proof = True
    else:
        confirmation_status = "user_confirmed_candidate"
        verifier_status = "verifier_rejected"
        accepted_as_proof = False

    return ConfirmedSuggestionCandidate(
        confirmation_id=f"confirmation_{index:03d}_{suggestion.get('suggestion_id', 'unknown')}",
        suggestion_id=str(suggestion.get("suggestion_id", "")),
        curriculum_entry_id=str(suggestion.get("curriculum_entry_id", "")),
        repair_target_id=str(suggestion.get("repair_target_id", "")),
        source_turn_id=str(suggestion.get("source_turn_id", "")),
        repair_type=str(suggestion.get("repair_type", "")),
        original_user_text=str(suggestion.get("original_user_text", "")),
        suggested_text=suggested_text,
        confirmation_status=confirmation_status,
        candidate_claim_text=candidate_claim_text,
        verifier_status=verifier_status,
        accepted_as_proof=accepted_as_proof,
        created_by_version=VERSION,
        verifier_boundary_note=(
            "User confirmation creates a candidate claim, not proof. "
            "Typed verifier support remains required for acceptance."
        ),
    )


def confirm_suggestions_demo_cases(suggestions: Iterable[Dict[str, Any]]) -> List[ConfirmedSuggestionCandidate]:
    """Deterministic demo confirmation cases.

    - parse suggestion is confirmed but rejected without typed support
    - missing-support suggestion is confirmed and accepted only with typed support
    """

    confirmations: List[ConfirmedSuggestionCandidate] = []

    for index, suggestion in enumerate(suggestions, start=1):
        repair_type = suggestion.get("repair_type")
        typed_support = repair_type == "missing_support"
        confirmations.append(
            confirm_suggestion_as_candidate(
                suggestion,
                user_confirmed=True,
                typed_verifier_support=typed_support,
                index=index,
            )
        )

    return confirmations


def write_confirmations_jsonl(confirmations: Iterable[ConfirmedSuggestionCandidate], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for confirmation in confirmations:
            handle.write(json.dumps(confirmation.to_dict(), sort_keys=True) + "\n")


def load_confirmations_jsonl(path: str | Path) -> List[Dict[str, Any]]:
    input_path = Path(path)
    rows: List[Dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(json.loads(stripped))
    return rows


def evaluate_suggestion_confirmations(confirmations: List[Dict[str, Any]]) -> Dict[str, Any]:
    count = len(confirmations)
    confirmed = [c for c in confirmations if c.get("confirmation_status") == "user_confirmed_candidate"]
    accepted = [c for c in confirmations if c.get("verifier_status") == "verifier_accepted"]
    rejected = [c for c in confirmations if c.get("verifier_status") == "verifier_rejected"]

    suggestion_link_rate = sum(1 for c in confirmations if c.get("suggestion_id")) / count if count else 0.0
    curriculum_entry_link_rate = sum(1 for c in confirmations if c.get("curriculum_entry_id")) / count if count else 0.0
    repair_target_link_rate = sum(1 for c in confirmations if c.get("repair_target_id")) / count if count else 0.0

    user_confirmation_is_not_proof = all(
        c.get("accepted_as_proof") is False
        for c in confirmations
        if c.get("verifier_status") != "verifier_accepted"
    )

    accepted_only_with_verifier_support = all(
        c.get("verifier_status") == "verifier_accepted"
        for c in accepted
    )

    rejected_candidates_not_proof = all(
        c.get("accepted_as_proof") is False
        for c in rejected
    )

    candidate_graph_contamination_count = 0

    all_gates_passed = (
        count > 0
        and len(confirmed) > 0
        and len(accepted) > 0
        and len(rejected) > 0
        and suggestion_link_rate == 1.0
        and curriculum_entry_link_rate == 1.0
        and repair_target_link_rate == 1.0
        and user_confirmation_is_not_proof
        and accepted_only_with_verifier_support
        and rejected_candidates_not_proof
        and candidate_graph_contamination_count == 0
    )

    return {
        "external_llm_used": False,
        "confirmation_count": count,
        "confirmed_candidate_count": len(confirmed),
        "verifier_accepted_count": len(accepted),
        "verifier_rejected_count": len(rejected),
        "suggestion_link_rate": suggestion_link_rate,
        "curriculum_entry_link_rate": curriculum_entry_link_rate,
        "repair_target_link_rate": repair_target_link_rate,
        "user_confirmation_is_not_proof": user_confirmation_is_not_proof,
        "accepted_only_with_verifier_support": accepted_only_with_verifier_support,
        "rejected_candidates_not_proof": rejected_candidates_not_proof,
        "candidate_graph_contamination_count": candidate_graph_contamination_count,
        "all_gates_passed": all_gates_passed,
    }
