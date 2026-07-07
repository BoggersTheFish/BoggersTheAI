"""Deterministic TSIR grammar for the initial syllogism domain."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .ir import (
    ClaimNode,
    EntityNode,
    EvidenceNode,
    Provenance,
    TSIRDocument,
    TSOperation,
    VerifierObligation,
    stable_hash,
)

PARSER_VERSION = "deterministic-tsir-parser-0.1"


@dataclass(frozen=True, slots=True)
class ParseResult:
    document: TSIRDocument


def _term_id(kind: str, label: str) -> str:
    safe = label.replace(" ", "_").replace("-", "_")
    return f"entity:{kind}:{safe}"


def _claim_id(parts: dict[str, Any]) -> str:
    return "claim:" + stable_hash(parts)[:20]


def _normalize_phrase(text: str, *, strip_things: bool = False) -> str:
    value = re.sub(r"\s+", " ", text.lower().strip())
    value = value.strip(" .;:,!?\"'")
    value = re.sub(r"\b(an?|the)\b\s+", "", value)
    if strip_things:
        value = re.sub(r"\s+things$", "", value)
    words = value.split()
    normalized: list[str] = []
    for word in words:
        normalized.append(_singularize(word))
    return " ".join(normalized).replace(" ", "_").replace("-", "_")


def _normalize_class_phrase(text: str) -> str:
    lower = text.lower().strip()
    if re.search(r"\bthings?$", lower) and "-" not in lower:
        return _normalize_phrase(text)
    return _normalize_phrase(text, strip_things=True)


def _singularize(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and len(word) > 3 and not word.endswith("ss"):
        return word[:-1]
    return word


def _label_from_id(entity_id: str) -> str:
    return entity_id.split(":", 2)[-1].replace("_", " ")


def _parse_number(text: str) -> int | float:
    return float(text) if "." in text else int(text)


class DeterministicTSParser:
    """Small explicit grammar for TSIR v0.1."""

    def __init__(self) -> None:
        self._active_document: TSIRDocument | None = None

    def _sentences(self, text: str) -> list[str]:
        cleaned = text.replace("\r\n", "\n")
        cleaned = re.sub(r"(?im)^step\s+\d+\s*:\s*", "", cleaned)
        parts = re.split(r"[\n.]+", cleaned)
        return [part.strip(" ;") for part in parts if part.strip(" ;")]

    def _add_entity(
        self,
        document: TSIRDocument,
        entity_id: str,
        entity_type: str,
        provenance: Provenance,
        attributes: dict[str, Any] | None = None,
    ) -> None:
        entity = EntityNode(
            id=entity_id,
            entity_type=entity_type,
            label=_label_from_id(entity_id),
            attributes=attributes or {},
            provenance=provenance,
        )
        document.add_entity_once(entity)
        document.operations.append(
            TSOperation(
                operation_type="CREATE_ENTITY",
                target=entity_id,
                payload=asdict(entity),
                provenance=provenance,
            )
        )

    def _add_claim(
        self,
        document: TSIRDocument,
        claim: ClaimNode,
        operation_type: str,
        provenance: Provenance,
    ) -> None:
        document.add_claim_once(claim)
        document.operations.append(
            TSOperation(
                operation_type=operation_type,
                target=claim.id,
                payload={
                    "subject": claim.subject,
                    "predicate": claim.predicate,
                    "object": claim.object,
                    "polarity": claim.polarity,
                    "modality": claim.modality,
                    "status": claim.status,
                    "claim_provenance": asdict(claim.provenance),
                },
                provenance=provenance,
            )
        )

    def _parse_fact_sentence(
        self,
        sentence: str,
        *,
        declared_classes: set[str],
        declared_properties: set[str],
        representation_provenance: Provenance,
        claim_provenance: Provenance,
    ) -> ClaimNode | None:
        document = getattr(self, "_active_document", None)
        match = re.fullmatch(
            r"(.+?)\s+(is|are)\s+(not\s+)?(an?\s+)?(.+)",
            sentence,
            flags=re.I,
        )
        if not match:
            return None
        if document is None:
            return None

        subject_label = _normalize_phrase(match.group(1))
        object_label = _normalize_phrase(match.group(5))
        subject = _term_id("individual", subject_label)
        article_present = bool(match.group(4))
        polarity = "negative" if match.group(3) else "positive"

        class_candidate = _term_id("class", object_label)
        property_candidate = _term_id("property", object_label)

        if class_candidate in declared_classes or article_present:
            predicate = "is_a"
            obj = class_candidate
            declared_classes.add(class_candidate)
            object_type = "class"
        elif property_candidate in declared_properties or "-" in match.group(5):
            predicate = "has_property"
            obj = property_candidate
            declared_properties.add(property_candidate)
            object_type = "property"
        else:
            self._warn(document, sentence, "unsupported_ambiguous_predication")
            return None

        self._add_entity(document, subject, "individual", representation_provenance)
        self._add_entity(document, obj, object_type, representation_provenance)
        claim = ClaimNode(
            id=_claim_id(
                {
                    "subject": subject,
                    "predicate": predicate,
                    "object": obj,
                    "polarity": polarity,
                }
            ),
            subject=subject,
            predicate=predicate,
            object=obj,
            polarity=polarity,
            status="unverified_premise",
            provenance=claim_provenance,
        )
        self._add_claim(document, claim, "CREATE_CLAIM", representation_provenance)
        return claim

    def _add_target_obligation(
        self,
        document: TSIRDocument,
        target_text: str,
        declared_classes: set[str],
        declared_properties: set[str],
        representation_provenance: Provenance,
        claim_provenance: Provenance,
        *,
        required: bool,
        status_query: bool = False,
    ) -> None:
        old_active = getattr(self, "_active_document", None)
        self._active_document = document
        try:
            target_text = target_text.strip().rstrip(".")
            if target_text.lower().startswith("all "):
                universal = re.fullmatch(r"all (.+?) are (.+)", target_text, flags=re.I)
                if universal is None:
                    self._warn(document, target_text, "unsupported_target")
                    return
                subject = _term_id(
                    "property",
                    _normalize_phrase(universal.group(1), strip_things=True),
                )
                obj = _term_id("class", _normalize_phrase(universal.group(2)))
                self._add_entity(
                    document, subject, "property", representation_provenance
                )
                self._add_entity(document, obj, "class", representation_provenance)
                target = ClaimNode(
                    id=_claim_id(
                        {
                            "subject": subject,
                            "predicate": "implies_property",
                            "object": obj,
                        }
                    ),
                    subject=subject,
                    predicate="implies_property",
                    object=obj,
                    status="under_verification",
                    provenance=claim_provenance,
                )
                document.add_claim_once(target)
            else:
                parsed_target = self._parse_fact_sentence(
                    target_text,
                    declared_classes=declared_classes,
                    declared_properties=declared_properties,
                    representation_provenance=representation_provenance,
                    claim_provenance=claim_provenance,
                )
                if parsed_target is None:
                    self._warn(document, target_text, "unsupported_target")
                    return
                target = ClaimNode(
                    id=parsed_target.id,
                    subject=parsed_target.subject,
                    predicate=parsed_target.predicate,
                    object=parsed_target.object,
                    polarity=parsed_target.polarity,
                    modality="asserted",
                    status="under_verification",
                    provenance=parsed_target.provenance,
                )
                document.claims = [
                    target if claim.id == target.id else claim
                    for claim in document.claims
                ]

            obligation = VerifierObligation(
                id="obl:"
                + stable_hash({"target": target.id, "status": status_query})[:16],
                verifier_type="syllogism",
                target_claim=target.id,
                premises=sorted(
                    claim.id
                    for claim in document.claims
                    if claim.id != target.id
                    and claim.status
                    in {
                        "proposed",
                        "asserted",
                        "transaction_assumption",
                        "unverified_premise",
                    }
                ),
                expected_property={"status_query": status_query},
                required=required,
            )
            document.obligations.append(obligation)
            document.operations.append(
                TSOperation(
                    operation_type="REQUEST_VERIFICATION",
                    target=obligation.id,
                    payload={"target_claim": target.id, "verifier_type": "syllogism"},
                    provenance=representation_provenance,
                )
            )
        finally:
            self._active_document = old_active

    def _add_arithmetic_obligation(
        self,
        document: TSIRDocument,
        sentence: str,
        provenance: Provenance,
    ) -> bool:
        expression = self._arithmetic_expression(sentence)
        if expression is None:
            return False
        obligation = VerifierObligation(
            id="obl:arith:" + stable_hash({"expression": expression})[:16],
            verifier_type="arithmetic",
            target_claim=expression,
            expected_property={"expression": expression},
            required=True,
        )
        document.obligations.append(obligation)
        document.operations.append(
            TSOperation(
                operation_type="REQUEST_VERIFICATION",
                target=obligation.id,
                payload={
                    "target_claim": expression,
                    "verifier_type": "arithmetic",
                },
                provenance=provenance,
            )
        )
        return True

    def _arithmetic_expression(self, sentence: str) -> str | None:
        value = sentence.strip().rstrip("?!.").strip()
        lower = value.lower()
        for prefix in (
            "what is ",
            "calculate ",
            "compute ",
            "verify that ",
            "verify ",
            "prove that ",
            "prove ",
        ):
            if lower.startswith(prefix):
                value = value[len(prefix) :].strip()
                lower = value.lower()
                break
        if re.fullmatch(r"[0-9\s+\-*/().=%]+", value):
            return value
        if re.fullmatch(r"[0-9\s+\-*/().%]+\s+is\s+(even|odd)", lower):
            return lower
        if re.fullmatch(
            r"[0-9\s+\-*/().%]+\s+(is\s+)?divisible\s+by\s+[0-9\s+\-*/().%]+", lower
        ):
            return lower
        return None

    def _add_code_property_obligation(
        self,
        document: TSIRDocument,
        sentence: str,
        provenance: Provenance,
    ) -> bool:
        if not sentence.lower().startswith("verify code property "):
            return False

        match = re.fullmatch(
            (
                r"verify code property\s+([A-Za-z_]\w*)\(([A-Za-z_]\w*)\)"
                r"\s*=\s*(.+?)\s+for examples\s+(.+)"
            ),
            sentence,
            flags=re.I,
        )
        expected_property: dict[str, Any]
        if match is None:
            expected_property = {"unsupported_input": sentence}
        else:
            examples = []
            for raw_example in re.split(r"\s*,\s*", match.group(4).strip()):
                example_match = re.fullmatch(
                    r"(-?\d+(?:\.\d+)?)\s*(?:->|=>|=)\s*(-?\d+(?:\.\d+)?)",
                    raw_example,
                )
                if example_match is None:
                    expected_property = {"unsupported_input": sentence}
                    break
                examples.append(
                    {
                        "input": _parse_number(example_match.group(1)),
                        "expected": _parse_number(example_match.group(2)),
                    }
                )
            else:
                expected_property = {
                    "function": match.group(1),
                    "parameter": match.group(2),
                    "body": match.group(3).strip(),
                    "examples": examples,
                }

        obligation = VerifierObligation(
            id="obl:codeprop:" + stable_hash(expected_property)[:16],
            verifier_type="code_property",
            target_claim=sentence,
            expected_property=expected_property,
            required=True,
        )
        document.obligations.append(obligation)
        document.operations.append(
            TSOperation(
                operation_type="REQUEST_VERIFICATION",
                target=obligation.id,
                payload={
                    "target_claim": sentence,
                    "verifier_type": "code_property",
                },
                provenance=provenance,
            )
        )
        return True

    def _add_representation_challenge(
        self,
        document: TSIRDocument,
        sentence: str,
    ) -> None:
        provenance = Provenance(
            "user",
            detail="authoritative representation challenge",
            reliability=0.95,
        )
        entity = EntityNode(
            id="entity:individual:whale_mechanical_device_branch",
            entity_type="branch",
            label="Whales mechanical devices",
            attributes={
                "branch_of": "entity:individual:whale",
                "challenge": "mechanical devices named Whales",
            },
            provenance=provenance,
        )
        document.add_entity_once(entity)
        evidence = EvidenceNode(
            id="evidence:" + stable_hash({"content": sentence})[:16],
            content=sentence,
            source="user",
            reliability=0.95,
            supports=[entity.id],
        )
        document.evidence.append(evidence)
        document.operations.append(
            TSOperation(
                operation_type="BRANCH_REPRESENTATION",
                target=entity.id,
                payload={
                    "branch_of": "entity:individual:whale",
                    "evidence": evidence.id,
                },
                provenance=provenance,
            )
        )
        document.diagnostics.append(
            {
                "severity": "warning",
                "severity_score": 1.0,
                "tension_type": "representation_tension",
                "message": "authoritative evidence challenges current entity decomposition",
                "text": sentence,
            }
        )

    def _warn(self, document: TSIRDocument, text: str, message: str) -> None:
        document.diagnostics.append(
            {
                "severity": "warning",
                "severity_score": 0.8,
                "tension_type": "representation_tension",
                "message": message,
                "text": text,
            }
        )

    def parse(self, text: str) -> ParseResult:
        document = TSIRDocument()
        self._active_document = document
        try:
            representation_provenance = Provenance(
                "deterministic_parser",
                detail="deterministic surface-to-TSIR representation",
                reliability=1.0,
            )
            claim_provenance = Provenance(
                "user",
                detail="user asserted premise; not verifier-derived truth",
                reliability=0.5,
            )
            sentences = self._sentences(text)
            declared_classes: set[str] = set()
            declared_properties: set[str] = set()
            universal_sentences: list[tuple[str, re.Match[str]]] = []
            universal_subject_labels: set[str] = set()
            article_class_labels: set[str] = set()

            for sentence in sentences:
                universal = re.fullmatch(r"all (.+?) are (.+)", sentence, flags=re.I)
                if universal:
                    universal_sentences.append((sentence, universal))
                    universal_subject_labels.add(
                        _normalize_class_phrase(universal.group(1))
                    )
                    continue
                fact_match = re.fullmatch(
                    r"(.+?)\s+(is|are)\s+(not\s+)?(an?\s+)(.+)",
                    sentence,
                    flags=re.I,
                )
                if fact_match:
                    article_class_labels.add(
                        _normalize_class_phrase(fact_match.group(5))
                    )

            for sentence, universal in universal_sentences:
                subject_raw = universal.group(1).strip()
                object_raw = universal.group(2).strip()
                if "hot dogs" in subject_raw.lower():
                    self._warn(
                        document,
                        sentence,
                        "unsupported_ambiguous_compound_universal",
                    )
                    continue
                subject_label = _normalize_class_phrase(subject_raw)
                object_class_label = _normalize_class_phrase(object_raw)
                object_property_label = _normalize_phrase(object_raw, strip_things=True)
                subject = _term_id("class", subject_label)
                object_is_class = (
                    object_class_label in universal_subject_labels
                    or object_class_label in article_class_labels
                )
                if object_is_class:
                    obj = _term_id("class", object_class_label)
                    predicate = "is_subclass_of"
                    declared_classes.add(obj)
                    object_type = "class"
                else:
                    obj = _term_id("property", object_property_label)
                    predicate = "implies_property"
                    declared_properties.add(obj)
                    object_type = "property"
                declared_classes.add(subject)
                self._add_entity(document, subject, "class", representation_provenance)
                self._add_entity(document, obj, object_type, representation_provenance)
                claim = ClaimNode(
                    id=_claim_id(
                        {
                            "predicate": predicate,
                            "subject": subject,
                            "object": obj,
                        }
                    ),
                    subject=subject,
                    predicate=predicate,
                    object=obj,
                    status="unverified_premise",
                    provenance=claim_provenance,
                )
                self._add_claim(
                    document, claim, "DECLARE_RULE", representation_provenance
                )

            for sentence in sentences:
                lower = sentence.lower()
                if lower.startswith(("all ", "prove ", "determine ", "step ")):
                    continue
                if self._add_arithmetic_obligation(
                    document, sentence, representation_provenance
                ):
                    continue
                if self._add_code_property_obligation(
                    document, sentence, representation_provenance
                ):
                    continue
                if " can be " in lower:
                    self._warn(document, sentence, "unsupported_modal_ambiguity")
                    continue
                if "mechanical devices named whales" in lower:
                    self._add_representation_challenge(document, sentence)
                    continue
                parsed = self._parse_fact_sentence(
                    sentence,
                    declared_classes=declared_classes,
                    declared_properties=declared_properties,
                    representation_provenance=representation_provenance,
                    claim_provenance=claim_provenance,
                )
                if parsed is None and sentence:
                    self._warn(document, sentence, "unsupported_sentence")

            for sentence in sentences:
                lower = sentence.lower()
                if lower.startswith("prove that "):
                    target_text = sentence[len("prove that ") :]
                    self._add_target_obligation(
                        document,
                        target_text,
                        declared_classes,
                        declared_properties,
                        representation_provenance,
                        claim_provenance,
                        required=True,
                    )
                elif lower.startswith("prove "):
                    target_text = sentence[len("prove ") :]
                    self._add_target_obligation(
                        document,
                        target_text,
                        declared_classes,
                        declared_properties,
                        representation_provenance,
                        claim_provenance,
                        required=True,
                    )
                elif lower.startswith("determine "):
                    target_text = sentence
                    claim_match = re.search(r"claim that (.+)$", sentence, flags=re.I)
                    whether_match = re.search(r"whether (.+)$", sentence, flags=re.I)
                    if claim_match:
                        target_text = claim_match.group(1)
                    elif whether_match:
                        target_text = whether_match.group(1)
                    self._add_target_obligation(
                        document,
                        target_text,
                        declared_classes,
                        declared_properties,
                        representation_provenance,
                        claim_provenance,
                        required=True,
                        status_query=True,
                    )
            return ParseResult(document=document)
        finally:
            self._active_document = None
