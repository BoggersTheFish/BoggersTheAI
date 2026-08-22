"""Higher-order adaptive construction engine for PRIME M20."""

from __future__ import annotations

from dataclasses import dataclass

from .composition import (
    generate_composed_candidates,
)
from .evidence import (
    EvidenceEpoch,
    FrozenPredictions,
)
from .engine import (
    ConstructionDecision,
    VerifierGate,
)
from .grammar import (
    description_length,
    generate_bounded_candidates,
    required_history,
)
from .registry import (
    ConstructionRegistry,
)
from .state import (
    ConstructionStateBuilder,
)
from .types import (
    ConstructionSpec,
)


@dataclass(frozen=True)
class CandidateFieldSnapshot:
    epoch: int
    candidate_count: int
    primitive_candidate_count: int
    composed_candidate_count: int
    active_construction_count: int
    threshold: int


class CompositionalAdaptiveConstructionEngine:
    """PRIME M20-B/C.

    Candidate grammar expands after each authorization.

    Authorized constructions become typed reusable atoms.

    Candidate field remains bounded.
    """

    def __init__(
        self,
        *,
        max_lag: int = 8,
        max_candidates: int = 128,
    ) -> None:
        self.max_lag = max_lag
        self.max_candidates = (
            max_candidates
        )

        self.registry = (
            ConstructionRegistry()
        )

        self.state_builder = (
            ConstructionStateBuilder(
                self.registry
            )
        )

        self.verifier = (
            VerifierGate()
        )

        self._private_history: list[
            int
        ] = []

        self._event_index = -1
        self._epoch_index = 0

        self._pending: (
            FrozenPredictions
            | None
        ) = None

        self._primitive_specs = (
            generate_bounded_candidates(
                max_lag=max_lag,
                max_candidates=(
                    max_candidates
                ),
            )
        )

        self._candidate_specs: tuple[
            ConstructionSpec,
            ...,
        ] = ()

        self._epoch = (
            self._build_epoch()
        )

    def _candidate_field(
        self,
    ) -> tuple[
        ConstructionSpec,
        ...,
    ]:
        active = set(
            self.registry.active_ids()
        )

        combined: dict[
            str,
            ConstructionSpec,
        ] = {}

        for spec in (
            self._primitive_specs
        ):
            if (
                spec.construction_id
                not in active
            ):
                combined[
                    spec.construction_id
                ] = spec

        for spec in (
            generate_composed_candidates(
                self.registry,
                max_lag=self.max_lag,
                max_candidates=(
                    self.max_candidates
                ),
            )
        ):
            if (
                spec.construction_id
                not in active
            ):
                combined[
                    spec.construction_id
                ] = spec

        ordered = sorted(
            combined.values(),
            key=lambda spec: (
                description_length(
                    spec.expression
                ),
                required_history(
                    spec.expression
                ),
                spec.construction_id,
            ),
        )

        return tuple(
            ordered[
                :self.max_candidates
            ]
        )

    def _build_epoch(
        self,
    ) -> EvidenceEpoch:
        candidates = (
            self._candidate_field()
        )

        for spec in candidates:
            self.registry.propose(
                spec
            )

        self._candidate_specs = (
            candidates
        )

        return EvidenceEpoch(
            candidates
        )

    def begin_episode(self) -> None:
        self._private_history = []
        self._pending = None

        self.state_builder.reset_episode()

    def observe(
        self,
        observation: int,
    ) -> tuple[int, ...]:
        if self._pending is not None:
            raise RuntimeError(
                "previous observation "
                "must be finalized"
            )

        self._event_index += 1

        self._private_history.append(
            observation
        )

        if (
            len(
                self._private_history
            )
            > self.max_lag + 1
        ):
            del self._private_history[
                :-(self.max_lag + 1)
            ]

        policy_state = (
            self.state_builder.observe(
                observation
            )
        )

        self._pending = (
            self._epoch.freeze(
                policy_state,
                tuple(
                    self._private_history
                ),
                self.state_builder.current_values,
            )
        )

        return policy_state

    def _select(
        self,
        supported_ids: tuple[
            str,
            ...,
        ],
    ) -> str:
        lookup = {
            spec.construction_id: spec
            for spec
            in self._candidate_specs
        }

        return min(
            supported_ids,
            key=lambda construction_id: (
                description_length(
                    lookup[
                        construction_id
                    ].expression
                ),
                required_history(
                    lookup[
                        construction_id
                    ].expression
                ),
                construction_id,
            ),
        )

    def finalize(
        self,
        target: int,
    ) -> ConstructionDecision:
        if self._pending is None:
            raise RuntimeError(
                "observe must occur first"
            )

        frozen = self._pending
        self._pending = None

        outcome = (
            self._epoch.finalize(
                frozen,
                target=target,
                event_index=(
                    self._event_index
                ),
            )
        )

        if not outcome.supported_ids:
            return ConstructionDecision(
                authorized=False,
                construction_id=None,
                evidence=None,
                receipt=None,
            )

        selected = (
            self._select(
                outcome.supported_ids
            )
        )

        evidence = (
            self._epoch.snapshot(
                selected,
                authorization_event_index=(
                    self._event_index
                ),
            )
        )

        authorization = (
            self.verifier.authorize(
                evidence
            )
        )

        receipt = (
            self.registry.apply(
                authorization
            )
        )

        # Candidate field grows only after
        # verifier-backed authorization.
        self._epoch_index += 1

        self._epoch = (
            self._build_epoch()
        )

        return ConstructionDecision(
            authorized=True,
            construction_id=selected,
            evidence=evidence,
            receipt=receipt,
        )

    def candidate_field_snapshot(
        self,
    ) -> CandidateFieldSnapshot:
        primitive_ids = {
            spec.construction_id
            for spec
            in self._primitive_specs
        }

        primitive = sum(
            spec.construction_id
            in primitive_ids
            for spec
            in self._candidate_specs
        )

        composed = (
            len(
                self._candidate_specs
            )
            - primitive
        )

        return CandidateFieldSnapshot(
            epoch=self._epoch_index,
            candidate_count=len(
                self._candidate_specs
            ),
            primitive_candidate_count=(
                primitive
            ),
            composed_candidate_count=(
                composed
            ),
            active_construction_count=len(
                self.registry.active_ids()
            ),
            threshold=(
                self._epoch.threshold
            ),
        )

    @property
    def active_construction_ids(
        self,
    ) -> tuple[str, ...]:
        return self.registry.active_ids()

    @property
    def receipt_chain(
        self,
    ) -> list[dict]:
        return (
            self.registry.receipts.records
        )
