from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from ts_reasoner.runtime_kernel import normalize_claim


BELONGS_TO_RE = re.compile(r"^(.+?) belongs to (.+)$")
BELONG_TO_RE = re.compile(r"^(.+?) belong to (.+)$")
KIND_OF_RE = re.compile(r"^(.+?) (?:is|are) (?:a |an )?kind of (.+)$")
TYPE_OF_RE = re.compile(r"^(.+?) (?:is|are) (?:a |an )?type of (.+)$")
COUNTS_AS_RE = re.compile(r"^(.+?) counts as (.+)$")
COUNT_AS_RE = re.compile(r"^(.+?) count as (.+)$")
IMPLIES_RE = re.compile(r"^(.+?) implies (.+)$")
SUPPORTS_RE = re.compile(r"^(.+?) supports (.+)$")
SUPPORT_RE = re.compile(r"^(.+?) support (.+)$")
REQUIRES_RE = re.compile(r"^(.+?) requires (.+)$")
REQUIRE_RE = re.compile(r"^(.+?) require (.+)$")
CANNOT_BE_RE = re.compile(r"^(.+?) cannot be (.+)$")
CAN_NOT_BE_RE = re.compile(r"^(.+?) can not be (.+)$")
EXCLUDES_RE = re.compile(r"^(.+?) excludes (.+)$")
EXCLUDE_RE = re.compile(r"^(.+?) exclude (.+)$")


@dataclass(frozen=True)
class RelationPhraseParse:
    surface_claim: str
    canonical_claim: str
    parse_status: str
    quantifier: str
    subject: str
    predicate: str
    relation: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(text: str) -> str:
    cleaned = normalize_claim(text)
    cleaned = cleaned.strip(" .?!;:")
    cleaned = cleaned.replace("'", "")
    cleaned = " ".join(cleaned.split())
    return cleaned


def _strip_article(text: str) -> str:
    text = " ".join(text.strip().split())
    for prefix in ("a ", "an ", "the "):
        if text.startswith(prefix):
            return text[len(prefix):]
    return text


def _pluralish(text: str) -> str:
    text = _strip_article(text)
    if not text:
        return text
    # Keep conservative. Do not try real morphology; just avoid "a/an/the".
    return text


def _result(
    *,
    surface_claim: str,
    quantifier: str,
    subject: str,
    predicate: str,
    relation: str,
) -> RelationPhraseParse:
    subject = _pluralish(subject)
    predicate = _pluralish(predicate)
    if not subject or not predicate:
        return RelationPhraseParse(
            surface_claim=surface_claim,
            canonical_claim=surface_claim,
            parse_status="unparsed",
            quantifier="",
            subject="",
            predicate="",
            relation=relation,
            reason="empty_subject_or_predicate",
        )

    canonical = f"{quantifier} {subject} are {predicate}"
    return RelationPhraseParse(
        surface_claim=surface_claim,
        canonical_claim=canonical,
        parse_status="parsed",
        quantifier=quantifier,
        subject=subject,
        predicate=predicate,
        relation=relation,
    )


def parse_relation_phrase(text: str) -> dict[str, Any]:
    surface = _clean(text)
    if not surface:
        return RelationPhraseParse("", "", "unparsed", "", "", "", "", "empty_claim").to_dict()

    positive_patterns: list[tuple[str, re.Pattern[str]]] = [
        ("belongs_to", BELONGS_TO_RE),
        ("belong_to", BELONG_TO_RE),
        ("kind_of", KIND_OF_RE),
        ("type_of", TYPE_OF_RE),
        ("counts_as", COUNTS_AS_RE),
        ("count_as", COUNT_AS_RE),
        ("implies", IMPLIES_RE),
        ("supports", SUPPORTS_RE),
        ("support", SUPPORT_RE),
        ("requires", REQUIRES_RE),
        ("require", REQUIRE_RE),
    ]

    for relation, pattern in positive_patterns:
        match = pattern.match(surface)
        if match:
            return _result(
                surface_claim=surface,
                quantifier="all",
                subject=match.group(1),
                predicate=match.group(2),
                relation=relation,
            ).to_dict()

    negative_patterns: list[tuple[str, re.Pattern[str]]] = [
        ("cannot_be", CANNOT_BE_RE),
        ("can_not_be", CAN_NOT_BE_RE),
        ("excludes", EXCLUDES_RE),
        ("exclude", EXCLUDE_RE),
    ]

    for relation, pattern in negative_patterns:
        match = pattern.match(surface)
        if match:
            return _result(
                surface_claim=surface,
                quantifier="no",
                subject=match.group(1),
                predicate=match.group(2),
                relation=relation,
            ).to_dict()

    return RelationPhraseParse(
        surface_claim=surface,
        canonical_claim=surface,
        parse_status="unparsed",
        quantifier="",
        subject="",
        predicate="",
        relation="",
        reason="unsupported_relation_phrase",
    ).to_dict()


def canonicalize_relation_phrase(text: str) -> str:
    parsed = parse_relation_phrase(text)
    if parsed["parse_status"] == "parsed":
        return str(parsed["canonical_claim"])
    return _clean(text)
