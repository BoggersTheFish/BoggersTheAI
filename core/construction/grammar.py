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


def ref(
    construction_id: str,
) -> FeatureExpr:
    return FeatureExpr(
        op=FeatureOp.REF,
        ref_id=construction_id,
    )


def binary(
    op: FeatureOp,
    left: FeatureExpr,
    right: FeatureExpr,
) -> FeatureExpr:
    if op not in COMMUTATIVE:
        raise ValueError(
            "unsupported binary operator"
        )

    if (
        left.expression_hash
        > right.expression_hash
    ):
        left, right = (
            right,
            left,
        )

    return FeatureExpr(
        op=op,
        left=left,
        right=right,
    )


def history_value(
    history: (
        list[int]
        | tuple[int, ...]
    ),
    k: int,
) -> int:
    index = (
        len(history)
        - 1
        - k
    )

    if index < 0:
        return 0

    value = history[
        index
    ]

    if value not in (
        0,
        1,
    ):
        raise ValueError(
            "history must be binary"
        )

    return value


def dependencies(
    expr: FeatureExpr,
) -> frozenset[str]:
    if expr.op == FeatureOp.LAG:
        return frozenset()

    if expr.op == FeatureOp.REF:
        assert expr.ref_id is not None

        return frozenset(
            (
                expr.ref_id,
            )
        )

    assert expr.left is not None
    assert expr.right is not None

    return (
        dependencies(
            expr.left
        )
        |
        dependencies(
            expr.right
        )
    )


def evaluate(
    expr: FeatureExpr,
    history: (
        list[int]
        | tuple[int, ...]
    ),
    resolved: (
        dict[str, int]
        | None
    ) = None,
) -> int:
    if resolved is None:
        resolved = {}

    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None

        return history_value(
            history,
            expr.lag,
        )

    if expr.op == FeatureOp.REF:
        assert expr.ref_id is not None

        if (
            expr.ref_id
            not in resolved
        ):
            raise KeyError(
                "construction reference "
                "is not currently resolved: "
                + expr.ref_id
            )

        value = resolved[
            expr.ref_id
        ]

        if value not in (
            0,
            1,
        ):
            raise ValueError(
                "resolved construction "
                "value must be binary"
            )

        return value

    assert expr.left is not None
    assert expr.right is not None

    a = evaluate(
        expr.left,
        history,
        resolved,
    )

    b = evaluate(
        expr.right,
        history,
        resolved,
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
        "unsupported expression op"
    )


def required_history(
    expr: FeatureExpr,
) -> int:
    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None
        return expr.lag

    if expr.op == FeatureOp.REF:
        return 0

    assert expr.left is not None
    assert expr.right is not None

    return max(
        required_history(
            expr.left
        ),
        required_history(
            expr.right
        ),
    )


def description_length(
    expr: FeatureExpr,
) -> int:
    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None

        return (
            2
            + max(
                1,
                expr.lag.bit_length(),
            )
        )

    if expr.op == FeatureOp.REF:
        # Reusing a verified construction
        # should be cheaper than restating
        # its internal expression.
        return 3

    assert expr.left is not None
    assert expr.right is not None

    return (
        1
        + description_length(
            expr.left
        )
        + description_length(
            expr.right
        )
    )


def generate_bounded_candidates(
    *,
    max_lag: int = 8,
    max_candidates: int = 128,
) -> tuple[
    ConstructionSpec,
    ...,
]:
    if max_lag < 1:
        raise ValueError(
            "max_lag must be positive"
        )

    if max_candidates < 1:
        raise ValueError(
            "max_candidates must be positive"
        )

    primitives = [
        lag(k)
        for k in range(
            1,
            max_lag + 1,
        )
    ]

    expressions: dict[
        str,
        FeatureExpr,
    ] = {}

    for expr in primitives:
        expressions[
            expr.expression_hash
        ] = expr

    for index, left in enumerate(
        primitives
    ):
        for right in primitives[
            index + 1:
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
            expression=expr
        )
        for expr in ordered[
            :max_candidates
        ]
    )
