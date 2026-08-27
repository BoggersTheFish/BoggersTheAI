"""Higher-order relation-schema proposal mining."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

from core.construction.types import (
    FeatureExpr,
    FeatureOp,
)

from .memory import (
    VerifiedConstructionMemory,
)


@dataclass(frozen=True)
class SchemaProposal:
    schema_id: str
    operator: str
    normalized_offsets: tuple[
        int,
        ...,
    ]
    example_memory_ids: tuple[
        str,
        ...,
    ]
    support: int
    state_commit_authorized: bool = False


def _flatten(
    expr: FeatureExpr,
    op: FeatureOp,
) -> list[FeatureExpr]:
    if expr.op != op:
        return [
            expr
        ]

    assert expr.left is not None
    assert expr.right is not None

    return (
        _flatten(
            expr.left,
            op,
        )
        + _flatten(
            expr.right,
            op,
        )
    )


def _raw_lag_pattern(
    expr: FeatureExpr,
) -> tuple[
    str,
    tuple[int, ...],
] | None:
    if expr.op not in (
        FeatureOp.XOR,
        FeatureOp.AND,
        FeatureOp.OR,
        FeatureOp.EQ,
    ):
        return None

    atoms = _flatten(
        expr,
        expr.op,
    )

    if not all(
        atom.op
        == FeatureOp.LAG
        for atom in atoms
    ):
        return None

    lags = sorted(
        atom.lag
        for atom in atoms
        if atom.lag is not None
    )

    if len(lags) < 2:
        return None

    minimum = min(
        lags
    )

    offsets = tuple(
        lag_value
        - minimum
        for lag_value in lags
    )

    return (
        expr.op.value,
        offsets,
    )


class SchemaMiner:
    def mine(
        self,
        memory: (
            VerifiedConstructionMemory
        ),
        *,
        minimum_examples: int = 2,
    ) -> tuple[
        SchemaProposal,
        ...,
    ]:
        groups: dict[
            tuple[
                str,
                tuple[int, ...],
            ],
            list[str],
        ] = {}

        for entry in (
            memory.entries.values()
        ):
            pattern = (
                _raw_lag_pattern(
                    entry.spec.expression
                )
            )

            if pattern is None:
                continue

            groups.setdefault(
                pattern,
                [],
            ).append(
                entry.memory_id
            )

        proposals = []

        for (
            operator,
            offsets,
        ), examples in groups.items():
            if (
                len(examples)
                < minimum_examples
            ):
                continue

            payload = {
                "operator": (
                    operator
                ),
                "normalized_offsets": list(
                    offsets
                ),
            }

            schema_id = (
                "schema:"
                + hashlib.sha256(
                    json.dumps(
                        payload,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode(
                        "utf-8"
                    )
                ).hexdigest()
            )

            proposals.append(
                SchemaProposal(
                    schema_id=(
                        schema_id
                    ),
                    operator=(
                        operator
                    ),
                    normalized_offsets=(
                        offsets
                    ),
                    example_memory_ids=tuple(
                        sorted(
                            examples
                        )
                    ),
                    support=len(
                        examples
                    ),
                )
            )

        proposals.sort(
            key=lambda row: (
                -row.support,
                row.schema_id,
            )
        )

        return tuple(
            proposals
        )
