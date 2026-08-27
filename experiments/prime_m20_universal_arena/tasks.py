"""Task definitions for PRIME M20 Universal Adaptive-State Arena."""

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


@dataclass(frozen=True)
class ArenaTask:
    name: str
    expression: (
        FeatureExpr
        | None
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


def xor(
    a: int,
    b: int,
) -> FeatureExpr:
    return binary(
        FeatureOp.XOR,
        lag(a),
        lag(b),
    )


def eq(
    a: int,
    b: int,
) -> FeatureExpr:
    return binary(
        FeatureOp.EQ,
        lag(a),
        lag(b),
    )


def and2(
    a: int,
    b: int,
) -> FeatureExpr:
    return binary(
        FeatureOp.AND,
        lag(a),
        lag(b),
    )


def or2(
    a: int,
    b: int,
) -> FeatureExpr:
    return binary(
        FeatureOp.OR,
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


TASKS = (
    ArenaTask(
        "CURRENT",
        None,
    ),
    ArenaTask(
        "LAG-1",
        lag(1),
    ),
    ArenaTask(
        "LAG-4",
        lag(4),
    ),
    ArenaTask(
        "LAG-7",
        lag(7),
    ),
    ArenaTask(
        "XOR-1-4",
        xor(1, 4),
    ),
    ArenaTask(
        "XOR-2-7",
        xor(2, 7),
    ),
    ArenaTask(
        "EQ-1-4",
        eq(1, 4),
    ),
    ArenaTask(
        "AND-1-4",
        and2(1, 4),
    ),
    ArenaTask(
        "OR-2-7",
        or2(2, 7),
    ),
    ArenaTask(
        "XOR-1-2-3",
        triple(
            FeatureOp.XOR,
            1,
            2,
            3,
        ),
    ),
    ArenaTask(
        "AND-1-2-4",
        triple(
            FeatureOp.AND,
            1,
            2,
            4,
        ),
    ),
    ArenaTask(
        "OR-2-3-4",
        triple(
            FeatureOp.OR,
            2,
            3,
            4,
        ),
    ),
)

TASK_BY_NAME = {
    task.name: task
    for task in TASKS
}
