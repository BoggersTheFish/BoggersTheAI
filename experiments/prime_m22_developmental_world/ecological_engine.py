"""Full-coverage memory-weighted construction search for PRIME M22."""

from __future__ import annotations

from dataclasses import dataclass

from core.cognition.hypothesis_ecology import (
    HypothesisAllocation,
    WeightedEvidenceEpoch,
    allocate_hypothesis_mass,
)
from core.construction.compositional_engine import (
    CompositionalAdaptiveConstructionEngine,
)
from core.construction.types import (
    ConstructionSpec,
)


@dataclass(frozen=True)
class EcologySnapshot:
    candidate_count: int
    priority_candidate_count: int
    total_mass: int
    priority_mass: int
    priority_mass_ppm: int
    minimum_threshold: int
    maximum_threshold: int
    uniform_equivalent_threshold: int


class EcologicalConstructionEngine(
    CompositionalAdaptiveConstructionEngine
):
    """Universal coverage + past-informed verifier weighting."""

    def __init__(
        self,
        *,
        priority_specs: tuple[
            ConstructionSpec,
            ...,
        ] = (),
        max_lag: int = 8,
        universal_candidate_limit: int = 256,
    ) -> None:
        self._priority_specs_m22 = (
            priority_specs
        )

        self._priority_ids_m22 = tuple(
            spec.construction_id
            for spec
            in priority_specs
        )

        self._allocation: (
            HypothesisAllocation
            | None
        ) = None

        super().__init__(
            max_lag=max_lag,
            max_candidates=(
                universal_candidate_limit
            ),
            enable_scaffolds=True,
        )

    @property
    def primed(self) -> bool:
        return bool(
            self._priority_specs_m22
        )

    def _candidate_field(
        self,
    ) -> tuple[
        ConstructionSpec,
        ...,
    ]:
        # Frozen M20 universal field.
        universal = tuple(
            super()._candidate_field()
        )

        active = set(
            self.registry.active_ids()
        )

        combined = {}

        # Past-informed candidates are inserted first, but universal
        # candidates are NEVER truncated away.
        for spec in (
            self._priority_specs_m22
        ):
            if (
                spec.construction_id
                not in active
            ):
                combined[
                    spec.construction_id
                ] = spec

        for spec in universal:
            if (
                spec.construction_id
                not in active
            ):
                combined.setdefault(
                    spec.construction_id,
                    spec,
                )

        return tuple(
            combined.values()
        )

    def _build_epoch(
        self,
    ) -> WeightedEvidenceEpoch:
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

        priority_ids = tuple(
            construction_id
            for construction_id
            in self._priority_ids_m22
            if any(
                spec.construction_id
                == construction_id
                for spec in candidates
            )
        )

        allocation = (
            allocate_hypothesis_mass(
                candidates,
                priority_ids=(
                    priority_ids
                ),
            )
        )

        self._allocation = (
            allocation
        )

        return WeightedEvidenceEpoch(
            candidates,
            epoch_index=(
                self._epoch_index
            ),
            allocation=allocation,
        )

    @property
    def priority_construction_ids(
        self,
    ) -> tuple[str, ...]:
        if self._allocation is None:
            return ()

        return (
            self._allocation.priority_ids
        )

    @property
    def candidate_construction_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            spec.construction_id
            for spec in self._candidate_specs
        )

    def ecology_snapshot(
        self,
    ) -> EcologySnapshot:
        if self._allocation is None:
            raise RuntimeError(
                "no ecology allocation"
            )

        allocation = (
            self._allocation
        )

        thresholds = tuple(
            self._epoch.threshold_for(
                construction_id
            )
            for construction_id
            in allocation.mass_by_id
        )

        priority_mass = sum(
            allocation.mass_by_id[
                construction_id
            ]
            for construction_id
            in allocation.priority_ids
        )

        base_denominator = (
            64
            * (
                1
                << (
                    self._epoch_index
                    + 1
                )
            )
        )

        return EcologySnapshot(
            candidate_count=len(
                allocation.mass_by_id
            ),
            priority_candidate_count=len(
                allocation.priority_ids
            ),
            total_mass=(
                allocation.total_mass
            ),
            priority_mass=(
                priority_mass
            ),
            priority_mass_ppm=(
                0
                if allocation.total_mass
                == 0
                else (
                    1_000_000
                    * priority_mass
                    // allocation.total_mass
                )
            ),
            minimum_threshold=min(
                thresholds
            ),
            maximum_threshold=max(
                thresholds
            ),
            uniform_equivalent_threshold=(
                base_denominator
                * len(
                    allocation.mass_by_id
                )
            ),
        )
