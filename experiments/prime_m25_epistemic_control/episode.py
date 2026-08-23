"""Epistemic-control causal episode for PRIME M25."""

from __future__ import annotations

from dataclasses import dataclass

from core.cognition.causal_certificate import (
    CausalAuthorityLedger,
)
from core.cognition.causal_ecology import (
    CausalMassField,
)
from core.cognition.causal_program import (
    CONFIGURATIONS,
    CausalProgram,
    program_lookup,
)

from experiments.prime_m24_causal_program_world.lab import (
    ProgramLab,
)

from .scientist import (
    EcologicalCausalScientist,
)


@dataclass(frozen=True)
class EpistemicEpisodeResult:
    target_program_id: str
    target_label: str
    interventions: int
    discovery_steps: int
    total_steps: int
    target_initial_mass: int
    target_initial_rank: int
    prior_bonus_mass: int
    goal_reached: bool
    receipt_hash: str
    authorization: object
    study_trace: tuple[dict, ...]


def run_epistemic_episode(
    target: CausalProgram,
    *,
    mass_field: CausalMassField,
    authority_ledger: (
        CausalAuthorityLedger
        | None
    ) = None,
) -> EpistemicEpisodeResult:
    ledger = (
        authority_ledger
        if authority_ledger is not None
        else CausalAuthorityLedger()
    )

    lab = ProgramLab(
        target
    )

    scientist = (
        EcologicalCausalScientist(
            mass_field=(
                mass_field
            )
        )
    )

    while (
        scientist.identified_program_id
        is None
    ):
        configuration = (
            scientist.choose_intervention(
                intervention_cost=(
                    lab.cost_to_probe
                )
            )
        )

        outcome = (
            lab.intervene(
                configuration
            )
        )

        scientist.observe(
            configuration,
            outcome,
        )

    identified = (
        scientist.identified_program_id
    )

    if (
        identified
        != target.program_id
    ):
        raise RuntimeError(
            "wrong causal program identified"
        )

    authorization = (
        ledger.authorize(
            identified,
            scientist.observations,
        )
    )

    if not authorization.verdict:
        raise RuntimeError(
            "causal authority rejected singleton identification"
        )

    discovery_steps = (
        lab.state.steps
    )

    verified = (
        program_lookup()[
            identified
        ]
    )

    openings = [
        configuration
        for configuration
        in CONFIGURATIONS
        if verified.evaluate(
            configuration
        )
    ]

    goal_options = []

    for configuration in openings:
        cost = (
            lab.cost_to_goal(
                configuration
            )
        )

        if cost is not None:
            goal_options.append(
                (
                    cost,
                    configuration,
                )
            )

    if not goal_options:
        raise RuntimeError(
            "no reachable verified goal plan"
        )

    goal_options.sort()

    _, selected = (
        goal_options[0]
    )

    lab.set_configuration(
        selected
    )

    lab.walk_to(
        lab.layout.goal
    )

    trace = tuple(
        {
            "configuration": list(
                study.configuration
            ),
            "primitive_cost": (
                study.primitive_cost
            ),
            "zero_mass": (
                study.zero_mass
            ),
            "one_mass": (
                study.one_mass
            ),
            "zero_count": (
                study.zero_count
            ),
            "one_count": (
                study.one_count
            ),
        }
        for study in (
            scientist.study_trace
        )
    )

    return EpistemicEpisodeResult(
        target_program_id=(
            target.program_id
        ),
        target_label=(
            target.label
        ),
        interventions=len(
            scientist.observations
        ),
        discovery_steps=(
            discovery_steps
        ),
        total_steps=(
            lab.state.steps
        ),
        target_initial_mass=(
            mass_field.mass(
                target.program_id
            )
        ),
        target_initial_rank=(
            mass_field.rank(
                target.program_id
            )
        ),
        prior_bonus_mass=(
            mass_field.bonus_mass
        ),
        goal_reached=(
            lab.state.goal_reached
        ),
        receipt_hash=(
            authorization.receipt_hash
        ),
        authorization=(
            authorization
        ),
        study_trace=(
            trace
        ),
    )
