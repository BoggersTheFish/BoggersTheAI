"""Bounded claim decomposer for generated answer text.

This is not broad NLP. It extracts simple all-X-are-Y relation claims from
messy candidate answers so the verifier-first arena can treat generated text
as candidate data, not proof.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ts_reasoner.answer_arena import (
    ALL_RELATION_RE,
    Relation,
    classify_answer,
    extract_question_relation,
    normalize_term,
)


@dataclass(frozen=True)
class DecomposedClaim:
    answer_type: str
    extracted_relation: Relation | None
    extraction_status: str
    reason: str


def extract_all_relations(text: str) -> list[Relation]:
    relations: list[Relation] = []

    for match in ALL_RELATION_RE.finditer(text):
        relation = Relation(
            normalize_term(match.group(1)),
            normalize_term(match.group(2)),
        )
        relations.append(relation)

    return relations


def choose_relation_for_question(
    relations: list[Relation],
    question_relation: Relation | None,
) -> tuple[Relation | None, str]:
    if question_relation and question_relation in relations:
        return question_relation, "question_matching_relation"

    if relations:
        return relations[0], "non_matching_relation"

    return None, "unparsed"


def decompose_candidate_answer(text: str, question: str | None = None) -> DecomposedClaim:
    answer_type = classify_answer(text)
    question_relation = extract_question_relation(question) if question else None

    if answer_type == "abstain":
        return DecomposedClaim(
            answer_type="abstain",
            extracted_relation=None,
            extraction_status="no_claim",
            reason="candidate abstains, so no positive claim is extracted",
        )

    relations = extract_all_relations(text)
    chosen_relation, relation_status = choose_relation_for_question(relations, question_relation)

    # Negative answers are still decomposed for audit, but cannot become proof support.
    if answer_type == "no":
        if chosen_relation:
            return DecomposedClaim(
                answer_type="no",
                extracted_relation=chosen_relation,
                extraction_status=f"negative_{relation_status}",
                reason="negative candidate claim extracted for audit only; negative text is not proof support",
            )

        if question_relation:
            return DecomposedClaim(
                answer_type="no",
                extracted_relation=question_relation,
                extraction_status="negative_question_relation_fallback",
                reason="negative answer mapped to the question relation for audit only",
            )

        return DecomposedClaim(
            answer_type="no",
            extracted_relation=None,
            extraction_status="negative_claim_unparsed",
            reason="negative answer had no bounded relation to extract",
        )

    # Positive answers: prefer a relation that exactly answers the question.
    if chosen_relation and question_relation and chosen_relation == question_relation:
        return DecomposedClaim(
            answer_type=answer_type,
            extracted_relation=chosen_relation,
            extraction_status="question_matching_relation",
            reason="candidate text contained a bounded relation matching the question relation",
        )

    # If the candidate states relation claims but none answer the question, preserve that mismatch.
    if chosen_relation:
        return DecomposedClaim(
            answer_type=answer_type,
            extracted_relation=chosen_relation,
            extraction_status="non_matching_relation",
            reason="candidate text contained a bounded relation, but it did not match the question relation",
        )

    # Bare yes-answer fallback, only when no explicit relation was stated.
    if answer_type == "yes" and question_relation:
        return DecomposedClaim(
            answer_type=answer_type,
            extracted_relation=question_relation,
            extraction_status="question_relation_fallback",
            reason="bare yes-answer mapped to the question relation in bounded arena",
        )

    return DecomposedClaim(
        answer_type=answer_type,
        extracted_relation=None,
        extraction_status="unparsed",
        reason="no bounded all-X-are-Y relation could be extracted",
    )


def decomposed_claim_to_dict(claim: DecomposedClaim) -> dict[str, Any]:
    return {
        "answer_type": claim.answer_type,
        "extraction_status": claim.extraction_status,
        "reason": claim.reason,
        "extracted_relation": None
        if claim.extracted_relation is None
        else {
            "subject": claim.extracted_relation.subject,
            "object": claim.extracted_relation.object,
        },
    }
