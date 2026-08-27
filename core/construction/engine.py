"""Verifier-governed adaptive construction engine for PRIME M20."""

from __future__ import annotations

from dataclasses import dataclass

from .evidence import (
    EvidenceEpoch,
    FrozenPredictions,
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
    AuthorityAction,
    ConstructionSpec,
    EvidenceSnapshot,
    VerifierAuthorization,
)


@dataclass(frozen=True)
class ConstructionDecision:
    authorized: bool
    construction_id: str | None
    evidence: EvidenceSnapshot | None
    receipt: dict | None


class VerifierGate:
    """Only this gate converts evidence into canonical authority."""

    def authorize(
        self,
        evidence: EvidenceSnapshot,
    ) -> VerifierAuthorization:
        if not evidence.supported:
            raise PermissionError(
                "unsupported evidence cannot authorize construction"
            )

        if (
            evidence.obstruction_event_index
            is None
        ):
            raise PermissionError(
                "construction cannot authorize before obstruction"
            )

        return VerifierAuthorization(
            action=(
                AuthorityAction.AUTHORIZE
            ),
            construction_id=(
                evidence.construction_id
            ),
            verdict=True,
            evidence_hash=(
                evidence.evidence_hash
            ),
            reason=(
                "ANYTIME_VALID_AND_STRUCTURAL_SUPPORT"
            ),
        )


class AdaptiveConstructionEngine:
    def __init__(
        self,
        *,
        candidates: (
            tuple[
                ConstructionSpec,
                ...,
            ]
            | None
        ) = None,
    ) -> None:
        self.registry = (
            ConstructionRegistry()
        )

        if candidates is None:
            candidates = (
                generate_bounded_candidates()
            )

        self.all_candidates = tuple(
            candidates
        )

        for spec in self.all_candidates:
            self.registry.propose(
                spec
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

        self._pending: (
            FrozenPredictions
            | None
        ) = None

        self._epoch = (
            self._new_evidence_epoch()
        )

    def _inactive_candidates(
        self,
    ) -> tuple[
        ConstructionSpec,
        ...,
    ]:
        active = set(
            self.registry.active_ids()
        )

        return tuple(
            spec
            for spec
            in self.all_candidates
            if spec.construction_id
            not in active
        )

    def _new_evidence_epoch(
        self,
    ) -> EvidenceEpoch:
        return EvidenceEpoch(
            self._inactive_candidates()
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
                "previous observation must be finalized before next observe"
            )

        self._event_index += 1

        self._private_history.append(
            observation
        )

        if len(
            self._private_history
        ) > 9:
            del self._private_history[
                :-9
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
            )
        )

        return policy_state

    def _select_supported(
        self,
        supported_ids: tuple[
            str,
            ...,
        ],
    ) -> str:
        lookup = {
            spec.construction_id: spec
            for spec
            in self.all_candidates
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
                "observe must occur before finalize"
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
            self._select_supported(
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

        # CRITICAL:
        # state_builder has never seen verifier-private history.
        # The newly active construction receives a fresh empty
        # prospective policy buffer when sync_registry() next runs.

        self._epoch = (
            self._new_evidence_epoch()
        )

        return ConstructionDecision(
            authorized=True,
            construction_id=selected,
            evidence=evidence,
            receipt=receipt,
        )

    @property
    def active_construction_ids(
        self,
    ) -> tuple[str, ...]:
        return self.registry.active_ids()

    @property
    def receipt_chain(self) -> list[dict]:
        return self.registry.receipts.records
