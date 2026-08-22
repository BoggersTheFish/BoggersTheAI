"""Anytime-valid construction evidence for PRIME M20."""

from __future__ import annotations

from dataclasses import dataclass

from .grammar import (
    description_length,
    evaluate,
)
from .types import (
    ConstructionSpec,
    EvidenceSnapshot,
)


OBSTRUCTION_MIN_PER_TARGET = 8
RUN_LEVEL_ALPHA_DENOMINATOR = 64


class BinaryMajorityPredictor:
    def __init__(self) -> None:
        self._counts: dict[
            tuple[int, ...],
            list[int],
        ] = {}

    def predict(
        self,
        state: tuple[int, ...],
    ) -> int:
        counts = self._counts.get(
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
        if target not in (0, 1):
            raise ValueError(
                "target must be binary"
            )

        counts = self._counts.setdefault(
            state,
            [0, 0],
        )

        counts[target] += 1


@dataclass
class CandidateEvidence:
    spec: ConstructionSpec
    predictor: BinaryMajorityPredictor
    wins: int = 0
    losses: int = 0

    @property
    def discordant(self) -> int:
        return self.wins + self.losses

    @property
    def net_advantage(self) -> int:
        return self.wins - self.losses

    @property
    def structural_cost(self) -> int:
        return description_length(
            self.spec.expression
        )

    def evidence_lhs(self) -> int:
        return 3 ** self.wins

    def evidence_rhs(
        self,
        threshold: int,
    ) -> int:
        return (
            threshold
            * 2 ** self.discordant
        )

    def statistical_pass(
        self,
        threshold: int,
    ) -> bool:
        return (
            self.evidence_lhs()
            >= self.evidence_rhs(
                threshold
            )
        )

    def structural_pass(self) -> bool:
        return (
            self.net_advantage
            > self.structural_cost
        )

    def supported(
        self,
        threshold: int,
    ) -> bool:
        return (
            self.statistical_pass(
                threshold
            )
            and self.structural_pass()
        )


@dataclass(frozen=True)
class FrozenPredictions:
    canonical_state: tuple[int, ...]
    canonical_prediction: int
    candidate_states: dict[
        str,
        tuple[int, ...],
    ]
    candidate_predictions: dict[
        str,
        int,
    ]


@dataclass(frozen=True)
class EvidenceOutcome:
    obstruction_open: bool
    obstruction_just_opened: bool
    supported_ids: tuple[str, ...]


class EvidenceEpoch:
    def __init__(
        self,
        candidates: tuple[
            ConstructionSpec,
            ...,
        ],
    ) -> None:
        self.candidates = candidates

        self.threshold = (
            RUN_LEVEL_ALPHA_DENOMINATOR
            * max(
                1,
                len(candidates),
            )
        )

        self.canonical_predictor = (
            BinaryMajorityPredictor()
        )

        self.trackers = {
            spec.construction_id: (
                CandidateEvidence(
                    spec=spec,
                    predictor=(
                        BinaryMajorityPredictor()
                    ),
                )
            )
            for spec in candidates
        }

        self.obstruction_counts: dict[
            tuple[int, ...],
            list[int],
        ] = {}

        self.obstruction_open = False
        self.obstruction_event_index: (
            int | None
        ) = None

    def freeze(
        self,
        canonical_state: tuple[int, ...],
        verifier_history: tuple[int, ...],
        resolved: dict[str, int] | None = None,
    ) -> FrozenPredictions:
        canonical_prediction = (
            self.canonical_predictor.predict(
                canonical_state
            )
        )

        states = {}
        predictions = {}

        for construction_id, tracker in (
            self.trackers.items()
        ):
            bit = evaluate(
                tracker.spec.expression,
                verifier_history,
                resolved,
            )

            candidate_state = (
                canonical_state
                + (bit,)
            )

            states[
                construction_id
            ] = candidate_state

            predictions[
                construction_id
            ] = tracker.predictor.predict(
                candidate_state
            )

        return FrozenPredictions(
            canonical_state=(
                canonical_state
            ),
            canonical_prediction=(
                canonical_prediction
            ),
            candidate_states=states,
            candidate_predictions=(
                predictions
            ),
        )

    def _has_obstruction(self) -> bool:
        return any(
            counts[0]
            >= OBSTRUCTION_MIN_PER_TARGET
            and counts[1]
            >= OBSTRUCTION_MIN_PER_TARGET
            for counts
            in self.obstruction_counts.values()
        )

    def supported_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            construction_id
            for construction_id, tracker
            in self.trackers.items()
            if tracker.supported(
                self.threshold
            )
        )

    def snapshot(
        self,
        construction_id: str,
        *,
        authorization_event_index: (
            int | None
        ) = None,
    ) -> EvidenceSnapshot:
        tracker = self.trackers[
            construction_id
        ]

        statistical = (
            tracker.statistical_pass(
                self.threshold
            )
        )

        structural = (
            tracker.structural_pass()
        )

        return EvidenceSnapshot(
            construction_id=(
                construction_id
            ),
            wins=tracker.wins,
            losses=tracker.losses,
            threshold=self.threshold,
            evidence_lhs=(
                tracker.evidence_lhs()
            ),
            evidence_rhs=(
                tracker.evidence_rhs(
                    self.threshold
                )
            ),
            statistical_pass=(
                statistical
            ),
            structural_cost=(
                tracker.structural_cost
            ),
            structural_pass=(
                structural
            ),
            supported=(
                statistical
                and structural
            ),
            obstruction_event_index=(
                self.obstruction_event_index
            ),
            authorization_event_index=(
                authorization_event_index
            ),
        )

    def finalize(
        self,
        frozen: FrozenPredictions,
        *,
        target: int,
        event_index: int,
    ) -> EvidenceOutcome:
        if target not in (0, 1):
            raise ValueError(
                "target must be binary"
            )

        for construction_id, tracker in (
            self.trackers.items()
        ):
            candidate_prediction = (
                frozen.candidate_predictions[
                    construction_id
                ]
            )

            if (
                candidate_prediction
                != frozen.canonical_prediction
            ):
                if (
                    candidate_prediction
                    == target
                ):
                    tracker.wins += 1
                else:
                    tracker.losses += 1

        bucket = (
            self.obstruction_counts.setdefault(
                frozen.canonical_state,
                [0, 0],
            )
        )

        bucket[target] += 1

        self.canonical_predictor.update(
            frozen.canonical_state,
            target,
        )

        for construction_id, tracker in (
            self.trackers.items()
        ):
            tracker.predictor.update(
                frozen.candidate_states[
                    construction_id
                ],
                target,
            )

        just_opened = False

        if (
            not self.obstruction_open
            and self._has_obstruction()
        ):
            self.obstruction_open = True
            self.obstruction_event_index = (
                event_index
            )
            just_opened = True

        supported: tuple[str, ...] = ()

        if self.obstruction_open:
            supported = (
                self.supported_ids()
            )

        return EvidenceOutcome(
            obstruction_open=(
                self.obstruction_open
            ),
            obstruction_just_opened=(
                just_opened
            ),
            supported_ids=supported,
        )
