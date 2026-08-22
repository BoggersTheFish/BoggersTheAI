"""Higher-order construction growth for PRIME M20."""

from __future__ import annotations

from .grammar import (
    binary,
    description_length,
    lag,
    ref,
    required_history,
)
from .registry import (
    ConstructionRegistry,
)
from .types import (
    ConstructionSpec,
    FeatureExpr,
    FeatureOp,
)


COMPOSITION_OPERATORS = (
    FeatureOp.XOR,
    FeatureOp.EQ,
    FeatureOp.AND,
    FeatureOp.OR,
)


def _add(
    expressions: dict[
        str,
        FeatureExpr,
    ],
    expr: FeatureExpr,
) -> None:
    expressions[
        expr.expression_hash
    ] = expr


def generate_composed_candidates(
    registry: ConstructionRegistry,
    *,
    max_lag: int = 8,
    max_candidates: int = 128,
) -> tuple[
    ConstructionSpec,
    ...,
]:
    """Build bounded candidates from authorized constructions.

    Authorized constructions are atoms.
    Proposed/retired constructions are not.
    """

    active = (
        registry.active_records()
    )

    if not active:
        return ()

    active_refs = [
        ref(
            record.spec.construction_id
        )
        for record in active
    ]

    raw_lags = [
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

    # Verified construction + raw observation relation.
    for verified in active_refs:
        for raw in raw_lags:
            for op in COMPOSITION_OPERATORS:
                _add(
                    expressions,
                    binary(
                        op,
                        verified,
                        raw,
                    ),
                )

    # Verified construction + verified construction.
    for index, left in enumerate(
        active_refs
    ):
        for right in active_refs[
            index + 1:
        ]:
            for op in COMPOSITION_OPERATORS:
                _add(
                    expressions,
                    binary(
                        op,
                        left,
                        right,
                    ),
                )

    active_ids = set(
        registry.active_ids()
    )

    proposed = []

    for expr in expressions.values():
        spec = ConstructionSpec(
            expression=expr,
            proposal_source=(
                "verified_composition"
            ),
        )

        if (
            spec.construction_id
            in active_ids
        ):
            continue

        proposed.append(
            spec
        )

    proposed.sort(
        key=lambda spec: (
            description_length(
                spec.expression
            ),
            required_history(
                spec.expression
            ),
            spec.construction_id,
        )
    )

    return tuple(
        proposed[
            :max_candidates
        ]
    )
