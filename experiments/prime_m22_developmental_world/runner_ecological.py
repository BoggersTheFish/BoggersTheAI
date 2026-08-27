"""Cold versus persistent developmental PRIME."""

from __future__ import annotations

from dataclasses import dataclass

from core.cognition import (
    MegaPrimeCognition,
)
from core.construction.quotient import (
    active_partition_matches,
)
from core.construction.receipts import (
    verify_receipt_chain,
)

from .candidate_source import (
    DevelopmentalCandidate,
    DevelopmentalCandidateSource,
)
from .ecological_engine import (
    EcologicalConstructionEngine,
)
from .world import (
    ChapterSpec,
    binary_stream,
    curriculum,
    splitmix64,
)


PPM = 1_000_000
FINAL_WINDOW = 256


class OnlineTableLearner:
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
        # Identical action randomness for cold/persistent modes.
        explore = (
            splitmix64(
                self.seed
                ^ splitmix64(
                    event_index
                )
            )
            % 10
            == 0
        )

        if explore:
            return (
                splitmix64(
                    self.seed
                    ^ 0x4D32324143544E
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
        counts = (
            self.counts.setdefault(
                state,
                [0, 0],
            )
        )

        counts[
            target
        ] += 1


@dataclass(frozen=True)
class ChapterResult:
    payload: dict


def target_recovered(
    engine: EcologicalConstructionEngine,
    chapter: ChapterSpec,
) -> bool:
    if chapter.expression is None:
        return (
            len(
                engine.active_construction_ids
            )
            == 0
        )

    return bool(
        active_partition_matches(
            engine.registry,
            chapter.expression,
            max_lag=8,
        )
    )


def run_chapter(
    chapter: ChapterSpec,
    *,
    cognition: (
        MegaPrimeCognition
        | None
    ),
    persistent: bool,
) -> ChapterResult:
    if (
        persistent
        and cognition is None
    ):
        raise ValueError(
            "persistent mode requires cognition"
        )

    priority_rows: tuple[
        DevelopmentalCandidate,
        ...,
    ] = ()

    if persistent:
        assert cognition is not None

        source = (
            DevelopmentalCandidateSource(
                cognition
            )
        )

        priority_rows = (
            source.propose(
                context_tokens=(
                    chapter.context_tokens
                ),
                max_candidates=64,
            )
        )

    priority_specs = tuple(
        row.spec
        for row in priority_rows
    )

    engine = (
        EcologicalConstructionEngine(
            priority_specs=(
                priority_specs
            ),
            max_lag=8,
            universal_candidate_limit=256,
        )
    )

    initial_field = (
        engine.candidate_field_snapshot()
    )

    initial_ecology = (
        engine.ecology_snapshot()
    )

    engine.begin_episode()

    learner = (
        OnlineTableLearner(
            splitmix64(
                chapter.seed
                ^ 0x4D32324C4541524E
            )
        )
    )

    stream = (
        binary_stream(
            chapter.seed
        )
    )

    history: list[int] = []

    outcomes = []

    cumulative_correct = 0
    curve_sum = 0

    first_authorization_event = None
    first_recovery_event = None

    authorized_ids = []

    accepted_priority: set[
        str
    ] = set()

    for event_index in range(
        chapter.steps
    ):
        observation = next(
            stream
        )

        history.append(
            observation
        )

        if len(history) > 9:
            del history[:-9]

        target = (
            chapter.target(
                tuple(history)
            )
        )

        state = engine.observe(
            observation
        )

        action = learner.choose(
            state,
            event_index,
        )

        correct = int(
            action == target
        )

        learner.update(
            state,
            target,
        )

        decision = (
            engine.finalize(
                target
            )
        )

        if decision.authorized:
            assert (
                decision.construction_id
                is not None
            )

            authorized_ids.append(
                decision.construction_id
            )

            if (
                first_authorization_event
                is None
            ):
                first_authorization_event = (
                    event_index
                )

            if (
                decision.construction_id
                in engine.priority_construction_ids
            ):
                accepted_priority.add(
                    decision.construction_id
                )

            if (
                first_recovery_event
                is None
                and target_recovered(
                    engine,
                    chapter,
                )
            ):
                first_recovery_event = (
                    event_index
                )

        outcomes.append(
            correct
        )

        cumulative_correct += (
            correct
        )

        curve_sum += (
            PPM
            * cumulative_correct
            // (
                event_index
                + 1
            )
        )

    recovered = (
        target_recovered(
            engine,
            chapter,
        )
    )

    accuracy_ppm = (
        PPM
        * sum(outcomes)
        // len(outcomes)
    )

    final = outcomes[
        -min(
            FINAL_WINDOW,
            len(outcomes),
        ):
    ]

    final_accuracy_ppm = (
        PPM
        * sum(final)
        // len(final)
    )

    if persistent:
        assert cognition is not None

        priority_lookup = {
            row.spec.construction_id: row
            for row in priority_rows
        }

        for construction_id in (
            accepted_priority
        ):
            row = priority_lookup[
                construction_id
            ]

            cognition.proposal_field.update(
                row.spec,
                chapter.context_tokens,
                accepted=True,
                gain_ppm=100000,
            )

            cognition.meta_memory.record(
                row.source,
                accepted=True,
                gain_ppm=100000,
            )

            if row.memory_id is not None:
                cognition.semantic_memory.record_transfer_outcome(
                    row.memory_id,
                    accepted=True,
                    gain_ppm=100000,
                )

        cognition.close_world(
            engine.registry,
            context_id=(
                chapter.chapter_id
            ),
            context_tokens=(
                chapter.context_tokens
            ),
            reward_ppm=(
                accuracy_ppm
            ),
            tensions=(
                ()
                if recovered
                else (
                    "representation-unresolved",
                )
            ),
        )

    return ChapterResult(
        payload={
            "chapter_id": (
                chapter.chapter_id
            ),
            "seed": (
                chapter.seed
            ),
            "developmental_role": (
                chapter.developmental_role
            ),
            "persistent": persistent,
            "steps": chapter.steps,
            "primed": engine.primed,
            "priority_candidate_count": (
                len(priority_rows)
            ),
            "initial_candidate_count": (
                initial_field.candidate_count
            ),
            "initial_threshold": (
                initial_field.threshold
            ),
            "ecology_priority_count": (
                initial_ecology.priority_candidate_count
            ),
            "ecology_priority_mass_ppm": (
                initial_ecology.priority_mass_ppm
            ),
            "ecology_minimum_threshold": (
                initial_ecology.minimum_threshold
            ),
            "ecology_maximum_threshold": (
                initial_ecology.maximum_threshold
            ),
            "ecology_uniform_threshold": (
                initial_ecology.uniform_equivalent_threshold
            ),
            "first_authorization_event": (
                first_authorization_event
            ),
            "first_recovery_event": (
                first_recovery_event
            ),
            "recovered": recovered,
            "active_construction_count": (
                len(
                    engine.active_construction_ids
                )
            ),
            "authorized_ids": (
                authorized_ids
            ),
            "accepted_priority_count": (
                len(
                    accepted_priority
                )
            ),
            "aulc_ppm": (
                curve_sum
                // chapter.steps
            ),
            "accuracy_ppm": (
                accuracy_ppm
            ),
            "final_accuracy_ppm": (
                final_accuracy_ppm
            ),
            "receipt_chain_valid": (
                verify_receipt_chain(
                    engine.receipt_chain,
                    expected_count=len(
                        engine.receipt_chain
                    ),
                )
            ),
        }
    )


def run_curriculum(
    *,
    persistent: bool,
) -> tuple[
    list[dict],
    MegaPrimeCognition | None,
]:
    brain = (
        MegaPrimeCognition()
        if persistent
        else None
    )

    rows = []

    for chapter in curriculum():
        rows.append(
            run_chapter(
                chapter,
                cognition=brain,
                persistent=persistent,
            ).payload
        )

    return (
        rows,
        brain,
    )
