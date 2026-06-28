from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from ts_reasoner.relation_phrase_parser import parse_relation_phrase
from ts_reasoner.runtime_kernel import normalize_claim

ALL_ARE_RE = re.compile(r"^all (.+?) are (.+)$")
ALL_IS_RE = re.compile(r"^all (.+?) is (.+)$")
EVERY_RE = re.compile(r"^(every|each|any) (.+?) (is|are) (.+)$")
NO_RE = re.compile(r"^no (.+?) (is|are) (.+)$")
NOT_RE = re.compile(r"^(.+?) (is|are) not (.+)$")
NOTHING_THAT_IS_RE = re.compile(r"^nothing that is (.+?) (is|are) (.+)$")
BARE_RE = re.compile(r"^(.+?) (is|are) (.+)$")


@dataclass(frozen=True)
class NormalizedClaimSurface:
    surface_claim: str
    canonical_claim: str
    parse_status: str
    quantifier: str
    subject: str
    predicate: str
    copula: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean(text: str) -> str:
    cleaned = normalize_claim(text)
    cleaned = cleaned.strip(" .?!;:")
    cleaned = cleaned.replace("'", "")
    cleaned = " ".join(cleaned.split())
    return cleaned


def _result(
    *,
    surface_claim: str,
    quantifier: str,
    subject: str,
    predicate: str,
    copula: str,
) -> NormalizedClaimSurface:
    subject = " ".join(subject.strip().split())
    predicate = " ".join(predicate.strip().split())
    if not subject or not predicate:
        return NormalizedClaimSurface(
            surface_claim=surface_claim,
            canonical_claim=surface_claim,
            parse_status="unparsed",
            quantifier="",
            subject="",
            predicate="",
            copula=copula,
            reason="empty_subject_or_predicate",
        )

    canonical = f"{quantifier} {subject} are {predicate}"
    return NormalizedClaimSurface(
        surface_claim=surface_claim,
        canonical_claim=canonical,
        parse_status="parsed",
        quantifier=quantifier,
        subject=subject,
        predicate=predicate,
        copula=copula,
    )


def normalize_claim_surface(text: str) -> dict[str, Any]:
    surface = _clean(text)

    if not surface:
        return NormalizedClaimSurface(
            surface_claim="",
            canonical_claim="",
            parse_status="unparsed",
            quantifier="",
            subject="",
            predicate="",
            copula="",
            reason="empty_claim",
        ).to_dict()

    match = ALL_ARE_RE.match(surface)
    if match:
        return _result(
            surface_claim=surface,
            quantifier="all",
            subject=match.group(1),
            predicate=match.group(2),
            copula="are",
        ).to_dict()

    match = ALL_IS_RE.match(surface)
    if match:
        return _result(
            surface_claim=surface,
            quantifier="all",
            subject=match.group(1),
            predicate=match.group(2),
            copula="is",
        ).to_dict()

    match = EVERY_RE.match(surface)
    if match:
        return _result(
            surface_claim=surface,
            quantifier="all",
            subject=match.group(2),
            predicate=match.group(4),
            copula=match.group(3),
        ).to_dict()

    match = NO_RE.match(surface)
    if match:
        return _result(
            surface_claim=surface,
            quantifier="no",
            subject=match.group(1),
            predicate=match.group(3),
            copula=match.group(2),
        ).to_dict()

    match = NOTHING_THAT_IS_RE.match(surface)
    if match:
        return _result(
            surface_claim=surface,
            quantifier="no",
            subject=match.group(1),
            predicate=match.group(3),
            copula=match.group(2),
        ).to_dict()

    match = NOT_RE.match(surface)
    if match:
        return _result(
            surface_claim=surface,
            quantifier="no",
            subject=match.group(1),
            predicate=match.group(3),
            copula=match.group(2),
        ).to_dict()

    relation = parse_relation_phrase(surface)
    if relation["parse_status"] == "parsed":
        return NormalizedClaimSurface(
            surface_claim=surface,
            canonical_claim=str(relation["canonical_claim"]),
            parse_status="parsed",
            quantifier=str(relation["quantifier"]),
            subject=str(relation["subject"]),
            predicate=str(relation["predicate"]),
            copula=str(relation["relation"]),
        ).to_dict()

    match = BARE_RE.match(surface)
    if match:
        return _result(
            surface_claim=surface,
            quantifier="all",
            subject=match.group(1),
            predicate=match.group(3),
            copula=match.group(2),
        ).to_dict()

    return NormalizedClaimSurface(
        surface_claim=surface,
        canonical_claim=surface,
        parse_status="unparsed",
        quantifier="",
        subject="",
        predicate="",
        copula="",
        reason="unsupported_surface_form",
    ).to_dict()


def canonicalize_claim_surface(text: str) -> str:
    normalized = normalize_claim_surface(text)
    if normalized["parse_status"] == "parsed":
        return str(normalized["canonical_claim"])
    return _clean(text)
