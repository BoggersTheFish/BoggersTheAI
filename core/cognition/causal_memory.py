"""Persistent causal-program memory for PRIME M24."""

from __future__ import annotations

from dataclasses import dataclass

from .causal_certificate import (
    CausalAuthorization,
)
from .causal_program import (
    CausalProgram,
    ProgramOp,
    program_lookup,
    program_universe,
)


@dataclass
class CausalMemoryEntry:
    program_id: str
    times_verified: int = 0
    successful_reuses: int = 0
    failed_reuses: int = 0
    last_sequence: int = 0


@dataclass(frozen=True)
class CausalSchema:
    operator: ProgramOp
    normalized_offsets: tuple[
        int,
        ...,
    ]
    support: int


def schema_descriptor(
    program: CausalProgram,
):
    if (
        program.op
        not in (
            ProgramOp.AND,
            ProgramOp.OR,
            ProgramOp.XOR,
            ProgramOp.EQ,
        )
    ):
        return None

    minimum = min(
        program.variables
    )

    offsets = tuple(
        variable
        - minimum
        for variable
        in program.variables
    )

    return (
        program.op,
        offsets,
    )


class CausalProgramMemory:
    def __init__(self) -> None:
        self.entries: dict[
            str,
            CausalMemoryEntry,
        ] = {}

        self.sequence = 0

    def ingest(
        self,
        authorization: (
            CausalAuthorization
        ),
    ) -> None:
        if not authorization.verdict:
            raise PermissionError(
                "rejected causal program "
                "cannot enter semantic memory"
            )

        if (
            authorization.program_id
            not in program_lookup()
        ):
            raise KeyError(
                "unknown causal program"
            )

        self.sequence += 1

        entry = (
            self.entries.setdefault(
                authorization.program_id,
                CausalMemoryEntry(
                    program_id=(
                        authorization.program_id
                    )
                ),
            )
        )

        entry.times_verified += 1

        entry.last_sequence = (
            self.sequence
        )

    def record_reuse(
        self,
        program_id: str,
        *,
        success: bool,
    ) -> None:
        entry = (
            self.entries.get(
                program_id
            )
        )

        if entry is None:
            return

        if success:
            entry.successful_reuses += 1
        else:
            entry.failed_reuses += 1

    def schemas(
        self,
    ) -> tuple[
        CausalSchema,
        ...,
    ]:
        lookup = (
            program_lookup()
        )

        groups: dict[
            tuple[
                ProgramOp,
                tuple[int, ...],
            ],
            set[str],
        ] = {}

        for program_id in (
            self.entries
        ):
            program = lookup[
                program_id
            ]

            descriptor = (
                schema_descriptor(
                    program
                )
            )

            if descriptor is None:
                continue

            groups.setdefault(
                descriptor,
                set(),
            ).add(
                program_id
            )

        rows = []

        for (
            operator,
            offsets,
        ), examples in groups.items():
            if len(examples) < 2:
                continue

            rows.append(
                CausalSchema(
                    operator=operator,
                    normalized_offsets=(
                        offsets
                    ),
                    support=len(
                        examples
                    ),
                )
            )

        rows.sort(
            key=lambda row: (
                -row.support,
                row.operator.value,
                row.normalized_offsets,
            )
        )

        return tuple(
            rows
        )

    def _schema_generated_ids(
        self,
    ) -> dict[str, int]:
        universe = (
            program_universe()
        )

        scores: dict[
            str,
            int,
        ] = {}

        for schema in (
            self.schemas()
        ):
            for program in universe:
                descriptor = (
                    schema_descriptor(
                        program
                    )
                )

                if descriptor != (
                    schema.operator,
                    schema.normalized_offsets,
                ):
                    continue

                scores[
                    program.program_id
                ] = max(
                    scores.get(
                        program.program_id,
                        0,
                    ),
                    (
                        175
                        + 70
                        * schema.support
                    ),
                )

        return scores

    def priority_program_ids(
        self,
        *,
        limit: int = 8,
    ) -> tuple[str, ...]:
        scores: dict[
            str,
            int,
        ] = {}

        for program_id, entry in (
            self.entries.items()
        ):
            age = (
                self.sequence
                - entry.last_sequence
            )

            scores[
                program_id
            ] = (
                220
                + 80
                * entry.times_verified
                + 35
                * entry.successful_reuses
                - 55
                * entry.failed_reuses
                + max(
                    0,
                    40
                    - 5
                    * age
                )
            )

        for (
            program_id,
            schema_score,
        ) in (
            self._schema_generated_ids().items()
        ):
            scores[
                program_id
            ] = max(
                scores.get(
                    program_id,
                    0,
                ),
                schema_score,
            )

        ordered = sorted(
            scores,
            key=lambda program_id: (
                -scores[
                    program_id
                ],
                program_lookup()[
                    program_id
                ].label,
            ),
        )

        return tuple(
            ordered[
                :limit
            ]
        )
