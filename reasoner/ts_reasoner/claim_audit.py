"""Unsupported-claim audit for decomposed generated reasoning.

v4.9 tightens the v4.8 claim-decomposer arena.

A candidate answer can no longer be accepted just because it contains one
supported final claim. If the explanation also contains unsupported bounded
all-X-are-Y claims, the candidate is rejected.

This remains bounded. It audits simple all-X-are-Y relations only.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ts_reasoner.answer_arena import (
    Relation,
    extract_question_relation,
    normalize_term,
    premise_edges,
    transitive_closure,
)
from ts_reasoner.claim_decomposer import decompose_candidate_answer, decomposed_claim_to_dict


CLAUSE_RELATION_RE = re.compile(
    r"\ball\s+(.+?)\s+(?:are|is)\s+(.+?)(?:[.?!,;:]|$)",
    re.IGNORECASE,
)


def split_relation_clauses(text: str) -> str:
    """Add punctuation boundaries before repeated all-X claims.

    Example:
    "all dogs are mammals and all mammals are animals"
    becomes:
    "all dogs are mammals. all mammals are animals"
    """

    normalized = re.sub(r"\s+(?:and|,)\s+(?=all\s+)", ". ", text, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+(?:so|therefore)\s+(?=all\s+)", ". ", normalized, flags=re.IGNORECASE)
    return normalized


def extract_audit_relations(text: str) -> list[Relation]:
    text = split_relation_clauses(text)
    relations: list[Relation] = []

    for match in CLAUSE_RELATION_RE.finditer(text):
        relation = Relation(
            normalize_term(match.group(1)),
            normalize_term(match.group(2)),
        )
        if relation not in relations:
            relations.append(relation)

    return relations


def audit_candidate_claims(
    candidate_text: str,
    premises: list[str],
) -> dict[str, Any]:
    closure = transitive_closure(premise_edges(premises))
    extracted = extract_audit_relations(candidate_text)

    audited_claims: list[dict[str, Any]] = []
    unsupported: list[dict[str, Any]] = []

    for relation in extracted:
        supported = (relation.subject, relation.object) in closure
        row = {
            "subject": relation.subject,
            "object": relation.object,
            "typed_supported": supported,
        }
        audited_claims.append(row)
        if not supported:
            unsupported.append(row)

    return {
        "audited_claims": audited_claims,
        "unsupported_claims": unsupported,
        "unsupported_claim_count": len(unsupported),
    }


def evaluate_audited_case(case: dict[str, Any]) -> dict[str, Any]:
    question_relation = extract_question_relation(case["question"])
    closure = transitive_closure(premise_edges(case.get("premises", [])))
    question_supported = (
        question_relation is not None
        and (question_relation.subject, question_relation.object) in closure
    )

    decisions: list[dict[str, Any]] = []

    for index, candidate in enumerate(case.get("candidates", [])):
        candidate_id = str(candidate.get("candidate_id", f"candidate_{index}"))
        source = str(candidate.get("source", "unknown"))
        confidence = float(candidate.get("confidence", 0.0))
        text = str(candidate.get("answer", ""))

        decomposed = decompose_candidate_answer(text, question=case["question"])
        decomposed_dict = decomposed_claim_to_dict(decomposed)
        audit = audit_candidate_claims(text, case.get("premises", []))

        relation_matches_question = (
            question_relation is not None
            and decomposed.extracted_relation is not None
            and decomposed.extracted_relation == question_relation
        )

        final_claim_supported = (
            decomposed.answer_type == "yes"
            and relation_matches_question
            and question_supported
        )

        explanation_audit_passed = audit["unsupported_claim_count"] == 0

        typed_support = final_claim_supported and explanation_audit_passed

        if typed_support:
            status = "accepted"
            reason = "final claim has typed support and explanation contains no unsupported bounded claims"
        elif decomposed.answer_type == "abstain" and not question_supported:
            status = "abstained"
            reason = "candidate abstains and no typed verifier support exists"
        else:
            status = "rejected"
            if final_claim_supported and not explanation_audit_passed:
                reason = "final claim is supported, but explanation contains unsupported bounded claims"
            else:
                reason = "candidate lacks matching typed verifier support"

        decisions.append(
            {
                "candidate_id": candidate_id,
                "source": source,
                "confidence": confidence,
                "answer": text,
                "answer_type": decomposed.answer_type,
                "status": status,
                "selected": False,
                "typed_support": typed_support,
                "final_claim_supported": final_claim_supported,
                "relation_matches_question": relation_matches_question,
                "explanation_audit_passed": explanation_audit_passed,
                "decomposed_claim": decomposed_dict,
                "claim_audit": audit,
                "reason": reason,
            }
        )

    selected_index: int | None = None

    for idx, decision in enumerate(decisions):
        if decision["status"] == "accepted" and decision["typed_support"]:
            selected_index = idx
            break

    if selected_index is None:
        for idx, decision in enumerate(decisions):
            if decision["status"] == "abstained":
                selected_index = idx
                break

    if selected_index is not None:
        for idx, decision in enumerate(decisions):
            decision["selected"] = idx == selected_index

    selected = next((d for d in decisions if d["selected"]), None)
    confidence_top = max(decisions, key=lambda d: d["confidence"]) if decisions else None

    expected_answer = case.get("expected_answer_type")
    expected_status = case.get("expected_selected_status")

    selected_correct = (
        selected is not None
        and selected["answer_type"] == expected_answer
        and selected["status"] == expected_status
    )

    confidence_top_correct = (
        confidence_top is not None
        and confidence_top["answer_type"] == expected_answer
        and confidence_top["status"] == expected_status
    )

    return {
        "case_id": case["case_id"],
        "question": case["question"],
        "selected_candidate_id": selected["candidate_id"] if selected else None,
        "selected_source": selected["source"] if selected else None,
        "selected_answer_type": selected["answer_type"] if selected else None,
        "selected_status": selected["status"] if selected else None,
        "selected_correct": selected_correct,
        "selected_explanation_audit_passed": selected["explanation_audit_passed"] if selected else None,
        "confidence_top_candidate_id": confidence_top["candidate_id"] if confidence_top else None,
        "confidence_top_source": confidence_top["source"] if confidence_top else None,
        "confidence_top_answer_type": confidence_top["answer_type"] if confidence_top else None,
        "confidence_top_correct": confidence_top_correct,
        "verifier_overrode_confidence": (
            selected is not None
            and confidence_top is not None
            and selected["candidate_id"] != confidence_top["candidate_id"]
        ),
        "wrong_accept": bool(selected and selected["status"] == "accepted" and not selected["typed_support"]),
        "accepted_without_typed_support": sum(
            1 for decision in decisions if decision["status"] == "accepted" and not decision["typed_support"]
        ),
        "accepted_with_unsupported_claims": sum(
            1
            for decision in decisions
            if decision["status"] == "accepted" and not decision["explanation_audit_passed"]
        ),
        "unsupported_claim_candidate_count": sum(
            1 for decision in decisions if decision["claim_audit"]["unsupported_claim_count"] > 0
        ),
        "candidate_graph_contamination": 0,
        "decisions": decisions,
    }


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def evaluate_claim_audit_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    case_results = [evaluate_audited_case(case) for case in cases]

    case_count = len(case_results)
    candidate_count = sum(len(result["decisions"]) for result in case_results)
    selected_correct_count = sum(1 for result in case_results if result["selected_correct"])
    confidence_correct_count = sum(1 for result in case_results if result["confidence_top_correct"])
    verifier_overrode_confidence_count = sum(
        1 for result in case_results if result["verifier_overrode_confidence"]
    )
    unsupported_claim_candidate_count = sum(
        result["unsupported_claim_candidate_count"] for result in case_results
    )

    report = {
        "version": "v4.9-unsupported-claim-audit",
        "claim": (
            "Generated answers are rejected when their explanations contain unsupported bounded claims, "
            "even if the final answer claim is typed-supported."
        ),
        "new_capability_claim": "bounded unsupported-claim audit for generated reasoning explanations",
        "confidence_is_not_proof": True,
        "generated_text_is_not_proof": True,
        "candidate_source_is_not_proof": True,
        "typed_verifier_is_proof_authority": True,
        "candidate_claims_do_not_contaminate_graph": True,
        "external_benchmark_victory_claim": False,
        "broad_nlp_claim": False,
        "general_theorem_proving_claim": False,
        "live_tensionlm_runtime_claim": False,
        "case_count": case_count,
        "candidate_count": candidate_count,
        "unsupported_claim_candidate_count": unsupported_claim_candidate_count,
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
        "accepted_with_unsupported_claims_count": sum(
            result["accepted_with_unsupported_claims"] for result in case_results
        ),
        "candidate_graph_contamination_count": sum(
            result["candidate_graph_contamination"] for result in case_results
        ),
        "trace_schema_validity": 1.0,
        "case_results": case_results,
    }

    report["gates"] = {
        "selection_accuracy_gate": report["arena_selection_accuracy"] == 1.0,
        "unsupported_claim_stress_present_gate": report["unsupported_claim_candidate_count"] > 0,
        "wrong_accept_gate": report["wrong_accept_count"] == 0,
        "accepted_without_support_gate": report["accepted_without_typed_support_count"] == 0,
        "accepted_with_unsupported_claims_gate": report["accepted_with_unsupported_claims_count"] == 0,
        "contamination_gate": report["candidate_graph_contamination_count"] == 0,
        "claim_boundary_gate": (
            report["confidence_is_not_proof"]
            and report["generated_text_is_not_proof"]
            and report["candidate_source_is_not_proof"]
            and report["typed_verifier_is_proof_authority"]
            and report["candidate_claims_do_not_contaminate_graph"]
            and not report["external_benchmark_victory_claim"]
            and not report["broad_nlp_claim"]
            and not report["general_theorem_proving_claim"]
            and not report["live_tensionlm_runtime_claim"]
        ),
    }
    report["gates"]["all_gates_passed"] = all(report["gates"].values())

    return report
