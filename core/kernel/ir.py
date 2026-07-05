"""Versioned TS intermediate representation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

TSIR_VERSION = "TSIR-0.1"

PROVENANCE_SOURCES = {
    "user",
    "deterministic_parser",
    "model_proposer",
    "tool",
    "database",
    "verifier",
    "BOGVM",
    "migration",
    "system_seed",
}

STATE_STATUSES = {
    "proposed",
    "sandboxed",
    "under_verification",
    "accepted",
    "rejected",
    "quarantined",
    "superseded",
    "branched",
    "abstained",
}

OPERATION_TYPES = {
    "CREATE_ENTITY",
    "CREATE_CLAIM",
    "ADD_SUPPORT",
    "ADD_INHIBITION",
    "DECLARE_RULE",
    "DERIVE_CLAIM",
    "RETRACT_CLAIM",
    "BRANCH_REPRESENTATION",
    "MERGE_REPRESENTATION",
    "REQUEST_VERIFICATION",
    "COMMIT_CLAIM",
    "QUARANTINE_CLAIM",
}


def canonical_json(payload: Any) -> str:
    """Serialize deterministically for hashing and receipts."""

    def _normalize(value: Any) -> Any:
        if is_dataclass(value):
            return _normalize(asdict(value))  # type: ignore[arg-type]
        if isinstance(value, dict):
            return {str(k): _normalize(value[k]) for k in sorted(value)}
        if isinstance(value, (list, tuple)):
            return [_normalize(item) for item in value]
        if isinstance(value, set):
            return sorted(_normalize(item) for item in value)
        return value

    return json.dumps(
        _normalize(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Provenance:
    source: str
    detail: str = ""
    reliability: float = 0.5

    def __post_init__(self) -> None:
        if self.source not in PROVENANCE_SOURCES:
            raise ValueError(f"unknown provenance source: {self.source}")
        if not 0.0 <= float(self.reliability) <= 1.0:
            raise ValueError("provenance reliability must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class EntityNode:
    id: str
    entity_type: str
    label: str
    attributes: dict[str, Any] = field(default_factory=dict)
    provenance: Provenance = field(
        default_factory=lambda: Provenance("deterministic_parser", reliability=1.0)
    )


@dataclass(frozen=True, slots=True)
class ClaimNode:
    id: str
    subject: str
    predicate: str
    object: str
    polarity: str = "positive"
    modality: str = "asserted"
    status: str = "proposed"
    provenance: Provenance = field(
        default_factory=lambda: Provenance("deterministic_parser", reliability=1.0)
    )

    def __post_init__(self) -> None:
        if self.polarity not in {"positive", "negative"}:
            raise ValueError("claim polarity must be positive or negative")
        if self.status not in STATE_STATUSES:
            raise ValueError(f"unknown claim status: {self.status}")


@dataclass(frozen=True, slots=True)
class RelationEdge:
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    direction: str = "directed"
    provenance: Provenance = field(
        default_factory=lambda: Provenance("deterministic_parser", reliability=1.0)
    )

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.weight) <= 1.0:
            raise ValueError("relation weight must be in [0, 1]")
        if self.direction not in {"directed", "undirected"}:
            raise ValueError("relation direction must be directed or undirected")


@dataclass(frozen=True, slots=True)
class EvidenceNode:
    id: str
    content: str
    source: str
    reliability: float
    supports: list[str] = field(default_factory=list)
    inhibits: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.reliability) <= 1.0:
            raise ValueError("evidence reliability must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class VerifierObligation:
    id: str
    verifier_type: str
    target_claim: str
    premises: list[str] = field(default_factory=list)
    expected_property: dict[str, Any] = field(default_factory=dict)
    required: bool = True


@dataclass(frozen=True, slots=True)
class TSOperation:
    operation_type: str
    target: str
    payload: dict[str, Any] = field(default_factory=dict)
    provenance: Provenance = field(
        default_factory=lambda: Provenance("deterministic_parser", reliability=1.0)
    )

    def __post_init__(self) -> None:
        if self.operation_type not in OPERATION_TYPES:
            raise ValueError(f"unknown TS operation: {self.operation_type}")


@dataclass(frozen=True, slots=True)
class ProofStep:
    rule_id: str
    consumed_premises: list[str]
    substitution: dict[str, str]
    produced_claim: str


@dataclass(frozen=True, slots=True)
class ProofObject:
    proof_type: str
    target_claim: str
    steps: list[ProofStep]
    exact_match: bool

    def hash(self) -> str:
        return stable_hash(self)


@dataclass(slots=True)
class TSIRDocument:
    entities: list[EntityNode] = field(default_factory=list)
    claims: list[ClaimNode] = field(default_factory=list)
    relations: list[RelationEdge] = field(default_factory=list)
    evidence: list[EvidenceNode] = field(default_factory=list)
    obligations: list[VerifierObligation] = field(default_factory=list)
    operations: list[TSOperation] = field(default_factory=list)
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    version: str = TSIR_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "entities": sorted(
                (asdict(entity) for entity in self.entities),
                key=lambda item: item["id"],
            ),
            "claims": sorted(
                (asdict(claim) for claim in self.claims), key=lambda item: item["id"]
            ),
            "relations": sorted(
                (asdict(edge) for edge in self.relations),
                key=lambda item: (
                    item["source"],
                    item["target"],
                    item["relation_type"],
                ),
            ),
            "evidence": sorted(
                (asdict(item) for item in self.evidence), key=lambda item: item["id"]
            ),
            "obligations": sorted(
                (asdict(item) for item in self.obligations), key=lambda item: item["id"]
            ),
            "operations": sorted(
                (asdict(item) for item in self.operations),
                key=lambda item: (
                    item["operation_type"],
                    item["target"],
                    stable_hash(item["payload"]),
                ),
            ),
            "diagnostics": sorted(
                self.diagnostics,
                key=lambda item: (
                    str(item.get("severity", "")),
                    str(item.get("message", "")),
                    str(item.get("text", "")),
                ),
            ),
        }

    def hash(self) -> str:
        return stable_hash(self.to_dict())

    def claim_by_id(self, claim_id: str) -> ClaimNode | None:
        for claim in self.claims:
            if claim.id == claim_id:
                return claim
        return None

    def entity_by_id(self, entity_id: str) -> EntityNode | None:
        for entity in self.entities:
            if entity.id == entity_id:
                return entity
        return None

    def add_claim_once(self, claim: ClaimNode) -> None:
        if self.claim_by_id(claim.id) is None:
            self.claims.append(claim)

    def add_entity_once(self, entity: EntityNode) -> None:
        if self.entity_by_id(entity.id) is None:
            self.entities.append(entity)


def operation_id(operation_type: str, payload: dict[str, Any]) -> str:
    return f"op:{operation_type.lower()}:{stable_hash(payload)[:16]}"
