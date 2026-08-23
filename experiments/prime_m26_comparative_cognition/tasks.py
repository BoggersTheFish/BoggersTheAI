"""Task universe for PRIME M26 comparative cognition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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


TargetFunction = Callable[
    [tuple[int, ...], int, int],
    int,
]


@dataclass(frozen=True)
class ComparativeTask:
    name: str
    family: str
    target_function: TargetFunction
    explicit_expression: FeatureExpr | None = None


def expression_target(
    expression: FeatureExpr,
) -> TargetFunction:
    def target(
        history,
        event_index,
        total_steps,
    ):
        del event_index
        del total_steps

        return evaluate(
            expression,
            history,
        )

    return target


def current_target(
    history,
    event_index,
    total_steps,
):
    del event_index
    del total_steps

    return history[-1]


def majority16(
    history,
    event_index,
    total_steps,
):
    del event_index
    del total_steps

    window = history[-16:]

    return int(
        2 * sum(window)
        >= len(window)
    )


def running_parity(
    history,
    event_index,
    total_steps,
):
    del event_index
    del total_steps

    result = 0

    for value in history:
        result ^= value

    return result


def mod3_ones(
    history,
    event_index,
    total_steps,
):
    del event_index
    del total_steps

    return int(
        sum(history) % 3
        == 0
    )


def toggle_on_11(
    history,
    event_index,
    total_steps,
):
    del event_index
    del total_steps

    state = 0

    for index in range(
        1,
        len(history),
    ):
        if (
            history[index - 1] == 1
            and history[index] == 1
            and (
                index == 1
                or history[index - 2] == 0
            )
        ):
            state ^= 1

    return state


def run_length_parity(
    history,
    event_index,
    total_steps,
):
    del event_index
    del total_steps

    current = history[-1]

    length = 1

    for index in range(
        len(history) - 2,
        -1,
        -1,
    ):
        if (
            history[index]
            != current
        ):
            break

        length += 1

    return length & 1


def switching_target(
    history,
    event_index,
    total_steps,
):
    xor_expr = binary(
        FeatureOp.XOR,
        lag(1),
        lag(4),
    )

    and_expr = binary(
        FeatureOp.AND,
        lag(1),
        lag(4),
    )

    expression = (
        xor_expr
        if event_index
        < total_steps // 2
        else and_expr
    )

    return evaluate(
        expression,
        history,
    )


def tasks() -> tuple[
    ComparativeTask,
    ...,
]:
    rows = []

    def add_expression(
        name,
        family,
        expression,
    ):
        rows.append(
            ComparativeTask(
                name=name,
                family=family,
                target_function=(
                    expression_target(
                        expression
                    )
                ),
                explicit_expression=(
                    expression
                ),
            )
        )

    rows.append(
        ComparativeTask(
            name="CURRENT",
            family="explicit-relational",
            target_function=current_target,
        )
    )

    add_expression(
        "LAG-1",
        "explicit-relational",
        lag(1),
    )

    add_expression(
        "LAG-4",
        "explicit-relational",
        lag(4),
    )

    add_expression(
        "XOR-1-4",
        "explicit-relational",
        binary(
            FeatureOp.XOR,
            lag(1),
            lag(4),
        ),
    )

    add_expression(
        "EQ-1-4",
        "explicit-relational",
        binary(
            FeatureOp.EQ,
            lag(1),
            lag(4),
        ),
    )

    add_expression(
        "AND-1-4",
        "explicit-relational",
        binary(
            FeatureOp.AND,
            lag(1),
            lag(4),
        ),
    )

    add_expression(
        "OR-2-7",
        "explicit-relational",
        binary(
            FeatureOp.OR,
            lag(2),
            lag(7),
        ),
    )

    add_expression(
        "XOR-1-2-3",
        "explicit-relational",
        fold_commutative(
            FeatureOp.XOR,
            (
                lag(1),
                lag(2),
                lag(3),
            ),
        ),
    )

    add_expression(
        "LAG-8",
        "scaling",
        lag(8),
    )

    add_expression(
        "LAG-16",
        "scaling",
        lag(16),
    )

    add_expression(
        "XOR-1-8",
        "scaling",
        binary(
            FeatureOp.XOR,
            lag(1),
            lag(8),
        ),
    )

    add_expression(
        "XOR-1-16",
        "scaling",
        binary(
            FeatureOp.XOR,
            lag(1),
            lag(16),
        ),
    )

    rows.append(
        ComparativeTask(
            name="MAJORITY-16",
            family="scaling",
            target_function=majority16,
        )
    )

    rows.extend(
        (
            ComparativeTask(
                name="RUNNING-PARITY",
                family="recurrent-state",
                target_function=running_parity,
            ),
            ComparativeTask(
                name="MOD3-ONES",
                family="recurrent-state",
                target_function=mod3_ones,
            ),
            ComparativeTask(
                name="TOGGLE-ON-11",
                family="recurrent-state",
                target_function=toggle_on_11,
            ),
            ComparativeTask(
                name="RUN-LENGTH-PARITY",
                family="recurrent-state",
                target_function=run_length_parity,
            ),
            ComparativeTask(
                name="XOR-TO-AND",
                family="nonstationary",
                target_function=switching_target,
            ),
        )
    )

    return tuple(rows)
