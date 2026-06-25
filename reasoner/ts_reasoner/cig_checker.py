"""Claim-Interaction-Graph extraction and checks."""

from __future__ import annotations

import re
from typing import Dict, Iterable, List, Optional, Tuple

from .generator import extract_relations
from .proof_chain import has_universal_bridge
from .types import CIGCheck, Claim, ReasoningChain

NEGATION_RE = re.compile(
    r"\b(?P<subject>[A-Za-z][A-Za-z0-9_-]*)\s+(?:are|is)\s+not\s+"
    r"(?P<predicate>[A-Za-z][A-Za-z0-9_-]*)\b",
    re.IGNORECASE,
)


def normalize_statement(subject: Optional[str], predicate: Optional[str], quantifier: Optional[str], polarity: str) -> str:
    if not subject or not predicate:
        return ""
    prefix = quantifier or "claim"
    marker = "not " if polarity == "negative" and prefix != "no" else ""
    return f"{prefix} {subject.lower()} are {marker}{predicate.lower()}"


def extract_claims_from_text(text: str, source_step_id: str, dependencies: Iterable[str], confidence: float) -> List[Claim]:
    claims: List[Claim] = []
    for index, relation in enumerate(extract_relations(text)):
        polarity = "negative" if relation.quantifier == "no" else "positive"
        normalized = normalize_statement(relation.subject, relation.predicate, relation.quantifier, polarity)
        claims.append(
            Claim(
                claim_id=f"{source_step_id}:c{index + 1}",
                text=relation.text,
                normalized=normalized,
                source_step_id=source_step_id,
                subject=relation.subject,
                predicate=relation.predicate,
                quantifier=relation.quantifier,
                polarity=polarity,
                confidence=confidence,
                dependencies=list(dependencies),
            )
        )
    offset = len(claims)
    for index, match in enumerate(NEGATION_RE.finditer(text)):
        subject = match.group("subject")
        predicate = match.group("predicate")
        claims.append(
            Claim(
                claim_id=f"{source_step_id}:c{offset + index + 1}",
                text=match.group(0),
                normalized=normalize_statement(subject, predicate, None, "negative"),
                source_step_id=source_step_id,
                subject=subject,
                predicate=predicate,
                quantifier=None,
                polarity="negative",
                confidence=confidence,
                dependencies=list(dependencies),
            )
        )
    return claims


def _contradict(a: Claim, b: Claim) -> bool:
    if not a.subject or not a.predicate or not b.subject or not b.predicate:
        return False
    same_pair = a.subject.lower() == b.subject.lower() and a.predicate.lower() == b.predicate.lower()
    if not same_pair:
        return False
    if a.quantifier == "no" and b.quantifier in {"all", "some"}:
        return True
    if b.quantifier == "no" and a.quantifier in {"all", "some"}:
        return True
    return a.polarity != b.polarity


def _find_unsupported_claims(claims: List[Claim]) -> List[str]:
    premise_claims = [claim for claim in claims if claim.source_step_id.startswith("p")]
    unsupported: List[str] = []
    for claim in claims:
        if not claim.source_step_id.startswith("s"):
            continue
        if claim.quantifier is None or not claim.subject or not claim.predicate:
            continue
        if _claim_has_support(claim, premise_claims):
            continue
        unsupported.append(claim.claim_id)
    return unsupported


def _claim_has_support(claim: Claim, premise_claims: List[Claim]) -> bool:
    for premise in premise_claims:
        if (
            premise.quantifier == claim.quantifier
            and premise.subject
            and premise.predicate
            and premise.subject.lower() == claim.subject.lower()
            and premise.predicate.lower() == claim.predicate.lower()
        ):
            return True
    if claim.quantifier == "all":
        return has_universal_bridge(premise_claims, claim.subject, claim.predicate)
    if claim.quantifier == "some":
        for left in premise_claims:
            for right in premise_claims:
                if (
                    left.quantifier == "some"
                    and right.quantifier == "all"
                    and left.subject
                    and left.predicate
                    and right.subject
                    and right.predicate
                    and left.subject.lower() == claim.subject.lower()
                    and left.predicate.lower() == right.subject.lower()
                    and right.predicate.lower() == claim.predicate.lower()
                ):
                    return True
    return False


def _find_circular_steps(chain: ReasoningChain) -> List[str]:
    circular = []
    for step in chain.steps:
        if step.step_id in step.dependencies:
            circular.append(step.step_id)
            continue
        text = step.text.lower()
        if "because the conclusion" in text or "assume the conclusion" in text:
            circular.append(step.step_id)
    return circular


class CIGChecker:
    """Build a toy Claim-Interaction Graph from one reasoning chain."""

    def check(self, chain: ReasoningChain) -> CIGCheck:
        claims: List[Claim] = []
        dependencies: Dict[str, List[str]] = {}
        for step in chain.steps:
            dependencies[step.step_id] = list(step.dependencies)
            claims.extend(
                extract_claims_from_text(
                    step.text,
                    source_step_id=step.step_id,
                    dependencies=step.dependencies,
                    confidence=step.confidence,
                )
            )
        contradiction_pairs = self._contradiction_pairs(claims)
        return CIGCheck(
            chain_id=chain.chain_id,
            claims=claims,
            dependencies=dependencies,
            contradiction_pairs=contradiction_pairs,
            unsupported_claim_ids=_find_unsupported_claims(claims),
            circular_step_ids=_find_circular_steps(chain),
        )

    def _contradiction_pairs(self, claims: List[Claim]) -> List[List[str]]:
        pairs: List[List[str]] = []
        for left_index, left in enumerate(claims):
            for right in claims[left_index + 1 :]:
                if _contradict(left, right):
                    pairs.append([left.claim_id, right.claim_id])
        return pairs
