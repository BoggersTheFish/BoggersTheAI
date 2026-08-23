"""128-chapter lifelong causal epistemic-control experiment."""

from __future__ import annotations

import json

from core.cognition import (
    MegaPrimeCognition,
)
from core.cognition.causal_certificate import (
    CausalAuthorityLedger,
)
from core.cognition.causal_ecology import (
    build_causal_mass_field,
)
from core.cognition.causal_program import (
    program_universe,
)

from .episode import (
    run_epistemic_episode,
)


MASK64 = (
    (1 << 64)
    - 1
)


def splitmix64(
    value: int,
) -> int:
    z = (
        value
        + 0x9E3779B97F4A7C15
    ) & MASK64

    z = (
        (
            z
            ^ (z >> 30)
        )
        * 0xBF58476D1CE4E5B9
    ) & MASK64

    z = (
        (
            z
            ^ (z >> 27)
        )
        * 0x94D049BB133111EB
    ) & MASK64

    return (
        z
        ^ (z >> 31)
    ) & MASK64


def curriculum():
    universe = list(
        program_universe()
    )

    # Deterministic permutation.
    universe.sort(
        key=lambda program: (
            splitmix64(
                int(
                    program.program_id[
                        3:19
                    ],
                    16,
                )
                ^ 0x4D32354341555345
            )
        )
    )

    rows = []

    # Phase 1:
    # broad but incomplete foundation.
    for index in range(24):
        rows.append(
            (
                "foundation",
                universe[index],
            )
        )

    # Phase 2:
    # alternate old and previously unseen structure.
    unseen = (
        universe[
            24:
        ]
    )

    for index in range(40):
        if index % 2 == 0:
            selector = (
                splitmix64(
                    0x4D32355048415345
                    ^ index
                )
                % 24
            )

            program = (
                universe[
                    selector
                ]
            )

            phase = (
                "reuse-and-transfer"
            )

        else:
            selector = (
                (index // 2)
                % len(
                    unseen
                )
            )

            program = (
                unseen[
                    selector
                ]
            )

            phase = (
                "novel-after-development"
            )

        rows.append(
            (
                phase,
                program,
            )
        )

    # Phase 3:
    # mature mixed lifetime.
    for index in range(64):
        selector = (
            splitmix64(
                0x4D32354D41545552
                ^ index
            )
            % len(
                universe
            )
        )

        rows.append(
            (
                "mature-mixed",
                universe[
                    selector
                ],
            )
        )

    if len(rows) != 128:
        raise RuntimeError(
            "M25 curriculum size changed"
        )

    return tuple(
        rows
    )


def mean(
    values,
):
    values = list(
        values
    )

    if not values:
        return None

    return (
        sum(values)
        / len(values)
    )


def main():
    brain = (
        MegaPrimeCognition()
    )

    cold_authority = (
        CausalAuthorityLedger()
    )

    persistent_authority = (
        CausalAuthorityLedger()
    )

    cold_field = (
        build_causal_mass_field(
            None
        )
    )

    rows = []

    seen = set()

    for index, (
        phase,
        target,
    ) in enumerate(
        curriculum()
    ):
        cold = (
            run_epistemic_episode(
                target,
                mass_field=(
                    cold_field
                ),
                authority_ledger=(
                    cold_authority
                ),
            )
        )

        memory = (
            brain.causal_program_memory
        )

        exact_seen = (
            target.program_id
            in memory.entries
        )

        persistent_field = (
            build_causal_mass_field(
                memory
            )
        )

        target_schema_biased = (
            not exact_seen
            and persistent_field.mass(
                target.program_id
            )
            > persistent_field.base_mass
        )

        persistent = (
            run_epistemic_episode(
                target,
                mass_field=(
                    persistent_field
                ),
                authority_ledger=(
                    persistent_authority
                ),
            )
        )

        intervention_gain = (
            cold.interventions
            - persistent.interventions
        )

        step_gain = (
            cold.total_steps
            - persistent.total_steps
        )

        # Meta-memory feedback applies only to exact reuse.
        if exact_seen:
            if intervention_gain > 0:
                memory.record_reuse(
                    target.program_id,
                    success=True,
                )

            elif intervention_gain < 0:
                memory.record_reuse(
                    target.program_id,
                    success=False,
                )

        memory.ingest(
            persistent.authorization
        )

        seen.add(
            target.program_id
        )

        brain.episodic_memory.append(
            context_id=(
                "m25-"
                + str(index)
            ),
            context_tokens=(
                "m25-lifelong-causal-world",
                phase,
            ),
            verified_construction_ids=(
                target.program_id,
            ),
            reward_ppm=max(
                0,
                (
                    1_000_000
                    - 5_000
                    * persistent.total_steps
                ),
            ),
            studies=tuple(
                str(
                    row[
                        "configuration"
                    ]
                )
                for row
                in persistent.study_trace
            ),
        )

        rows.append(
            {
                "index": index,
                "phase": phase,
                "target": (
                    target.label
                ),
                "exact_seen_before": (
                    exact_seen
                ),
                "schema_biased_novel": (
                    target_schema_biased
                ),
                "cold_interventions": (
                    cold.interventions
                ),
                "persistent_interventions": (
                    persistent.interventions
                ),
                "intervention_gain": (
                    intervention_gain
                ),
                "cold_steps": (
                    cold.total_steps
                ),
                "persistent_steps": (
                    persistent.total_steps
                ),
                "step_gain": (
                    step_gain
                ),
                "target_prior_mass": (
                    persistent.target_initial_mass
                ),
                "target_prior_rank": (
                    persistent.target_initial_rank
                ),
                "prior_bonus_mass": (
                    persistent.prior_bonus_mass
                ),
                "cold_goal": (
                    cold.goal_reached
                ),
                "persistent_goal": (
                    persistent.goal_reached
                ),
            }
        )

    phases = {}

    for phase in sorted(
        {
            row["phase"]
            for row in rows
        }
    ):
        subset = [
            row
            for row in rows
            if row[
                "phase"
            ] == phase
        ]

        phases[
            phase
        ] = {
            "count": len(
                subset
            ),
            "mean_intervention_gain": mean(
                row[
                    "intervention_gain"
                ]
                for row in subset
            ),
            "mean_step_gain": mean(
                row[
                    "step_gain"
                ]
                for row in subset
            ),
            "positive": sum(
                row[
                    "intervention_gain"
                ] > 0
                for row in subset
            ),
            "ties": sum(
                row[
                    "intervention_gain"
                ] == 0
                for row in subset
            ),
            "negative": sum(
                row[
                    "intervention_gain"
                ] < 0
                for row in subset
            ),
        }

    thirds = []

    for start in (
        0,
        42,
        85,
    ):
        end = (
            42
            if start == 0
            else (
                85
                if start == 42
                else 128
            )
        )

        subset = (
            rows[
                start:end
            ]
        )

        thirds.append(
            {
                "start": start,
                "end": end,
                "mean_intervention_gain": mean(
                    row[
                        "intervention_gain"
                    ]
                    for row in subset
                ),
                "mean_step_gain": mean(
                    row[
                        "step_gain"
                    ]
                    for row in subset
                ),
            }
        )

    report = {
        "experiment": (
            "prime-m25-lifelong-epistemic-control"
        ),
        "status": (
            "DEVELOPMENT_ONLY"
        ),
        "chapter_count": len(
            rows
        ),
        "cold_goal_count": sum(
            row[
                "cold_goal"
            ]
            for row in rows
        ),
        "persistent_goal_count": sum(
            row[
                "persistent_goal"
            ]
            for row in rows
        ),
        "mean_intervention_gain": mean(
            row[
                "intervention_gain"
            ]
            for row in rows
        ),
        "mean_step_gain": mean(
            row[
                "step_gain"
            ]
            for row in rows
        ),
        "positive": sum(
            row[
                "intervention_gain"
            ] > 0
            for row in rows
        ),
        "ties": sum(
            row[
                "intervention_gain"
            ] == 0
            for row in rows
        ),
        "negative": sum(
            row[
                "intervention_gain"
            ] < 0
            for row in rows
        ),
        "exact_reuse_chapters": sum(
            row[
                "exact_seen_before"
            ]
            for row in rows
        ),
        "schema_biased_novel_chapters": sum(
            row[
                "schema_biased_novel"
            ]
            for row in rows
        ),
        "causal_memory_size": len(
            brain.causal_program_memory.entries
        ),
        "causal_schema_count": len(
            brain.causal_program_memory.schemas()
        ),
        "cold_authority_chain_valid": (
            cold_authority.verify_chain()
        ),
        "persistent_authority_chain_valid": (
            persistent_authority.verify_chain()
        ),
        "episodic_chain_valid": (
            brain.episodic_memory.verify_chain()
        ),
        "phase_summaries": (
            phases
        ),
        "developmental_thirds": (
            thirds
        ),
        "rows": (
            rows
        ),
    }

    print(
        json.dumps(
            report,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
