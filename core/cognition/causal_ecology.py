"""Universal weighted causal hypothesis ecology for PRIME M25."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .causal_memory import (
    CausalProgramMemory,
    schema_descriptor,
)
from .causal_program import (
    CONFIGURATIONS,
    program_lookup,
    program_universe,
)


BASE_MASS = 1024


@dataclass(frozen=True)
class CausalMassField:
    mass_by_id: dict[str, int]
    base_mass: int
    universal_mass: int
    bonus_mass: int
    total_mass: int
    memory_program_count: int
    schema_count: int

    def mass(
        self,
        program_id: str,
    ) -> int:
        return self.mass_by_id[
            program_id
        ]

    def rank(
        self,
        program_id: str,
    ) -> int:
        lookup = program_lookup()

        ordered = sorted(
            self.mass_by_id,
            key=lambda pid: (
                -self.mass_by_id[pid],
                lookup[pid].label,
            ),
        )

        return (
            ordered.index(
                program_id
            )
            + 1
        )


def build_causal_mass_field(
    memory: (
        CausalProgramMemory
        | None
    ),
) -> CausalMassField:
    universe = (
        program_universe()
    )

    mass_by_id = {
        program.program_id: (
            BASE_MASS
        )
        for program
        in universe
    }

    universal_mass = (
        BASE_MASS
        * len(universe)
    )

    if memory is None:
        return CausalMassField(
            mass_by_id=mass_by_id,
            base_mass=BASE_MASS,
            universal_mass=(
                universal_mass
            ),
            bonus_mass=0,
            total_mass=(
                universal_mass
            ),
            memory_program_count=0,
            schema_count=0,
        )

    raw_bonus = {
        program.program_id: 0
        for program
        in universe
    }

    # Exact verified causal experience.
    for program_id, entry in (
        memory.entries.items()
    ):
        if program_id not in (
            raw_bonus
        ):
            continue

        recency = max(
            0,
            16
            - (
                memory.sequence
                - entry.last_sequence
            ),
        )

        raw_bonus[
            program_id
        ] += max(
            0,
            (
                4096
                + 1536
                * entry.times_verified
                + 768
                * entry.successful_reuses
                - 1024
                * entry.failed_reuses
                + 128
                * recency
            ),
        )

    schemas = (
        memory.schemas()
    )

    # Schema knowledge can raise an unseen program without
    # making the schema itself authoritative.
    for schema in schemas:
        for program in universe:
            if (
                schema_descriptor(
                    program
                )
                != (
                    schema.operator,
                    schema.normalized_offsets,
                )
            ):
                continue

            raw_bonus[
                program.program_id
            ] += (
                2048
                * schema.support
            )

    raw_total = sum(
        raw_bonus.values()
    )

    # Safety mixture:
    #
    # total prior-derived mass <= universal baseline mass.
    #
    # Thus universal support is never less than half the
    # pre-observation proposal mass.
    bonus_budget = min(
        universal_mass,
        raw_total,
    )

    scaled_bonus = {
        program_id: 0
        for program_id
        in raw_bonus
    }

    if (
        raw_total > 0
        and bonus_budget > 0
    ):
        for program_id, raw in (
            raw_bonus.items()
        ):
            scaled_bonus[
                program_id
            ] = (
                raw
                * bonus_budget
                // raw_total
            )

    for program_id, bonus in (
        scaled_bonus.items()
    ):
        mass_by_id[
            program_id
        ] += bonus

    bonus_mass = sum(
        scaled_bonus.values()
    )

    return CausalMassField(
        mass_by_id=mass_by_id,
        base_mass=BASE_MASS,
        universal_mass=(
            universal_mass
        ),
        bonus_mass=(
            bonus_mass
        ),
        total_mass=(
            universal_mass
            + bonus_mass
        ),
        memory_program_count=len(
            memory.entries
        ),
        schema_count=len(
            schemas
        ),
    )


@dataclass(frozen=True)
class EpistemicStudy:
    configuration: tuple[int, ...]
    zero_mass: int
    one_mass: int
    surviving_mass: int
    primitive_cost: int
    information_product: int
    value_per_cost: Fraction
    worst_case_mass: int
    zero_count: int
    one_count: int


class WeightedCausalStudySelector:
    """Select globally useful interventions.

    Prior mass alters experiment order only.

    Exact hypothesis elimination and causal authority remain
    separate.
    """

    def choose(
        self,
        *,
        surviving_program_ids: set[
            str
        ],
        observations: dict[
            tuple[int, ...],
            int,
        ],
        mass_field: CausalMassField,
        intervention_cost,
    ) -> EpistemicStudy:
        if len(
            surviving_program_ids
        ) <= 1:
            raise ValueError(
                "study requested after identification"
            )

        lookup = (
            program_lookup()
        )

        rows = []

        for configuration in (
            CONFIGURATIONS
        ):
            if (
                configuration
                in observations
            ):
                continue

            zero_ids = []
            one_ids = []

            zero_mass = 0
            one_mass = 0

            for program_id in (
                surviving_program_ids
            ):
                outcome = (
                    lookup[
                        program_id
                    ].evaluate(
                        configuration
                    )
                )

                if outcome:
                    one_ids.append(
                        program_id
                    )

                    one_mass += (
                        mass_field.mass(
                            program_id
                        )
                    )

                else:
                    zero_ids.append(
                        program_id
                    )

                    zero_mass += (
                        mass_field.mass(
                            program_id
                        )
                    )

            if (
                zero_mass == 0
                or one_mass == 0
            ):
                continue

            cost = max(
                1,
                int(
                    intervention_cost(
                        configuration
                    )
                ),
            )

            # For deterministic binary observations,
            # expected eliminated probability mass is proportional
            # to m0*m1/M. M is constant across candidate studies.
            information_product = (
                zero_mass
                * one_mass
            )

            rows.append(
                EpistemicStudy(
                    configuration=(
                        configuration
                    ),
                    zero_mass=(
                        zero_mass
                    ),
                    one_mass=(
                        one_mass
                    ),
                    surviving_mass=(
                        zero_mass
                        + one_mass
                    ),
                    primitive_cost=(
                        cost
                    ),
                    information_product=(
                        information_product
                    ),
                    value_per_cost=Fraction(
                        information_product,
                        cost,
                    ),
                    worst_case_mass=max(
                        zero_mass,
                        one_mass,
                    ),
                    zero_count=len(
                        zero_ids
                    ),
                    one_count=len(
                        one_ids
                    ),
                )
            )

        if not rows:
            raise RuntimeError(
                "no discriminating causal intervention remains"
            )

        rows.sort(
            key=lambda row: (
                -row.value_per_cost,
                row.worst_case_mass,
                -min(
                    row.zero_count,
                    row.one_count,
                ),
                row.primitive_cost,
                row.configuration,
            )
        )

        return rows[0]
