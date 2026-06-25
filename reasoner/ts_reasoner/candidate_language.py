"""Candidate language rules for TS-Chat.

This is not an LLM.

It is an inspectable response-candidate layer:
- generate multiple response candidates from common-ground records
- score candidates using simple verifier/common-ground signals
- select the highest scoring candidate
- expose which rule produced the selected response

This is the first step toward TS-native language generation where language
rules are candidate-called rather than hidden inside model weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResponseCandidate:
    candidate_id: str
    rule_id: str
    text: str
    score: float
    reasons: list[str]


def candidate_to_dict(candidate: ResponseCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "rule_id": candidate.rule_id,
        "text": candidate.text,
        "score": candidate.score,
        "reasons": candidate.reasons,
    }


def relation_text(relation: dict[str, str]) -> str:
    return f"all {relation['subject']} are {relation['object']}"


def record_relation_text(record: dict[str, Any]) -> str:
    return relation_text(record["relation"])


def generate_response_candidates(
    *,
    parsed_command: str | None,
    records: list[dict[str, Any]],
    repair_records: list[dict[str, Any]],
    parse_warnings: list[str],
    discourse_markers: list[str],
    fallback_text: str,
) -> list[ResponseCandidate]:
    """Generate candidate phrasings from explicit language rules."""

    candidates: list[ResponseCandidate] = []

    def add(rule_id: str, text: str, score: float, reasons: list[str]) -> None:
        candidates.append(
            ResponseCandidate(
                candidate_id=f"cand_{len(candidates) + 1:04d}",
                rule_id=rule_id,
                text=text,
                score=score,
                reasons=reasons,
            )
        )

    question_records = [r for r in records if r.get("kind") == "question"]
    accepted_questions = [r for r in question_records if r.get("status") == "accepted"]
    abstained_questions = [r for r in question_records if r.get("status") == "abstained"]

    requested_records = [r for r in records if r.get("kind") == "requested_claim"]
    rejected_requests = [r for r in requested_records if r.get("status") == "rejected"]
    accepted_requests = [r for r in requested_records if r.get("status") == "accepted"]

    contradiction_records = [r for r in records if r.get("kind") == "contradiction_claim"]
    negative_records = [r for r in records if r.get("kind") == "negative_claim"]

    premise_records = [r for r in records if r.get("kind") == "asserted_premise"]

    open_repairs = [r for r in repair_records if r.get("status") == "open"]
    resolved_repairs = [r for r in repair_records if r.get("status") == "resolved"]

    if premise_records or accepted_questions:
        lines: list[str] = []
        if len(premise_records) == 1:
            lines.append(f"Noted: {record_relation_text(premise_records[0])}.")
        elif len(premise_records) > 1:
            lines.append(f"Noted {len(premise_records)} premises into common ground.")

        for record in accepted_questions:
            lines.append(f"Yes — {record_relation_text(record)}.")
            lines.append("Verifier: accepted from common-ground support.")

        for repair in resolved_repairs:
            lines.append("Resolved repair targets:")
            lines.append(f"- {repair['repair_id']}: {repair['message']}")
            lines.append(f"  resolved: {repair.get('resolution_reason')}")

        add(
            "supported_answer_concise",
            "\n".join(lines),
            1.0 + 0.2 * len(accepted_questions) + 0.15 * len(resolved_repairs),
            ["uses accepted common-ground support", "concise answer rule"],
        )

    if accepted_questions:
        lines = []
        for record in accepted_questions:
            lines.append(f"Yes — {record_relation_text(record)}.")
            if record.get("support_path"):
                lines.append("Support path:")
                for edge in record["support_path"]:
                    lines.append(f"- all {edge['subject']} are {edge['object']}")
        add(
            "supported_answer_with_path",
            "\n".join(lines),
            0.9 + 0.25 * len(accepted_questions),
            ["uses support path", "more explanatory but longer"],
        )

    if abstained_questions:
        lines = []
        for record in abstained_questions:
            lines.append(f"I cannot determine that {record_relation_text(record)} from the current common ground.")
            lines.append("Verifier: abstained; support is missing.")
        add(
            "abstain_missing_support",
            "\n".join(lines),
            1.0,
            ["avoids unsupported assertion", "missing support"],
        )

    if rejected_requests:
        lines = []
        for record in rejected_requests:
            lines.append(f"I cannot support the requested claim: {record_relation_text(record)}.")
            lines.append("Verifier: rejected; unsupported requested claim was not added to common ground.")
        for repair in open_repairs:
            lines.append("Repair targets:")
            lines.append(f"- {repair['repair_id']}: {repair['message']}")
        add(
            "reject_unsupported_requested_claim",
            "\n".join(lines),
            1.2 + 0.2 * len(open_repairs),
            ["blocks unsupported requested claim", "creates repair target"],
        )

    if contradiction_records:
        lines = []
        for record in contradiction_records:
            relation = record["relation"]
            lines.append(f"Rejected contradiction: no {relation['subject']} are {relation['object']}.")
            lines.append("Verifier: rejected; negative claim conflicts with accepted common-ground support.")
            if record.get("support_path"):
                lines.append("Contradiction path:")
                for edge in record["support_path"]:
                    lines.append(f"- all {edge['subject']} are {edge['object']}")
        for repair in open_repairs:
            lines.append("Repair targets:")
            lines.append(f"- {repair['repair_id']}: {repair['message']}")
        add(
            "reject_live_contradiction",
            "\n".join(lines),
            1.45 + 0.25 * len(contradiction_records),
            ["blocks contradiction", "uses accepted support path", "creates repair target"],
        )

    if negative_records:
        lines = []
        for record in negative_records:
            relation = record["relation"]
            lines.append(f"I cannot accept the negative claim: no {relation['subject']} are {relation['object']}.")
            lines.append("Verifier: abstained; no positive support path exists to contradict.")
        add(
            "abstain_negative_claim",
            "\n".join(lines),
            0.95,
            ["negative claim is not accepted into common ground"],
        )

    if accepted_requests:
        lines = []
        for record in accepted_requests:
            lines.append(f"I can support the requested claim: {record_relation_text(record)}.")
            lines.append("Verifier: accepted from common-ground support.")
        add(
            "accept_supported_requested_claim",
            "\n".join(lines),
            1.05,
            ["requested claim has typed support"],
        )

    if open_repairs and parsed_command == "repairs":
        lines = ["Open repair targets:"]
        for repair in open_repairs:
            lines.append(f"- {repair['repair_id']}: {repair['message']}")
            for hint in repair.get("missing_support_hint", []):
                lines.append(f"  hint: {hint.get('suggestion')}")
        add(
            "list_open_repairs",
            "\n".join(lines),
            1.3,
            ["repair command requested", "lists open repairs"],
        )

    if resolved_repairs and not rejected_requests and not accepted_questions:
        lines = ["Resolved repair targets:"]
        for repair in resolved_repairs:
            lines.append(f"- {repair['repair_id']}: {repair['message']}")
            lines.append(f"  resolved: {repair.get('resolution_reason')}")
        add(
            "list_resolved_repairs",
            "\n".join(lines),
            1.0,
            ["repair target resolved"],
        )

    if parse_warnings:
        lines = []
        if open_repairs:
            lines.append("Repair targets:")
            for repair in open_repairs:
                lines.append(f"- {repair['repair_id']}: {repair['message']}")
        lines.append("Parse notes:")
        for warning in parse_warnings:
            lines.append(f"- {warning}")
        add(
            "parse_failure_repair",
            "\n".join(lines),
            1.15,
            ["parse failure exposed", "repair target created"],
        )

    if discourse_markers and candidates:
        # Candidate language can notice discourse without owning truth.
        best_text = candidates[0].text + f"\nDiscourse markers noticed: {', '.join(discourse_markers)}."
        add(
            "discourse_marker_append",
            best_text,
            candidates[0].score + 0.05,
            candidates[0].reasons + ["discourse marker surfaced"],
        )

    if not candidates:
        add(
            "fallback",
            fallback_text,
            0.1,
            ["no specific candidate rule fired"],
        )

    return candidates


def select_response_candidate(candidates: list[ResponseCandidate]) -> ResponseCandidate:
    return sorted(candidates, key=lambda c: (-c.score, c.candidate_id))[0]


def candidate_selection_to_dict(candidates: list[ResponseCandidate]) -> dict[str, Any]:
    selected = select_response_candidate(candidates)
    return {
        "selected": candidate_to_dict(selected),
        "candidates": [candidate_to_dict(candidate) for candidate in candidates],
    }
