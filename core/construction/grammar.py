"""Bounded generative construction grammar for PRIME M20."""

from __future__ import annotations

from .types import (
    ConstructionSpec,
    FeatureExpr,
    FeatureOp,
)


COMMUTATIVE = {
    FeatureOp.XOR,
    FeatureOp.EQ,
    FeatureOp.AND,
    FeatureOp.OR,
}


def lag(k: int) -> FeatureExpr:
    return FeatureExpr(
        op=FeatureOp.LAG,
        lag=k,
    )


def binary(
    op: FeatureOp,
    left: FeatureExpr,
    right: FeatureExpr,
) -> FeatureExpr:
    if op not in COMMUTATIVE:
        raise ValueError("unsupported binary operator")

    # Deterministic commutative normalization.
    if left.expression_hash > right.expression_hash:
        left, right = right, left

    return FeatureExpr(
        op=op,
        left=left,
        right=right,
    )


def history_value(
    history: list[int] | tuple[int, ...],
    k: int,
) -> int:
    index = len(history) - 1 - k

    if index < 0:
        return 0

    value = history[index]

    if value not in (0, 1):
        raise ValueError("history must be binary")

    return value


def evaluate(
    expr: FeatureExpr,
    history: list[int] | tuple[int, ...],
) -> int:
    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None
        return history_value(
            history,
            expr.lag,
        )

    assert expr.left is not None
    assert expr.right is not None

    a = evaluate(
        expr.left,
        history,
    )

    b = evaluate(
        expr.right,
        history,
    )

    if expr.op == FeatureOp.XOR:
        return a ^ b

    if expr.op == FeatureOp.EQ:
        return int(a == b)

    if expr.op == FeatureOp.AND:
        return a & b

    if expr.op == FeatureOp.OR:
        return a | b

    raise ValueError(
        f"unsupported expression op: {expr.op}"
    )


def required_history(expr: FeatureExpr) -> int:
    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None
        return expr.lag

    assert expr.left is not None
    assert expr.right is not None

    return max(
        required_history(expr.left),
        required_history(expr.right),
    )


def description_length(expr: FeatureExpr) -> int:
    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None

        return (
            2
            + max(
                1,
                expr.lag.bit_length(),
            )
        )

    assert expr.left is not None
    assert expr.right is not None

    return (
        1
        + description_length(expr.left)
        + description_length(expr.right)
    )


def generate_bounded_candidates(
    *,
    max_lag: int = 8,
    max_candidates: int = 128,
) -> tuple[ConstructionSpec, ...]:
    if max_lag < 1:
        raise ValueError("max_lag must be positive")

    if max_candidates < 1:
        raise ValueError("max_candidates must be positive")

    primitives = [
        lag(k)
        for k in range(1, max_lag + 1)
    ]

    expressions: dict[str, FeatureExpr] = {}

    for expr in primitives:
        expressions[
            expr.expression_hash
        ] = expr

    for i, left in enumerate(primitives):
        for right in primitives[
            i + 1:
        ]:
            for op in (
                FeatureOp.XOR,
                FeatureOp.EQ,
                FeatureOp.AND,
                FeatureOp.OR,
            ):
                expr = binary(
                    op,
                    left,
                    right,
                )

                expressions[
                    expr.expression_hash
                ] = expr

    ordered = sorted(
        expressions.values(),
        key=lambda expr: (
            description_length(expr),
            required_history(expr),
            expr.expression_hash,
        ),
    )

    return tuple(
        ConstructionSpec(
            expression=expr
        )
        for expr in ordered[
            :max_candidates
        ]
    )
