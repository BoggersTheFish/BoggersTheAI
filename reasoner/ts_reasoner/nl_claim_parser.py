"""Bounded natural-language claim ingestion for TS-Reasoner.

This module intentionally does not claim general natural-language understanding.
It parses a small supported surface of syllogistic / graph-claim language into
canonical TS-Reasoner relation claims, then delegates verification to the
existing candidate bridge and typed channels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .candidates import CandidateClaim
from .candidate_bridge import run_tensionlm_candidate_bridge
from .tensionlm_adapter import normalize_candidate_claim_text


@dataclass(frozen=True)
class ParsedNaturalLanguageClaim:
    input_text: str
    premises: list[str]
    candidate_claim: str | None
    parse_success: bool
    parse_status: str
    rejected_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_text": self.input_text,
            "premises": list(self.premises),
            "candidate_claim": self.candidate_claim,
            "parse_success": self.parse_success,
            "parse_status": self.parse_status,
            "rejected_reason": self.rejected_reason,
        }


_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_QUESTION_PREFIX_RE = re.compile(
    r"^(?:therefore|so|then|can\s+we\s+conclude|does\s+it\s+follow\s+that|is\s+it\s+true\s+that)\s+",
    re.IGNORECASE,
)
_QUERY_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "all",
        re.compile(
            r"^(?:are|is)\s+(?:all|every|each)\s+"
            r"(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
            r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\??$",
            re.IGNORECASE,
        ),
    ),
    (
        "all",
        re.compile(
            r"^(?:do|does)\s+(?:all|every|each)\s+"
            r"(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
            r"(?:belong\s+to|fall\s+under|count\s+as|become|be|are)\s+"
            r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\??$",
            re.IGNORECASE,
        ),
    ),
    (
        "some",
        re.compile(
            r"^(?:are|is)\s+(?:some|at\s+least\s+one)\s+"
            r"(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
            r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\??$",
            re.IGNORECASE,
        ),
    ),
    (
        "no",
        re.compile(
            r"^(?:are|is)\s+(?:no|none\s+of\s+the)\s+"
            r"(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+"
            r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\??$",
            re.IGNORECASE,
        ),
    ),
]


def parse_natural_language_claim(input_text: str) -> ParsedNaturalLanguageClaim:
    """Parse bounded NL into canonical premises and one candidate claim.

    Supported examples:
    - "All dogs are mammals. All mammals are animals. Are all dogs animals?"
    - "Every raven belongs to bird. Each bird falls under animal. Can we conclude all raven are animal?"
    - "All A are B. Some B are C. Are all A C?"

    Unsupported/malformed input returns parse_success=False and is handled as a
    safe abstention by run_natural_language_claim_ingestion.
    """

    sentences = _split_sentences(input_text)
    if len(sentences) < 2:
        return ParsedNaturalLanguageClaim(
            input_text=input_text,
            premises=[],
            candidate_claim=None,
            parse_success=False,
            parse_status="unparsed",
            rejected_reason="expected at least one premise and one query sentence",
        )

    query_sentence = sentences[-1]
    premise_sentences = sentences[:-1]

    premises: list[str] = []
    for sentence in premise_sentences:
        normalized, status = normalize_candidate_claim_text(sentence)
        if status == "unparsed":
            return ParsedNaturalLanguageClaim(
                input_text=input_text,
                premises=premises,
                candidate_claim=None,
                parse_success=False,
                parse_status="unparsed",
                rejected_reason=f"premise could not be parsed: {sentence}",
            )
        premises.append(normalized)

    candidate_claim = _parse_query_sentence(query_sentence)
    if candidate_claim is None:
        normalized, status = normalize_candidate_claim_text(query_sentence)
        if status == "unparsed":
            return ParsedNaturalLanguageClaim(
                input_text=input_text,
                premises=premises,
                candidate_claim=None,
                parse_success=False,
                parse_status="unparsed",
                rejected_reason=f"query could not be parsed: {query_sentence}",
            )
        candidate_claim = normalized

    return ParsedNaturalLanguageClaim(
        input_text=input_text,
        premises=premises,
        candidate_claim=candidate_claim,
        parse_success=True,
        parse_status="bounded_nl_claim",
        rejected_reason=None,
    )


def run_natural_language_claim_ingestion(input_text: str, case_id: str = "nl_claim_case") -> dict[str, Any]:
    """Parse bounded NL and verify the parsed candidate through typed channels."""

    parsed = parse_natural_language_claim(input_text)
    if not parsed.parse_success or parsed.candidate_claim is None:
        return {
            "case_id": case_id,
            "input_text": input_text,
            "parser": parsed.to_dict(),
            "verification": {
                "accepted": [],
                "rejected": [],
                "abstained": [],
                "channels": {"nl_claim_parser": "safe abstain on unsupported or malformed bounded NL input"},
                "candidate_results": [],
            },
            "trace_receipt": {
                "role": "Bounded NL parser extracts candidate data. TS-Reasoner typed channels verify.",
                "candidate_count": 0,
                "accepted_count": 0,
                "rejected_count": 0,
                "abstained_count": 1,
                "provenance_preserved": True,
                "parse_success": False,
            },
            "status": "abstained",
            "reason": parsed.rejected_reason,
        }

    candidate = CandidateClaim(
        candidate_id=f"{case_id}_candidate_1",
        claim=parsed.candidate_claim,
        source="natural_language_claim_parser",
        confidence=0.5,
        raw_output=input_text,
        metadata={
            "adapter": "bounded_natural_language_claim_ingestion",
            "parse_status": parsed.parse_status,
            "case_id": case_id,
        },
    )

    payload = run_tensionlm_candidate_bridge(
        input_text,
        parsed.premises,
        mode="external",
        external_hook=lambda _text, _premises: [candidate],
    )
    payload["case_id"] = case_id
    payload["parser"] = parsed.to_dict()
    results = payload["verification"]["candidate_results"]
    payload["status"] = results[0]["status"] if results else "abstained"
    payload["reason"] = results[0]["reason"] if results else "no candidate result"
    return payload


def _split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.strip().split())
    if not normalized:
        return []
    raw_parts = [part.strip() for part in _BOUNDARY_RE.split(normalized) if part.strip()]
    return [part.rstrip(".!?").strip() for part in raw_parts if part.rstrip(".!?").strip()]


def _parse_query_sentence(sentence: str) -> str | None:
    cleaned = _QUESTION_PREFIX_RE.sub("", sentence.strip()).strip()
    cleaned = cleaned.rstrip(".!?").strip()
    normalized, status = normalize_candidate_claim_text(cleaned)
    if status != "unparsed":
        return normalized

    for quantifier, pattern in _QUERY_PATNS():
        match = pattern.match(cleaned)
        if match:
            return f"{quantifier.capitalize()} {match.group('subject')} are {match.group('predicate')}"
    return None


def _QUERY_PATNS() -> list[tuple[str, re.Pattern[str]]]:
    """Small helper kept separate so tests can monkey-patch if needed."""
    return _QUERY_PATTERNS
