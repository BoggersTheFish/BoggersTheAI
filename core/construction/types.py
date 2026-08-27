"""Typed objects for PRIME M20 adaptive construction."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json


SEMANTICS_VERSION = "prime-m20.1"


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


class FeatureOp(str, Enum):
    LAG = "lag"
    REF = "ref"
    XOR = "xor"
    EQ = "eq"
    AND = "and"
    OR = "or"


class ConstructionStatus(str, Enum):
    PROPOSED = "proposed"
    AUTHORIZED = "authorized"
    RETIRED = "retired"


class AuthorityAction(str, Enum):
    AUTHORIZE = "authorize"
    RETIRE = "retire"
    RESTORE = "restore"


@dataclass(frozen=True)
class FeatureExpr:
    op: FeatureOp
    lag: int | None = None
    ref_id: str | None = None
    left: "FeatureExpr | None" = None
    right: "FeatureExpr | None" = None

    def __post_init__(self) -> None:
        if self.op == FeatureOp.LAG:
            if self.lag is None or self.lag < 1:
                raise ValueError(
                    "lag expression requires positive lag"
                )

            if (
                self.ref_id is not None
                or self.left is not None
                or self.right is not None
            ):
                raise ValueError(
                    "lag expression cannot have ref/children"
                )

            return

        if self.op == FeatureOp.REF:
            if (
                not isinstance(
                    self.ref_id,
                    str,
                )
                or not self.ref_id
            ):
                raise ValueError(
                    "ref expression requires construction id"
                )

            if (
                self.lag is not None
                or self.left is not None
                or self.right is not None
            ):
                raise ValueError(
                    "ref expression cannot have lag/children"
                )

            return

        if (
            self.lag is not None
            or self.ref_id is not None
        ):
            raise ValueError(
                "binary expression cannot contain direct lag/ref field"
            )

        if (
            self.left is None
            or self.right is None
        ):
            raise ValueError(
                "binary expression requires two children"
            )

    def to_dict(self) -> dict:
        if self.op == FeatureOp.LAG:
            return {
                "op": self.op.value,
                "lag": self.lag,
            }

        if self.op == FeatureOp.REF:
            return {
                "op": self.op.value,
                "ref_id": self.ref_id,
            }

        return {
            "op": self.op.value,
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
        }

    @property
    def expression_hash(self) -> str:
        payload = {
            "semantics_version": (
                SEMANTICS_VERSION
            ),
            "expression": self.to_dict(),
        }

        return hashlib.sha256(
            canonical_bytes(
                payload
            )
        ).hexdigest()


def expr_from_dict(
    value: dict,
) -> FeatureExpr:
    op = FeatureOp(
        value["op"]
    )

    if op == FeatureOp.LAG:
        return FeatureExpr(
            op=op,
            lag=int(
                value["lag"]
            ),
        )

    if op == FeatureOp.REF:
        return FeatureExpr(
            op=op,
            ref_id=str(
                value["ref_id"]
            ),
        )

    return FeatureExpr(
        op=op,
        left=expr_from_dict(
            value["left"]
        ),
        right=expr_from_dict(
            value["right"]
        ),
    )


@dataclass(frozen=True)
class ConstructionSpec:
    expression: FeatureExpr
    proposal_source: str = (
        "bounded_grammar"
    )

    @property
    def construction_id(self) -> str:
        return (
            "cx:"
            + self.expression.expression_hash
        )

    def to_dict(self) -> dict:
        return {
            "construction_id": (
                self.construction_id
            ),
            "semantics_version": (
                SEMANTICS_VERSION
            ),
            "expression": (
                self.expression.to_dict()
            ),
            "proposal_source": (
                self.proposal_source
            ),
        }


@dataclass(frozen=True)
class EvidenceSnapshot:
    construction_id: str
    wins: int
    losses: int
    threshold: int
    evidence_lhs: int
    evidence_rhs: int
    statistical_pass: bool
    structural_cost: int
    structural_pass: bool
    supported: bool
    obstruction_event_index: (
        int | None
    )
    authorization_event_index: (
        int | None
    )

    def to_dict(self) -> dict:
        return {
            "construction_id": (
                self.construction_id
            ),
            "wins": self.wins,
            "losses": self.losses,
            "threshold": self.threshold,
            "evidence_lhs": (
                self.evidence_lhs
            ),
            "evidence_rhs": (
                self.evidence_rhs
            ),
            "statistical_pass": (
                self.statistical_pass
            ),
            "structural_cost": (
                self.structural_cost
            ),
            "structural_pass": (
                self.structural_pass
            ),
            "supported": (
                self.supported
            ),
            "obstruction_event_index": (
                self.obstruction_event_index
            ),
            "authorization_event_index": (
                self.authorization_event_index
            ),
        }

    @property
    def evidence_hash(self) -> str:
        return hashlib.sha256(
            canonical_bytes(
                self.to_dict()
            )
        ).hexdigest()


@dataclass(frozen=True)
class VerifierAuthorization:
    action: AuthorityAction
    construction_id: str
    verdict: bool
    evidence_hash: str
    reason: str

    def to_dict(self) -> dict:
        return {
            "action": (
                self.action.value
            ),
            "construction_id": (
                self.construction_id
            ),
            "verdict": self.verdict,
            "evidence_hash": (
                self.evidence_hash
            ),
            "reason": self.reason,
        }
