"""Dependency-free arena runner for PRIME M20."""

from __future__ import annotations

from dataclasses import dataclass

from core.construction.compositional_engine import (
    CompositionalAdaptiveConstructionEngine,
)
from core.construction.grammar import (
    evaluate,
    history_value,
)
from core.construction.receipts import (
    verify_receipt_chain,
)

from .tasks import (
    ArenaTask,
    TASKS,
)


PPM = 1_000_000

STEPS = 1536
FINAL_WINDOW = 256

DEVELOPMENT_SEEDS = tuple(
    range(
        600,
        608,
    )
)

EVALUATION_SEEDS = tuple(
    range(
        6000,
        6032,
    )
)

CONDITIONS = (
    "REACTIVE",
    "FIXED-H8",
    "ORACLE-FEATURE",
    "M20-CONSTRUCTION",
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


class TargetTableLearner:
    def __init__(
        self,
        seed: int,
    ) -> None:
        self.seed = seed

        self.counts: dict[
            tuple[int, ...],
            list[int],
        ] = {}

    def choose(
        self,
        state: tuple[int, ...],
        event_index: int,
    ) -> int:
        exploration = (
            splitmix64(
                self.seed
                ^ splitmix64(
                    event_index
                )
            )
            % 10
            == 0
        )

        if exploration:
            return (
                splitmix64(
                    self.seed
                    ^ 0xA11CE
                    ^ splitmix64(
                        event_index
                    )
                )
                & 1
            )

        counts = self.counts.get(
            state,
            [0, 0],
        )

        return int(
            counts[1]
            > counts[0]
        )

    def update(
        self,
        state: tuple[int, ...],
        target: int,
    ) -> None:
        counts = self.counts.setdefault(
            state,
            [0, 0],
        )

        counts[
            target
        ] += 1


@dataclass(frozen=True)
class ArenaResult:
    payload: dict


def observation_stream(
    seed: int,
):
    state = splitmix64(
        seed
        ^ 0x5052494D453230
    )

    while True:
        state = splitmix64(
            state
        )

        yield (
            state >> 63
        ) & 1


def fixed_h8_state(
    observation: int,
    history: tuple[int, ...],
) -> tuple[int, ...]:
    return (
        observation,
        *(
            history_value(
                history,
                lag_index,
            )
            for lag_index
            in range(
                1,
                9,
            )
        ),
    )


def oracle_state(
    observation: int,
    task: ArenaTask,
    history: tuple[int, ...],
) -> tuple[int, ...]:
    return (
        observation,
        task.target(
            history
        ),
    )


def target_construction_active(
    engine: (
        CompositionalAdaptiveConstructionEngine
    ),
    task: ArenaTask,
) -> bool:
    if task.expression is None:
        return (
            len(
                engine.active_construction_ids
            )
            == 0
        )

    target_hash = (
        task.expression.expression_hash
    )

    return any(
        record.spec.expression.expression_hash
        == target_hash
        for record
        in engine.registry.active_records()
    )


def run_world(
    *,
    task: ArenaTask,
    stream_seed: int,
    condition: str,
    permit_evaluation: bool = False,
) -> ArenaResult:
    if condition not in CONDITIONS:
        raise ValueError(
            "unknown arena condition"
        )

    if permit_evaluation:
        if (
            stream_seed
            not in EVALUATION_SEEDS
        ):
            raise RuntimeError(
                "evaluation mode accepts only frozen evaluation seeds"
            )
    else:
        if (
            stream_seed
            not in DEVELOPMENT_SEEDS
        ):
            raise RuntimeError(
                "development mode accepts only frozen development seeds"
            )

    learner_seed = (
        splitmix64(
            stream_seed
            ^ sum(
                ord(ch)
                for ch in condition
            )
        )
    )

    learner = (
        TargetTableLearner(
            learner_seed
        )
    )

    engine = None

    if (
        condition
        == "M20-CONSTRUCTION"
    ):
        engine = (
            CompositionalAdaptiveConstructionEngine(
                max_lag=8,
                max_candidates=256,
                enable_scaffolds=True,
            )
        )

        engine.begin_episode()

    stream = (
        observation_stream(
            stream_seed
        )
    )

    history: list[
        int
    ] = []

    outcomes: list[
        int
    ] = []

    authorization_events: list[
        int
    ] = []

    authorized_ids: list[
        str
    ] = []

    cumulative = 0
    curve_sum = 0

    for event_index in range(
        STEPS
    ):
        observation = next(
            stream
        )

        history.append(
            observation
        )

        if len(history) > 9:
            del history[:-9]

        history_tuple = tuple(
            history
        )

        target = task.target(
            history_tuple
        )

        if condition == "REACTIVE":
            state = (
                observation,
            )

        elif condition == "FIXED-H8":
            state = fixed_h8_state(
                observation,
                history_tuple,
            )

        elif condition == "ORACLE-FEATURE":
            state = oracle_state(
                observation,
                task,
                history_tuple,
            )

        elif (
            condition
            == "M20-CONSTRUCTION"
        ):
            assert (
                engine is not None
            )

            state = engine.observe(
                observation
            )

        else:
            raise RuntimeError(
                "unreachable condition"
            )

        action = learner.choose(
            state,
            event_index,
        )

        correct = int(
            action
            == target
        )

        learner.update(
            state,
            target,
        )

        if engine is not None:
            decision = (
                engine.finalize(
                    target
                )
            )

            if decision.authorized:
                authorization_events.append(
                    event_index
                )

                assert (
                    decision.construction_id
                    is not None
                )

                authorized_ids.append(
                    decision.construction_id
                )

        outcomes.append(
            correct
        )

        cumulative += correct

        curve_sum += (
            PPM
            * cumulative
        ) // (
            event_index + 1
        )

    final_window = (
        outcomes[
            -FINAL_WINDOW:
        ]
    )

    receipt_valid = True
    active_count = 0
    exact_target = None
    field = None

    if engine is not None:
        receipt_valid = (
            verify_receipt_chain(
                engine.receipt_chain,
                expected_count=len(
                    engine.receipt_chain
                ),
            )
        )

        active_count = len(
            engine.active_construction_ids
        )

        exact_target = (
            target_construction_active(
                engine,
                task,
            )
        )

        snapshot = (
            engine.candidate_field_snapshot()
        )

        field = {
            "epoch": (
                snapshot.epoch
            ),
            "candidate_count": (
                snapshot.candidate_count
            ),
            "primitive_candidate_count": (
                snapshot.primitive_candidate_count
            ),
            "scaffold_candidate_count": (
                snapshot.scaffold_candidate_count
            ),
            "composed_candidate_count": (
                snapshot.composed_candidate_count
            ),
            "active_construction_count": (
                snapshot.active_construction_count
            ),
            "threshold": (
                snapshot.threshold
            ),
        }

    payload = {
        "task": task.name,
        "stream_seed": (
            stream_seed
        ),
        "condition": condition,
        "steps": STEPS,
        "primary_aulc_ppm": (
            curve_sum
            // STEPS
        ),
        "final_window_accuracy_ppm": (
            PPM
            * sum(
                final_window
            )
            // len(
                final_window
            )
        ),
        "cumulative_mistakes": (
            STEPS
            - sum(
                outcomes
            )
        ),
        "authorized_construction_count": (
            active_count
        ),
        "authorization_events": (
            authorization_events
        ),
        "authorized_construction_ids": (
            authorized_ids
        ),
        "exact_target_construction_active": (
            exact_target
        ),
        "receipt_chain_valid": (
            receipt_valid
        ),
        "candidate_field": (
            field
        ),
    }

    return ArenaResult(
        payload=payload
    )
