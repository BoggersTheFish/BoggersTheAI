"""Explicit causal-program language for PRIME M24."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
import hashlib
import json
from itertools import combinations, product


VARIABLE_NAMES = (
    "A",
    "B",
    "C",
    "D",
)

CONFIGURATIONS = tuple(
    product(
        (0, 1),
        repeat=len(
            VARIABLE_NAMES
        ),
    )
)


class ProgramOp(str, Enum):
    VAR = "VAR"
    NOT = "NOT"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    EQ = "EQ"


@dataclass(frozen=True)
class CausalProgram:
    op: ProgramOp
    variables: tuple[int, ...]

    def __post_init__(
        self,
    ) -> None:
        variables = tuple(
            sorted(
                self.variables
            )
        )

        if (
            len(set(variables))
            != len(variables)
        ):
            raise ValueError(
                "causal-program variables must be unique"
            )

        if not all(
            0 <= variable
            < len(
                VARIABLE_NAMES
            )
            for variable
            in variables
        ):
            raise ValueError(
                "invalid causal-program variable"
            )

        if (
            self.op
            in (
                ProgramOp.VAR,
                ProgramOp.NOT,
            )
            and len(variables)
            != 1
        ):
            raise ValueError(
                "VAR/NOT require one variable"
            )

        if (
            self.op
            == ProgramOp.EQ
            and len(variables)
            != 2
        ):
            raise ValueError(
                "EQ requires exactly two variables"
            )

        if (
            self.op
            in (
                ProgramOp.AND,
                ProgramOp.OR,
                ProgramOp.XOR,
            )
            and not (
                2
                <= len(variables)
                <= 4
            )
        ):
            raise ValueError(
                "AND/OR/XOR require 2..4 variables"
            )

        object.__setattr__(
            self,
            "variables",
            variables,
        )

    @property
    def label(self) -> str:
        names = tuple(
            VARIABLE_NAMES[index]
            for index
            in self.variables
        )

        if self.op == ProgramOp.VAR:
            return names[0]

        if self.op == ProgramOp.NOT:
            return (
                "NOT("
                + names[0]
                + ")"
            )

        return (
            self.op.value
            + "("
            + ",".join(names)
            + ")"
        )

    @property
    def program_id(self) -> str:
        payload = {
            "op": self.op.value,
            "variables": list(
                self.variables
            ),
        }

        digest = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

        return (
            "cp:"
            + digest
        )

    def evaluate(
        self,
        configuration: tuple[
            int,
            ...,
        ],
    ) -> int:
        values = [
            configuration[index]
            for index
            in self.variables
        ]

        if self.op == ProgramOp.VAR:
            return values[0]

        if self.op == ProgramOp.NOT:
            return (
                1
                - values[0]
            )

        if self.op == ProgramOp.AND:
            result = 1

            for value in values:
                result &= value

            return result

        if self.op == ProgramOp.OR:
            result = 0

            for value in values:
                result |= value

            return result

        if self.op == ProgramOp.XOR:
            result = 0

            for value in values:
                result ^= value

            return result

        if self.op == ProgramOp.EQ:
            return int(
                values[0]
                == values[1]
            )

        raise ValueError(
            self.op
        )

    @property
    def signature(
        self,
    ) -> tuple[int, ...]:
        return tuple(
            self.evaluate(
                configuration
            )
            for configuration
            in CONFIGURATIONS
        )


@lru_cache(maxsize=1)
def program_universe(
) -> tuple[
    CausalProgram,
    ...,
]:
    programs = []

    for variable in range(4):
        programs.append(
            CausalProgram(
                ProgramOp.VAR,
                (variable,),
            )
        )

        programs.append(
            CausalProgram(
                ProgramOp.NOT,
                (variable,),
            )
        )

    for op in (
        ProgramOp.AND,
        ProgramOp.OR,
        ProgramOp.XOR,
        ProgramOp.EQ,
    ):
        for pair in combinations(
            range(4),
            2,
        ):
            programs.append(
                CausalProgram(
                    op,
                    pair,
                )
            )

    for op in (
        ProgramOp.AND,
        ProgramOp.OR,
        ProgramOp.XOR,
    ):
        for triple in combinations(
            range(4),
            3,
        ):
            programs.append(
                CausalProgram(
                    op,
                    triple,
                )
            )

        programs.append(
            CausalProgram(
                op,
                (
                    0,
                    1,
                    2,
                    3,
                ),
            )
        )

    programs.sort(
        key=lambda program: (
            program.label
        )
    )

    ids = {
        program.program_id
        for program
        in programs
    }

    signatures = {
        program.signature
        for program
        in programs
    }

    if len(ids) != 47:
        raise RuntimeError(
            "unexpected M24 program count"
        )

    if len(signatures) != 47:
        raise RuntimeError(
            "causal program quotient collision"
        )

    return tuple(
        programs
    )


def program_lookup(
) -> dict[str, CausalProgram]:
    return {
        program.program_id: program
        for program
        in program_universe()
    }
