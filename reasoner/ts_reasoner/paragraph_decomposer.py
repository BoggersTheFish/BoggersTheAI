from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from ts_reasoner.claim_normalizer import canonicalize_claim_surface, normalize_claim_surface
from ts_reasoner.runtime_kernel import normalize_claim
from ts_reasoner.support_path_verifier import parse_claim


SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
QUESTION_PREFIX_RE = re.compile(r"^(is|are|can|does|do|should|could|would)\b")
ARE_ALL_RE = re.compile(r"^are all (.+?) (.+)$")
ARE_RE = re.compile(r"^are (.+?) (.+)$")
IS_NOT_RE = re.compile(r"^is (.+?) not (.+)$")
ARE_NOT_RE = re.compile(r"^are (.+?) not (.+)$")
IS_RE = re.compile(r"^is (.+)$")
CAN_BE_RE = re.compile(r"^can (.+?) be (.+)$")
DOES_COUNT_AS_RE = re.compile(r"^does (.+?) count as (.+)$")
DOES_BELONG_TO_RE = re.compile(r"^does (.+?) belong to (.+)$")
DOES_REQUIRE_RE = re.compile(r"^does (.+?) require (.+)$")
DOES_SUPPORT_RE = re.compile(r"^does (.+?) support (.+)$")


@dataclass(frozen=True)
class ParagraphDecomposition:
    paragraph: str
    status: str
    premises: tuple[str, ...]
    candidate_claim: str
    question: str
    ignored_sentences: tuple[str, ...]
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["premises"] = list(self.premises)
        payload["ignored_sentences"] = list(self.ignored_sentences)
        return payload


def _clean(text: str) -> str:
    cleaned = normalize_claim(text)
    cleaned = cleaned.strip(" .?!;:")
    cleaned = " ".join(cleaned.split())
    return cleaned


def split_sentences(paragraph: str) -> list[str]:
    chunks = []
    for raw in SPLIT_RE.split(paragraph.strip()):
        cleaned = _clean(raw)
        if cleaned:
            chunks.append(cleaned)
    return chunks


def is_question(sentence: str) -> bool:
    return sentence.endswith("?") or bool(QUESTION_PREFIX_RE.match(_clean(sentence)))


def _canonical_statement(sentence: str) -> str | None:
    cleaned = _clean(sentence)
    if not cleaned:
        return None

    for prefix in (
        "therefore ",
        "given that ",
        "also ",
        "clearly ",
        "we know that ",
        "it is true that ",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()

    observed = normalize_claim_surface(cleaned)
    if observed["parse_status"] == "parsed":
        return str(observed["canonical_claim"])

    return None


def _known_terms(premises: list[str] | None) -> list[str]:
    terms: set[str] = set()
    for premise in premises or []:
        parsed = parse_claim(premise)
        if parsed is None:
            continue
        terms.add(parsed.subject)
        terms.add(parsed.predicate)
    return sorted(terms, key=len, reverse=True)


def _claim_from_tail_with_known_terms(tail: str, premises: list[str] | None) -> str | None:
    tail = _clean(tail)
    terms = _known_terms(premises)

    # Prefer terms already present in the premise graph. This fixes:
    # "is generated text untrusted material" -> subject "generated text",
    # predicate "untrusted material".
    for term in terms:
        if tail == term:
            continue
        if tail.startswith(term + " "):
            predicate = tail[len(term):].strip()
            if predicate:
                return canonicalize_claim_surface(f"{term} is {predicate}")

    # Fallback heuristic for standalone calls: split the phrase in half.
    words = tail.split()
    if len(words) >= 4 and len(words) % 2 == 0:
        midpoint = len(words) // 2
        subject = " ".join(words[:midpoint])
        predicate = " ".join(words[midpoint:])
        return canonicalize_claim_surface(f"{subject} is {predicate}")

    if len(words) >= 3:
        subject = " ".join(words[:-1])
        predicate = words[-1]
        return canonicalize_claim_surface(f"{subject} is {predicate}")

    return None


def question_to_claim(question: str, premises: list[str] | None = None) -> str | None:
    q = _clean(question)
    if not q:
        return None

    match = ARE_ALL_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"all {match.group(1)} are {match.group(2)}")

    match = ARE_NOT_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"{match.group(1)} are not {match.group(2)}")

    match = IS_NOT_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"{match.group(1)} is not {match.group(2)}")

    match = ARE_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"{match.group(1)} are {match.group(2)}")

    match = IS_RE.match(q)
    if match:
        return _claim_from_tail_with_known_terms(match.group(1), premises)

    match = CAN_BE_RE.match(q)
    if match:
        subject = match.group(1)
        predicate = match.group(2)
        if predicate.startswith("not "):
            return canonicalize_claim_surface(f"{subject} is not {predicate[4:]}")
        return canonicalize_claim_surface(f"{subject} is {predicate}")

    match = DOES_COUNT_AS_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"{match.group(1)} counts as {match.group(2)}")

    match = DOES_BELONG_TO_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"{match.group(1)} belongs to {match.group(2)}")

    match = DOES_REQUIRE_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"{match.group(1)} requires {match.group(2)}")

    match = DOES_SUPPORT_RE.match(q)
    if match:
        return canonicalize_claim_surface(f"{match.group(1)} supports {match.group(2)}")

    return None


def decompose_paragraph(paragraph: str) -> dict[str, Any]:
    sentences = split_sentences(paragraph)
    premises: list[str] = []
    ignored: list[str] = []
    questions: list[str] = []

    for sentence in sentences:
        if is_question(sentence):
            questions.append(sentence)
            continue

        premise = _canonical_statement(sentence)
        if premise is None:
            ignored.append(sentence)
        else:
            premises.append(premise)

    candidate_claim = ""
    selected_question = ""
    for question in questions:
        claim = question_to_claim(question, premises)
        if claim:
            candidate_claim = claim
            selected_question = question
            break
        ignored.append(question)

    if not premises and not candidate_claim:
        return ParagraphDecomposition(
            paragraph=paragraph,
            status="abstained",
            premises=(),
            candidate_claim="",
            question="",
            ignored_sentences=tuple(ignored),
            reason="no_parseable_premises_or_question",
        ).to_dict()

    if not candidate_claim:
        return ParagraphDecomposition(
            paragraph=paragraph,
            status="abstained",
            premises=tuple(premises),
            candidate_claim="",
            question="",
            ignored_sentences=tuple(ignored),
            reason="no_parseable_question",
        ).to_dict()

    return ParagraphDecomposition(
        paragraph=paragraph,
        status="parsed",
        premises=tuple(premises),
        candidate_claim=candidate_claim,
        question=selected_question,
        ignored_sentences=tuple(ignored),
    ).to_dict()
