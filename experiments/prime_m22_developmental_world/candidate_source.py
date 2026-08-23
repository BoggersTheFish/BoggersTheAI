"""Persistent-memory and schema-derived candidate generation."""

from __future__ import annotations

from dataclasses import dataclass

from core.cognition import (
    MegaPrimeCognition,
)
from core.construction.grammar import (
    binary,
    description_length,
    lag,
)
from core.construction.scaffold import (
    fold_commutative,
)
from core.construction.types import (
    ConstructionSpec,
    FeatureOp,
)


@dataclass(frozen=True)
class DevelopmentalCandidate:
    spec: ConstructionSpec
    source: str
    score: int
    memory_id: str | None = None
    schema_id: str | None = None


def instantiate_schema(
    operator: str,
    offsets: tuple[int, ...],
    *,
    max_lag: int = 8,
) -> tuple[
    ConstructionSpec,
    ...,
]:
    op = FeatureOp(
        operator
    )

    if not offsets:
        return ()

    largest = max(
        offsets
    )

    result = {}

    for base in range(
        1,
        max_lag - largest + 1,
    ):
        atoms = tuple(
            lag(
                base + offset
            )
            for offset in offsets
        )

        if len(atoms) == 2:
            expr = binary(
                op,
                atoms[0],
                atoms[1],
            )

        elif (
            len(atoms) >= 3
            and op
            in (
                FeatureOp.XOR,
                FeatureOp.AND,
                FeatureOp.OR,
            )
        ):
            expr = (
                fold_commutative(
                    op,
                    atoms,
                )
            )

        else:
            continue

        spec = (
            ConstructionSpec(
                expression=expr,
                proposal_source=(
                    "m22-schema-instantiation"
                ),
            )
        )

        result[
            spec.construction_id
        ] = spec

    return tuple(
        sorted(
            result.values(),
            key=lambda spec: (
                description_length(
                    spec.expression
                ),
                spec.construction_id,
            ),
        )
    )


class DevelopmentalCandidateSource:
    def __init__(
        self,
        cognition: MegaPrimeCognition,
    ) -> None:
        self.cognition = (
            cognition
        )

    def propose(
        self,
        *,
        context_tokens: tuple[
            str,
            ...,
        ],
        max_candidates: int = 64,
    ) -> tuple[
        DevelopmentalCandidate,
        ...,
    ]:
        candidates: dict[
            str,
            DevelopmentalCandidate,
        ] = {}

        # Exact / quotient memory recall.
        recalled = (
            self.cognition.transfer_engine.recall(
                context_tokens=(
                    context_tokens
                ),
                max_candidates=(
                    max_candidates
                ),
            )
        )

        for proposal in recalled:
            candidates[
                proposal.spec.construction_id
            ] = DevelopmentalCandidate(
                spec=proposal.spec,
                source="verified-memory",
                score=proposal.score,
                memory_id=(
                    proposal.memory_id
                ),
            )

        # Generalized schema instantiation.
        for schema in (
            self.cognition.mine_schemas()
        ):
            instantiated = (
                instantiate_schema(
                    schema.operator,
                    schema.normalized_offsets,
                )
            )

            for spec in instantiated:
                field_score = (
                    self.cognition.proposal_field.score(
                        spec,
                        context_tokens,
                    )
                )

                score = (
                    50
                    * schema.support
                    + field_score
                    - description_length(
                        spec.expression
                    )
                )

                current = (
                    candidates.get(
                        spec.construction_id
                    )
                )

                proposed = (
                    DevelopmentalCandidate(
                        spec=spec,
                        source="verified-schema",
                        score=score,
                        schema_id=(
                            schema.schema_id
                        ),
                    )
                )

                if (
                    current is None
                    or proposed.score
                    > current.score
                ):
                    candidates[
                        spec.construction_id
                    ] = proposed

        ordered = sorted(
            candidates.values(),
            key=lambda row: (
                -row.score,
                row.spec.construction_id,
            ),
        )

        return tuple(
            ordered[
                :max_candidates
            ]
        )
