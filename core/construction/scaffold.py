"""Bounded non-authoritative proposal scaffolds for PRIME M20."""

from __future__ import annotations

from itertools import combinations

from .grammar import (
    binary,
    description_length,
    lag,
    required_history,
)
from .types import (
    ConstructionSpec,
    FeatureExpr,
    FeatureOp,
)


SCAFFOLD_OPS = (
    FeatureOp.XOR,
    FeatureOp.AND,
    FeatureOp.OR,
)


def fold_commutative(
    op: FeatureOp,
    expressions: tuple[
        FeatureExpr,
        ...,
    ],
) -> FeatureExpr:
    if (
        op
        not in SCAFFOLD_OPS
    ):
        raise ValueError(
            "unsupported scaffold operator"
        )

    if len(expressions) < 2:
        raise ValueError(
            "scaffold requires >=2 expressions"
        )

    ordered = sorted(
        expressions,
        key=lambda expr: (
            expr.expression_hash
        ),
    )

    current = ordered[0]

    for expr in ordered[1:]:
        current = binary(
            op,
            current,
            expr,
        )

    return current


def generate_scaffold_candidates(
    *,
    max_lag: int = 8,
    max_candidates: int = 256,
) -> tuple[
    ConstructionSpec,
    ...,
]:
    """Generate bounded depth-2 proposal expressions.

    Internal subexpressions are proposal scaffolds only.

    They are NOT canonical constructions and receive no authority.
    """

    if max_lag < 3:
        return ()

    expressions: dict[
        str,
        FeatureExpr,
    ] = {}

    for a, b, c in combinations(
        range(
            1,
            max_lag + 1,
        ),
        3,
    ):
        atoms = (
            lag(a),
            lag(b),
            lag(c),
        )

        for op in SCAFFOLD_OPS:
            expr = fold_commutative(
                op,
                atoms,
            )

            expressions[
                expr.expression_hash
            ] = expr

    ordered = sorted(
        expressions.values(),
        key=lambda expr: (
            description_length(
                expr
            ),
            required_history(
                expr
            ),
            expr.expression_hash,
        ),
    )

    return tuple(
        ConstructionSpec(
            expression=expr,
            proposal_source=(
                "bounded_scaffold"
            ),
        )
        for expr in ordered[
            :max_candidates
        ]
    )
