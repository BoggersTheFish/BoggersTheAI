"""Predictive quotient semantics for bounded PRIME M20 constructions."""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import (
    description_length,
)
from .registry import (
    ConstructionRegistry,
)
from .types import (
    FeatureExpr,
    FeatureOp,
)


RELATION_EXACT = "exact"
RELATION_COMPLEMENT = "complement"
RELATION_DIFFERENT = "different"


def registry_expression_lookup(
    registry: ConstructionRegistry,
) -> dict[
    str,
    FeatureExpr,
]:
    return {
        construction_id: (
            record.spec.expression
        )
        for construction_id, record
        in registry._records.items()
    }


def _evaluate_assignment(
    expr: FeatureExpr,
    assignment: dict[int, int],
    lookup: dict[
        str,
        FeatureExpr,
    ],
    stack: tuple[str, ...] = (),
) -> int:
    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None

        if expr.lag not in assignment:
            raise ValueError(
                "truth-table assignment "
                "does not cover required lag"
            )

        return assignment[
            expr.lag
        ]

    if expr.op == FeatureOp.REF:
        assert expr.ref_id is not None

        if expr.ref_id in stack:
            raise ValueError(
                "cyclic construction reference"
            )

        target = lookup.get(
            expr.ref_id
        )

        if target is None:
            raise KeyError(
                "unresolved construction reference: "
                + expr.ref_id
            )

        return _evaluate_assignment(
            target,
            assignment,
            lookup,
            stack
            + (
                expr.ref_id,
            ),
        )

    assert expr.left is not None
    assert expr.right is not None

    a = _evaluate_assignment(
        expr.left,
        assignment,
        lookup,
        stack,
    )

    b = _evaluate_assignment(
        expr.right,
        assignment,
        lookup,
        stack,
    )

    if expr.op == FeatureOp.XOR:
        return a ^ b

    if expr.op == FeatureOp.EQ:
        return int(
            a == b
        )

    if expr.op == FeatureOp.AND:
        return a & b

    if expr.op == FeatureOp.OR:
        return a | b

    raise ValueError(
        "unsupported feature operation"
    )


def semantic_signature(
    expr: FeatureExpr,
    *,
    max_lag: int = 8,
    lookup: (
        dict[
            str,
            FeatureExpr,
        ]
        | None
    ) = None,
) -> int:
    """Exact Boolean truth-table signature."""

    if lookup is None:
        lookup = {}

    signature = 0

    for case in range(
        1 << max_lag
    ):
        assignment = {
            lag_index: (
                case
                >> (
                    lag_index
                    - 1
                )
            )
            & 1
            for lag_index
            in range(
                1,
                max_lag + 1,
            )
        }

        value = _evaluate_assignment(
            expr,
            assignment,
            lookup,
        )

        signature |= (
            value
            << case
        )

    return signature


def complement_signature(
    signature: int,
    *,
    max_lag: int = 8,
) -> int:
    mask = (
        1
        << (
            1 << max_lag
        )
    ) - 1

    return (
        mask
        ^ signature
    )


def predictive_partition_signature(
    expr: FeatureExpr,
    *,
    max_lag: int = 8,
    lookup: (
        dict[
            str,
            FeatureExpr,
        ]
        | None
    ) = None,
) -> int:
    signature = semantic_signature(
        expr,
        max_lag=max_lag,
        lookup=lookup,
    )

    complement = (
        complement_signature(
            signature,
            max_lag=max_lag,
        )
    )

    return min(
        signature,
        complement,
    )


def semantic_relation(
    left: FeatureExpr,
    right: FeatureExpr,
    *,
    max_lag: int = 8,
    left_lookup: (
        dict[
            str,
            FeatureExpr,
        ]
        | None
    ) = None,
    right_lookup: (
        dict[
            str,
            FeatureExpr,
        ]
        | None
    ) = None,
) -> str:
    left_signature = (
        semantic_signature(
            left,
            max_lag=max_lag,
            lookup=left_lookup,
        )
    )

    right_signature = (
        semantic_signature(
            right,
            max_lag=max_lag,
            lookup=right_lookup,
        )
    )

    if (
        left_signature
        == right_signature
    ):
        return RELATION_EXACT

    if (
        left_signature
        == complement_signature(
            right_signature,
            max_lag=max_lag,
        )
    ):
        return (
            RELATION_COMPLEMENT
        )

    return RELATION_DIFFERENT


def predictively_equivalent(
    left: FeatureExpr,
    right: FeatureExpr,
    *,
    max_lag: int = 8,
    left_lookup=None,
    right_lookup=None,
) -> bool:
    return (
        semantic_relation(
            left,
            right,
            max_lag=max_lag,
            left_lookup=(
                left_lookup
            ),
            right_lookup=(
                right_lookup
            ),
        )
        != RELATION_DIFFERENT
    )


@dataclass(frozen=True)
class QuotientMatch:
    construction_id: str
    relation: str


def active_partition_matches(
    registry: ConstructionRegistry,
    target: FeatureExpr,
    *,
    max_lag: int = 8,
) -> tuple[
    QuotientMatch,
    ...,
]:
    lookup = (
        registry_expression_lookup(
            registry
        )
    )

    matches = []

    for record in (
        registry.active_records()
    ):
        relation = (
            semantic_relation(
                record.spec.expression,
                target,
                max_lag=max_lag,
                left_lookup=lookup,
            )
        )

        if (
            relation
            != RELATION_DIFFERENT
        ):
            matches.append(
                QuotientMatch(
                    construction_id=(
                        record.spec.construction_id
                    ),
                    relation=relation,
                )
            )

    return tuple(
        matches
    )


def expanded_description_length(
    expr: FeatureExpr,
    *,
    lookup: dict[
        str,
        FeatureExpr,
    ],
    stack: tuple[str, ...] = (),
) -> int:
    if expr.op != FeatureOp.REF:
        if expr.op == FeatureOp.LAG:
            return (
                description_length(
                    expr
                )
            )

        assert expr.left is not None
        assert expr.right is not None

        return (
            1
            + expanded_description_length(
                expr.left,
                lookup=lookup,
                stack=stack,
            )
            + expanded_description_length(
                expr.right,
                lookup=lookup,
                stack=stack,
            )
        )

    assert expr.ref_id is not None

    if expr.ref_id in stack:
        raise ValueError(
            "cyclic construction reference"
        )

    target = lookup.get(
        expr.ref_id
    )

    if target is None:
        raise KeyError(
            expr.ref_id
        )

    return expanded_description_length(
        target,
        lookup=lookup,
        stack=(
            stack
            + (
                expr.ref_id,
            )
        ),
    )
