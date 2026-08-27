"""Procedural developmental curriculum for PRIME M22."""

from __future__ import annotations

from dataclasses import dataclass

from core.construction.grammar import (
    binary,
    evaluate,
    lag,
)
from core.construction.scaffold import (
    fold_commutative,
)
from core.construction.types import (
    FeatureExpr,
    FeatureOp,
)


MASK64 = (
    (1 << 64)
    - 1
)


def splitmix64(
    value: int,
) -> int:
    z = (
        value
        + 0x9E3779B97F4A7C15
    ) & MASK64

    z = (
        (
            z
            ^ (z >> 30)
        )
        * 0xBF58476D1CE4E5B9
    ) & MASK64

    z = (
        (
            z
            ^ (z >> 27)
        )
        * 0x94D049BB133111EB
    ) & MASK64

    return (
        z
        ^ (z >> 31)
    ) & MASK64


def binary_stream(
    seed: int,
):
    state = splitmix64(
        seed
        ^ 0x4D32324445564C42
    )

    while True:
        state = splitmix64(
            state
        )

        yield (
            state >> 63
        ) & 1


def pair(
    op: FeatureOp,
    a: int,
    b: int,
) -> FeatureExpr:
    return binary(
        op,
        lag(a),
        lag(b),
    )


def triple(
    op: FeatureOp,
    a: int,
    b: int,
    c: int,
) -> FeatureExpr:
    return fold_commutative(
        op,
        (
            lag(a),
            lag(b),
            lag(c),
        ),
    )


@dataclass(frozen=True)
class ChapterSpec:
    chapter_id: str
    seed: int
    expression: FeatureExpr | None
    developmental_role: str
    steps: int = 1024

    @property
    def context_tokens(
        self,
    ) -> tuple[str, ...]:
        # Deliberately does not reveal the hidden operator or lags.
        return (
            "prime-m22-developmental-lab",
            "binary-partial-observation",
            "persistent-curriculum",
        )

    def target(
        self,
        history: tuple[
            int,
            ...,
        ],
    ) -> int:
        if self.expression is None:
            if not history:
                return 0

            return history[-1]

        return evaluate(
            self.expression,
            history,
        )


def curriculum() -> tuple[
    ChapterSpec,
    ...,
]:
    chapters = (
        # Foundation.
        ChapterSpec(
            "C00-current",
            22000,
            None,
            "novel",
        ),
        ChapterSpec(
            "C01-lag1",
            22001,
            lag(1),
            "novel",
        ),
        ChapterSpec(
            "C02-xor1-4",
            22002,
            pair(
                FeatureOp.XOR,
                1,
                4,
            ),
            "novel",
        ),
        ChapterSpec(
            "C03-and1-4",
            22003,
            pair(
                FeatureOp.AND,
                1,
                4,
            ),
            "novel",
        ),

        # Exact recurrence.
        ChapterSpec(
            "C04-lag1-repeat",
            22004,
            lag(1),
            "repeat",
        ),
        ChapterSpec(
            "C05-xor1-4-repeat",
            22005,
            pair(
                FeatureOp.XOR,
                1,
                4,
            ),
            "repeat",
        ),
        ChapterSpec(
            "C06-and1-4-repeat",
            22006,
            pair(
                FeatureOp.AND,
                1,
                4,
            ),
            "repeat",
        ),

        # Shifted families: enough evidence for schema formation.
        ChapterSpec(
            "C07-xor2-5",
            22007,
            pair(
                FeatureOp.XOR,
                2,
                5,
            ),
            "family-learning",
        ),
        ChapterSpec(
            "C08-xor3-6",
            22008,
            pair(
                FeatureOp.XOR,
                3,
                6,
            ),
            "schema-transfer",
        ),
        ChapterSpec(
            "C09-xor4-7",
            22009,
            pair(
                FeatureOp.XOR,
                4,
                7,
            ),
            "schema-transfer",
        ),

        ChapterSpec(
            "C10-and2-5",
            22010,
            pair(
                FeatureOp.AND,
                2,
                5,
            ),
            "family-learning",
        ),
        ChapterSpec(
            "C11-and3-6",
            22011,
            pair(
                FeatureOp.AND,
                3,
                6,
            ),
            "schema-transfer",
        ),
        ChapterSpec(
            "C12-and4-7",
            22012,
            pair(
                FeatureOp.AND,
                4,
                7,
            ),
            "schema-transfer",
        ),

        # OR family.
        ChapterSpec(
            "C13-or1-4",
            22013,
            pair(
                FeatureOp.OR,
                1,
                4,
            ),
            "novel",
        ),
        ChapterSpec(
            "C14-or2-5",
            22014,
            pair(
                FeatureOp.OR,
                2,
                5,
            ),
            "family-learning",
        ),
        ChapterSpec(
            "C15-or3-6",
            22015,
            pair(
                FeatureOp.OR,
                3,
                6,
            ),
            "schema-transfer",
        ),

        # Higher-order family.
        ChapterSpec(
            "C16-xor123",
            22016,
            triple(
                FeatureOp.XOR,
                1,
                2,
                3,
            ),
            "novel",
        ),
        ChapterSpec(
            "C17-xor234",
            22017,
            triple(
                FeatureOp.XOR,
                2,
                3,
                4,
            ),
            "family-learning",
        ),
        ChapterSpec(
            "C18-xor345",
            22018,
            triple(
                FeatureOp.XOR,
                3,
                4,
                5,
            ),
            "schema-transfer",
        ),

        # Complement-equivalent family.
        ChapterSpec(
            "C19-eq1-4",
            22019,
            pair(
                FeatureOp.EQ,
                1,
                4,
            ),
            "quotient-transfer",
        ),

        # Stress: no representation should be invented.
        ChapterSpec(
            "C20-current",
            22020,
            None,
            "negative-transfer",
        ),

        # Return to old knowledge after intervening worlds.
        ChapterSpec(
            "C21-xor1-4-long-return",
            22021,
            pair(
                FeatureOp.XOR,
                1,
                4,
            ),
            "long-range-recall",
        ),
        ChapterSpec(
            "C22-lag1-long-return",
            22022,
            lag(1),
            "long-range-recall",
        ),

        # Higher-order conjunction/disjunction.
        ChapterSpec(
            "C23-and124",
            22023,
            triple(
                FeatureOp.AND,
                1,
                2,
                4,
            ),
            "novel",
        ),
        ChapterSpec(
            "C24-or234",
            22024,
            triple(
                FeatureOp.OR,
                2,
                3,
                4,
            ),
            "novel",
        ),
    )

    return chapters
