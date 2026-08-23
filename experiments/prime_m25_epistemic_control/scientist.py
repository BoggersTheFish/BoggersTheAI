"""Global weighted active causal scientist for PRIME M25."""

from __future__ import annotations

from core.cognition.causal_certificate import (
    compatible_program_ids,
)
from core.cognition.causal_ecology import (
    CausalMassField,
    WeightedCausalStudySelector,
)
from core.cognition.causal_program import (
    program_lookup,
)


class EcologicalCausalScientist:
    def __init__(
        self,
        *,
        mass_field: CausalMassField,
    ) -> None:
        self.mass_field = (
            mass_field
        )

        self.observations: dict[
            tuple[int, ...],
            int,
        ] = {}

        self.survivors = set(
            program_lookup()
        )

        self.selector = (
            WeightedCausalStudySelector()
        )

        self.study_trace = []

    @property
    def identified_program_id(
        self,
    ) -> str | None:
        if len(
            self.survivors
        ) != 1:
            return None

        return next(
            iter(
                self.survivors
            )
        )

    def choose_intervention(
        self,
        *,
        intervention_cost,
    ):
        study = (
            self.selector.choose(
                surviving_program_ids=(
                    self.survivors
                ),
                observations=(
                    self.observations
                ),
                mass_field=(
                    self.mass_field
                ),
                intervention_cost=(
                    intervention_cost
                ),
            )
        )

        self.study_trace.append(
            study
        )

        return study.configuration

    def observe(
        self,
        configuration,
        outcome,
    ) -> None:
        self.observations[
            configuration
        ] = int(
            outcome
        )

        compatible = set(
            compatible_program_ids(
                self.observations
            )
        )

        self.survivors &= (
            compatible
        )

        if not self.survivors:
            raise RuntimeError(
                "causal program universe falsified"
            )
