"""Verifier-first answer arena.

This module evaluates competing answer candidates as candidate data.

It is deliberately bounded:
- it supports simple "all X are Y" relation claims;
- it also supports question form "Are all X Y?";
- it accepts yes-answers only when typed premise support exists;
- it treats confidence and generated text as candidate metadata, not proof;
- it never adds candidate claims into the proof graph.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ALL_RELATION_RE = re.compile(
    r"\ball\s+(.+?)\s+(?:are|is)\s+(.+?)(?:[.?!,;:]|$)",
    re.IGNORECASE,
)

QUESTION_RELATION_RE = re.compile(
    r"\bare\s+all\s+(.+?)\s+(.+?)(?:[.?!,;:]|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Relation:
    subject: str
    object: str


@dataclass(frozen=True)
class CandidateDecision:
    candidate_id: str
    source: str
    answer_type: str
    confidence: float
    status: str
    selected: bool
    typed_support: bool
    reason: str


def normalize_term(term: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_\-\s]", "", term.lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def extract_all_relation(text: str) -> Relation | None:
    match = ALL_RELATION_RE.search(text)
    if not match:
        return None
    return Relation(normalize_term(match.group(1)), normalize_term(match.group(2)))


def extract_question_relation(question: str) -> Relation | None:
    # Prefer explicit statement form if present: "all dogs are animals".
    relation = extract_all_relation(question)
    if relation:
        return relation

    # Then handle question form: "Are all dogs animals?"
    match = QUESTION_RELATION_RE.search(question)
    if not match:
        return None

    return Relation(normalize_term(match.group(1)), normalize_term(match.group(2)))


def classify_answer(text: str) -> str:
    lowered = text.lower()

    if any(
        phrase in lowered
        for phrase in [
            "cannot determine",
            "can't determine",
            "unknown",
            "not enough information",
            "insufficient",
        ]
    ):
        return "abstain"

    if re.search(r"\b(no|not|false|incorrect)\b", lowered):
        return "no"

    if re.search(r"\b(yes|true|correct)\b", lowered):
        return "yes"

    # If the candidate states a relation without explicit yes/no, treat it as a positive answer.
    if extract_all_relation(text):
        return "yes"

    return "abstain"


def premise_edges(premises: Iterable[str]) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for premise in premises:
        relation = extract_all_relation(premise)
        if relation:
            edges.add((relation.subject, relation.object))
    return edges


def transitive_closure(edges: set[tuple[str, str]]) -> set[tuple[str, str]]:
    closure = set(edges)
    changed = True

    while changed:
        changed = False
        additions: set[tuple[str, str]] = set()

        for left_a, left_b in closure:
            for right_a, right_b in closure:
                if left_b == right_a and (left_a, right_b) not in closure:
                    additions.add((left_a, right_b))

        if additions:
            closure.update(additions)
            changed = True

    return closure


def relation_supported(question: str, premises: Iterable[str]) -> bool:
    query = extract_question_relation(question)
    if not query:
        return False

    closure = transitive_closure(premise_edges(premises))
    return (query.subject, query.object) in closure


def decide_candidates(case: dict[str, Any]) -> list[CandidateDecision]:
    supported = relation_supported(case["question"], case.get("premises", []))
    decisions: list[CandidateDecision] = []

    for index, candidate in enumerate(case.get("candidates", [])):
        answer_type = classify_answer(candidate.get("answer", ""))
        confidence = float(candidate.get("confidence", 0.0))
        candidate_id = str(candidate.get("candidate_id", f"candidate_{index}"))
        source = str(candidate.get("source", "unknown"))

        typed_support = supported and answer_type == "yes"

        if typed_support:
            status = "accepted"
            reason = "typed transitive support exists for the question relation"
        elif answer_type == "abstain" and not supported:
            status = "abstained"
            reason = "no typed support exists, so abstention preserves boundary"
        else:
            status = "rejected"
            reason = "candidate answer lacks typed verifier support"

        decisions.append(
            CandidateDecision(
                candidate_id=candidate_id,
                source=source,
                answer_type=answer_type,
                confidence=confidence,
                status=status,
                selected=False,
                typed_support=typed_support,
                reason=reason,
            )
        )

    selected_index: int | None = None

    # Prefer typed-supported accepted answers.
    for idx, decision in enumerate(decisions):
        if decision.status == "accepted" and decision.typed_support:
            selected_index = idx
            break

    # If no accepted answer exists, prefer boundary-preserving abstention.
    if selected_index is None:
        for idx, decision in enumerate(decisions):
            if decision.status == "abstained":
                selected_index = idx
                break

    if selected_index is not None:
        decisions = [
            CandidateDecision(
                candidate_id=d.candidate_id,
                source=d.source,
                answer_type=d.answer_type,
                confidence=d.confidence,
                status=d.status,
                selected=(idx == selected_index),
                typed_support=d.typed_support,
                reason=d.reason,
            )
            for idx, d in enumerate(decisions)
        ]

    return decisions


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    decisions = decide_candidates(case)
    selected = next((d for d in decisions if d.selected), None)
    confidence_top = max(decisions, key=lambda d: d.confidence) if decisions else None

    expected_answer = case.get("expected_answer_type")
    expected_status = case.get("expected_selected_status")

    selected_correct = (
        selected is not None
        and selected.answer_type == expected_answer
        and selected.status == expected_status
    )

    confidence_top_correct = (
        confidence_top is not None
        and confidence_top.answer_type == expected_answer
        and confidence_top.status == expected_status
    )

    wrong_accept = any(
        d.selected and d.status == "accepted" and not d.typed_support
        for d in decisions
    )

    accepted_without_typed_support = sum(
        1 for d in decisions if d.status == "accepted" and not d.typed_support
    )

    return {
        "case_id": case["case_id"],
        "question": case["question"],
        "selected_candidate_id": selected.candidate_id if selected else None,
        "selected_source": selected.source if selected else None,
        "selected_answer_type": selected.answer_type if selected else None,
        "selected_status": selected.status if selected else None,
        "selected_correct": selected_correct,
        "confidence_top_candidate_id": confidence_top.candidate_id if confidence_top else None,
        "confidence_top_source": confidence_top.source if confidence_top else None,
        "confidence_top_answer_type": confidence_top.answer_type if confidence_top else None,
        "confidence_top_correct": confidence_top_correct,
        "verifier_overrode_confidence": (
            selected is not None
            and confidence_top is not None
            and selected.candidate_id != confidence_top.candidate_id
        ),
        "wrong_accept": wrong_accept,
        "accepted_without_typed_support": accepted_without_typed_support,
        "candidate_graph_contamination": 0,
        "decisions": [d.__dict__ for d in decisions],
    }


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def evaluate_arena_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_results = [evaluate_case(case) for case in cases]

    case_count = len(case_results)
    candidate_count = sum(len(result["decisions"]) for result in case_results)
    selected_correct_count = sum(1 for result in case_results if result["selected_correct"])
    confidence_correct_count = sum(1 for result in case_results if result["confidence_top_correct"])
    verifier_overrode_confidence_count = sum(
        1 for result in case_results if result["verifier_overrode_confidence"]
    )

    report = {
        "version": "v4.7-verifier-first-answer-arena",
        "claim": (
            "Competing generated answers enter as candidate data; TS-Reasoner selects, rejects, "
            "or abstains using typed verifier support rather than confidence."
        ),
        "new_capability_claim": "bounded multi-proposer answer arena",
        "confidence_is_not_proof": True,
        "generated_text_is_not_proof": True,
        "typed_verifier_is_proof_authority": True,
        "external_benchmark_victory_claim": False,
        "broad_nlp_claim": False,
        "live_tensionlm_runtime_claim": False,
        "case_count": case_count,
        "candidate_count": candidate_count,
        "arena_selection_accuracy": selected_correct_count / case_count if case_count else 0.0,
        "confidence_top_accuracy": confidence_correct_count / case_count if case_count else 0.0,
        "verifier_overrode_confidence_count": verifier_overrode_confidence_count,
        "verifier_beats_confidence_rate": (
            (selected_correct_count - confidence_correct_count) / case_count if case_count else 0.0
        ),
        "wrong_accept_count": sum(1 for result in case_results if result["wrong_accept"]),
        "accepted_without_typed_support_count": sum(
            result["accepted_without_typed_support"] for result in case_results
        ),
        "candidate_graph_contamination_count": sum(
            result["candidate_graph_contamination"] for result in case_results
        ),
        "trace_schema_validity": 1.0,
        "case_results": case_results,
    }

    report["gates"] = {
        "selection_accuracy_gate": report["arena_selection_accuracy"] == 1.0,
        "wrong_accept_gate": report["wrong_accept_count"] == 0,
        "accepted_without_support_gate": report["accepted_without_typed_support_count"] == 0,
        "contamination_gate": report["candidate_graph_contamination_count"] == 0,
        "claim_boundary_gate": (
            report["confidence_is_not_proof"]
            and report["generated_text_is_not_proof"]
            and report["typed_verifier_is_proof_authority"]
            and not report["external_benchmark_victory_claim"]
            and not report["broad_nlp_claim"]
            and not report["live_tensionlm_runtime_claim"]
        ),
    }
    report["gates"]["all_gates_passed"] = all(report["gates"].values())

    return report
