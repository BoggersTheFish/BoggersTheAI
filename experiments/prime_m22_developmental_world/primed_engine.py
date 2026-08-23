"""Transfer-primed M20 construction engine for M22."""

from __future__ import annotations

from core.construction.compositional_engine import (
    CompositionalAdaptiveConstructionEngine,
)
from core.construction.types import (
    ConstructionSpec,
)


class PrimedConstructionEngine(
    CompositionalAdaptiveConstructionEngine
):
    """M20 construction with externally ranked proposal candidates.

    External candidates change proposal search only.

    Verifier authority remains inherited unchanged from M20.
    """

    def __init__(
        self,
        *,
        priority_specs: tuple[
            ConstructionSpec,
            ...,
        ] = (),
        max_lag: int = 8,
        cold_candidate_limit: int = 256,
        primed_candidate_limit: int = 64,
    ) -> None:
        self._priority_specs = (
            priority_specs
        )

        self.primed = bool(
            priority_specs
        )

        limit = (
            primed_candidate_limit
            if self.primed
            else cold_candidate_limit
        )

        super().__init__(
            max_lag=max_lag,
            max_candidates=limit,
            enable_scaffolds=True,
        )

    def _candidate_field(
        self,
    ):
        base = list(
            super()._candidate_field()
        )

        active = set(
            self.registry.active_ids()
        )

        combined = {}

        # Deliberately preserve learned proposal order.
        for spec in (
            self._priority_specs
        ):
            if (
                spec.construction_id
                not in active
            ):
                combined[
                    spec.construction_id
                ] = spec

        for spec in base:
            if (
                spec.construction_id
                not in active
                and spec.construction_id
                not in combined
            ):
                combined[
                    spec.construction_id
                ] = spec

        return tuple(
            list(
                combined.values()
            )[
                :self.max_candidates
            ]
        )

    @property
    def priority_construction_ids(
        self,
    ) -> tuple[str, ...]:
        return tuple(
            spec.construction_id
            for spec
            in self._priority_specs
        )
