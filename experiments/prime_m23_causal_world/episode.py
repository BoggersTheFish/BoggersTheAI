"""End-to-end causal discovery and planning episode."""

from __future__ import annotations

from dataclasses import dataclass

from .lab import (
    CONFIGURATIONS,
    CausalLab,
    DoorLaw,
    evaluate_law,
)
from .scientist import (
    CausalScientist,
)


@dataclass(frozen=True)
class EpisodeResult:
    law: DoorLaw
    prior: DoorLaw | None
    prior_correct: bool | None
    verified: bool
    interventions: int
    discovery_steps: int
    total_steps: int
    goal_reached: bool
    verified_law: DoorLaw | None


def solve_episode(
    law: DoorLaw,
    *,
    prior: DoorLaw | None = None,
) -> EpisodeResult:
    lab = CausalLab(
        law
    )

    scientist = (
        CausalScientist(
            prior=prior
        )
    )

    while (
        scientist.verified_law
        is None
    ):
        configuration = (
            scientist.choose_intervention()
        )

        outcome = (
            lab.perform_intervention(
                configuration
            )
        )

        scientist.observe(
            configuration,
            outcome,
        )

    verified_law = (
        scientist.verified_law
    )

    assert verified_law is not None

    discovery_steps = (
        lab.state.steps
    )

    opening = [
        configuration
        for configuration
        in CONFIGURATIONS
        if evaluate_law(
            verified_law,
            configuration[0],
            configuration[1],
        )
        == 1
    ]

    if not opening:
        raise RuntimeError(
            "verified law has no opening state"
        )

    # Choose cheapest reachable opening configuration.
    opening.sort()

    lab.set_configuration(
        opening[0]
    )

    lab.walk_to(
        lab.layout.goal
    )

    return EpisodeResult(
        law=law,
        prior=prior,
        prior_correct=(
            None
            if prior is None
            else (
                prior
                == law
            )
        ),
        verified=True,
        interventions=len(
            scientist.observations
        ),
        discovery_steps=(
            discovery_steps
        ),
        total_steps=(
            lab.state.steps
        ),
        goal_reached=(
            lab.state.goal_reached
        ),
        verified_law=(
            verified_law
        ),
    )
