"""PRIME M26 comparative cognition runner."""

from __future__ import annotations

from dataclasses import dataclass

from core.construction.compositional_engine import (
    CompositionalAdaptiveConstructionEngine,
)
from core.construction.quotient import (
    active_partition_matches,
)
from core.construction.receipts import (
    verify_receipt_chain,
)

from .gru_agent import (
    GRUOnlinePredictor,
)
from .tasks import (
    ComparativeTask,
)


MASK64 = (
    (1 << 64) - 1
)

PPM = 1_000_000

STEPS = 1536

FINAL_WINDOW = 256

DEVELOPMENT_SEEDS = tuple(
    range(
        26000,
        26006,
    )
)

EVALUATION_SEEDS = tuple(
    range(
        36000,
        36032,
    )
)

CONDITIONS = (
    "REACTIVE",
    "H8",
    "H16",
    "GRU32",
    "PRIME",
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


def observation_stream(
    seed: int,
):
    state = splitmix64(
        seed
        ^ 0x4D3236434F474E49
    )

    while True:
        state = splitmix64(
            state
        )

        yield (
            state >> 63
        ) & 1


class OnlineTableLearner:
    def __init__(
        self,
        seed: int,
    ) -> None:
        self.seed = seed

        self.counts = {}

    def predict(
        self,
        state,
        event_index,
    ) -> int:
        counts = self.counts.get(
            state,
            (0, 0),
        )

        if counts[0] == counts[1]:
            return int(
                splitmix64(
                    self.seed
                    ^ splitmix64(
                        event_index
                    )
                )
                & 1
            )

        return int(
            counts[1]
            > counts[0]
        )

    def learn(
        self,
        state,
        target,
    ) -> None:
        counts = list(
            self.counts.get(
                state,
                (0, 0),
            )
        )

        counts[target] += 1

        self.counts[state] = tuple(
            counts
        )


@dataclass(frozen=True)
class WorldResult:
    payload: dict


def state_for_history(
    history,
    width,
):
    return tuple(
        history[-width:]
    )


def summarize_outcomes(
    outcomes,
):
    cumulative = 0
    curve = 0

    for index, value in enumerate(
        outcomes
    ):
        cumulative += value

        curve += (
            PPM
            * cumulative
            // (
                index + 1
            )
        )

    final = outcomes[
        -min(
            FINAL_WINDOW,
            len(outcomes),
        ):
    ]

    return {
        "aulc_ppm": (
            curve
            // len(outcomes)
        ),
        "accuracy_ppm": (
            PPM
            * sum(outcomes)
            // len(outcomes)
        ),
        "final_accuracy_ppm": (
            PPM
            * sum(final)
            // len(final)
        ),
        "mistakes": (
            len(outcomes)
            - sum(outcomes)
        ),
    }


def run_world(
    task: ComparativeTask,
    seed: int,
    condition: str,
    *,
    permit_evaluation: bool = False,
) -> WorldResult:
    if seed in EVALUATION_SEEDS:
        if not permit_evaluation:
            raise PermissionError(
                "M26 held-out evaluation is blocked"
            )

    elif seed not in DEVELOPMENT_SEEDS:
        raise PermissionError(
            "unregistered M26 seed"
        )

    if condition not in CONDITIONS:
        raise ValueError(
            condition
        )

    task_salt = sum(
        (
            index + 1
        )
        * ord(character)
        for index, character
        in enumerate(
            task.name
        )
    )

    stream = observation_stream(
        seed
        ^ splitmix64(
            task_salt
        )
    )

    history = []

    outcomes = []

    table = None
    gru = None
    prime = None

    first_authorization = None

    if condition in (
        "REACTIVE",
        "H8",
        "H16",
        "PRIME",
    ):
        table = OnlineTableLearner(
            splitmix64(
                seed
                ^ 0x4D32365441424C45
            )
        )

    if condition == "GRU32":
        gru = GRUOnlinePredictor(
            seed=(
                splitmix64(
                    seed
                    ^ task_salt
                    ^ 0x4D32364752553332
                )
                & 0x7FFFFFFF
            ),
            hidden_size=32,
            learning_rate=0.01,
            chunk_length=32,
        )

    if condition == "PRIME":
        prime = (
            CompositionalAdaptiveConstructionEngine(
                max_lag=16,
                max_candidates=512,
                enable_scaffolds=True,
            )
        )

        prime.begin_episode()

    for event_index in range(
        STEPS
    ):
        observation = next(
            stream
        )

        history.append(
            observation
        )

        target = (
            task.target_function(
                tuple(history),
                event_index,
                STEPS,
            )
        )

        if condition == "REACTIVE":
            state = (
                observation,
            )

            prediction = (
                table.predict(
                    state,
                    event_index,
                )
            )

            table.learn(
                state,
                target,
            )

        elif condition == "H8":
            state = (
                state_for_history(
                    history,
                    8,
                )
            )

            prediction = (
                table.predict(
                    state,
                    event_index,
                )
            )

            table.learn(
                state,
                target,
            )

        elif condition == "H16":
            state = (
                state_for_history(
                    history,
                    16,
                )
            )

            prediction = (
                table.predict(
                    state,
                    event_index,
                )
            )

            table.learn(
                state,
                target,
            )

        elif condition == "GRU32":
            prediction = (
                gru.predict(
                    observation
                )
            )

            gru.learn(
                target
            )

        elif condition == "PRIME":
            state = (
                prime.observe(
                    observation
                )
            )

            prediction = (
                table.predict(
                    state,
                    event_index,
                )
            )

            table.learn(
                state,
                target,
            )

            decision = (
                prime.finalize(
                    target
                )
            )

            if (
                decision.authorized
                and first_authorization
                is None
            ):
                first_authorization = (
                    event_index
                )

        else:
            raise AssertionError(
                condition
            )

        outcomes.append(
            int(
                prediction
                == target
            )
        )

    # Flush final incomplete GRU training chunk for diagnostics only.
    if (
        gru is not None
        and gru.chunk_y
    ):
        gru._train_chunk()

    summary = summarize_outcomes(
        outcomes
    )

    payload = {
        "task": task.name,
        "family": task.family,
        "seed": seed,
        "condition": condition,
        **summary,
    }

    if gru is not None:
        payload.update(
            {
                "gru_parameter_count": (
                    gru.parameter_count
                ),
                "gru_last_loss": (
                    gru.last_loss
                ),
            }
        )

    if prime is not None:
        explicit_recovery = None

        if (
            task.explicit_expression
            is not None
        ):
            explicit_recovery = bool(
                active_partition_matches(
                    prime.registry,
                    task.explicit_expression,
                    max_lag=16,
                )
            )

        payload.update(
            {
                "prime_first_authorization": (
                    first_authorization
                ),
                "prime_active_constructions": (
                    len(
                        prime.active_construction_ids
                    )
                ),
                "prime_explicit_recovery": (
                    explicit_recovery
                ),
                "prime_receipts_valid": (
                    verify_receipt_chain(
                        prime.receipt_chain,
                        expected_count=len(
                            prime.receipt_chain
                        ),
                    )
                ),
            }
        )

    return WorldResult(
        payload=payload
    )
