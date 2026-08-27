"""Causal-program discovery -> authority -> planning."""

from __future__ import annotations

from dataclasses import dataclass

from core.cognition.causal_certificate import (
    CausalAuthorityLedger,
    CausalAuthorization,
    minimal_certificate,
)
from core.cognition.causal_program import (
    CONFIGURATIONS,
    CausalProgram,
    program_lookup,
)

from .lab import (
    ProgramLab,
)
from .scientist import (
    CausalProgramScientist,
)


@dataclass(frozen=True)
class ProgramEpisodeResult:
    target_program_id: str
    target_label: str
    priority_count: int
    target_was_priority: bool
    certificate_size: int
    interventions: int
    discovery_steps: int
    total_steps: int
    attempted_priority_ids: tuple[
        str,
        ...,
    ]
    falsified_priority_ids: tuple[
        str,
        ...,
    ]
    goal_reached: bool
    authorization: (
        CausalAuthorization
    )


def run_program_episode(
    target: CausalProgram,
    *,
    priority_program_ids=(),
    authority_ledger=None,
) -> ProgramEpisodeResult:
    ledger = (
        authority_ledger
        if authority_ledger is not None
        else CausalAuthorityLedger()
    )

    scientist = (
        CausalProgramScientist(
            priority_program_ids=(
                priority_program_ids
            )
        )
    )

    lab = ProgramLab(
        target
    )

    while (
        scientist.identified_program_id
        is None
    ):
        configuration = (
            scientist.choose_intervention()
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
            "causal scientist identified wrong program"
        )

    authorization = (
        ledger.authorize(
            identified,
            scientist.observations,
        )
    )

    if not authorization.verdict:
        raise RuntimeError(
            "causal authority rejected unique program"
        )

    discovery_steps = (
        lab.state.steps
    )

    verified = (
        program_lookup()[
            authorization.program_id
        ]
    )

    opening = [
        configuration
        for configuration
        in CONFIGURATIONS
        if verified.evaluate(
            configuration
        )
    ]

    ranked = []

    for configuration in opening:
        cost = lab.cost_to_goal(
            configuration
        )

        if cost is not None:
            ranked.append(
                (
                    cost,
                    configuration,
                )
            )

    if not ranked:
        raise RuntimeError(
            "verified program yields no reachable opening"
        )

    ranked.sort()

    _, selected = (
        ranked[0]
    )

    lab.set_configuration(
        selected
    )

    lab.walk_to(
        lab.layout.goal
    )

    return ProgramEpisodeResult(
        target_program_id=(
            target.program_id
        ),
        target_label=(
            target.label
        ),
        priority_count=len(
            priority_program_ids
        ),
        target_was_priority=(
            target.program_id
            in priority_program_ids
        ),
        certificate_size=len(
            minimal_certificate(
                target.program_id
            )
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
        attempted_priority_ids=tuple(
            scientist.attempted_priority_ids
        ),
        falsified_priority_ids=tuple(
            scientist.falsified_priority_ids
        ),
        goal_reached=(
            lab.state.goal_reached
        ),
        authorization=(
            authorization
        ),
    )
