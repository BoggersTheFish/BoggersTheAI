"""Persistent causal-program development for PRIME M24."""

from __future__ import annotations

from dataclasses import dataclass
import json

from core.cognition import (
    MegaPrimeCognition,
)
from core.cognition.causal_certificate import (
    CausalAuthorityLedger,
)
from core.cognition.causal_program import (
    CausalProgram,
    ProgramOp,
)

from .episode import (
    run_program_episode,
)


@dataclass(frozen=True)
class CausalChapter:
    chapter_id: str
    role: str
    program: CausalProgram


def P(
    op,
    *variables,
):
    return CausalProgram(
        op,
        tuple(
            variables
        ),
    )


def curriculum():
    return (
        CausalChapter(
            "C00-A",
            "novel",
            P(
                ProgramOp.VAR,
                0,
            ),
        ),
        CausalChapter(
            "C01-XOR-AB",
            "novel",
            P(
                ProgramOp.XOR,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C02-AND-AB",
            "novel",
            P(
                ProgramOp.AND,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C03-OR-AB",
            "novel",
            P(
                ProgramOp.OR,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C04-NOT-A",
            "novel",
            P(
                ProgramOp.NOT,
                0,
            ),
        ),

        CausalChapter(
            "C05-XOR-AB-repeat",
            "repeat",
            P(
                ProgramOp.XOR,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C06-XOR-BC",
            "family-learning",
            P(
                ProgramOp.XOR,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C07-XOR-CD",
            "schema-transfer",
            P(
                ProgramOp.XOR,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C08-AND-AB-repeat",
            "repeat",
            P(
                ProgramOp.AND,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C09-AND-BC",
            "family-learning",
            P(
                ProgramOp.AND,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C10-AND-CD",
            "schema-transfer",
            P(
                ProgramOp.AND,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C11-OR-AB-repeat",
            "repeat",
            P(
                ProgramOp.OR,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C12-OR-BC",
            "family-learning",
            P(
                ProgramOp.OR,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C13-OR-CD",
            "schema-transfer",
            P(
                ProgramOp.OR,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C14-EQ-AB",
            "novel",
            P(
                ProgramOp.EQ,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C15-EQ-BC",
            "family-learning",
            P(
                ProgramOp.EQ,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C16-EQ-CD",
            "schema-transfer",
            P(
                ProgramOp.EQ,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C17-XOR-ABC",
            "novel",
            P(
                ProgramOp.XOR,
                0,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C18-XOR-BCD",
            "schema-transfer",
            P(
                ProgramOp.XOR,
                1,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C19-AND-ABC",
            "novel",
            P(
                ProgramOp.AND,
                0,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C20-AND-BCD",
            "schema-transfer",
            P(
                ProgramOp.AND,
                1,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C21-OR-ABC",
            "novel",
            P(
                ProgramOp.OR,
                0,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C22-OR-BCD",
            "schema-transfer",
            P(
                ProgramOp.OR,
                1,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C23-XOR-ABCD",
            "higher-order",
            P(
                ProgramOp.XOR,
                0,
                1,
                2,
                3,
            ),
        ),
        CausalChapter(
            "C24-AND-ABCD",
            "higher-order",
            P(
                ProgramOp.AND,
                0,
                1,
                2,
                3,
            ),
        ),
        CausalChapter(
            "C25-OR-ABCD",
            "higher-order",
            P(
                ProgramOp.OR,
                0,
                1,
                2,
                3,
            ),
        ),

        CausalChapter(
            "C26-NOT-B",
            "novel",
            P(
                ProgramOp.NOT,
                1,
            ),
        ),
        CausalChapter(
            "C27-NOT-C",
            "novel",
            P(
                ProgramOp.NOT,
                2,
            ),
        ),
        CausalChapter(
            "C28-NOT-D",
            "novel",
            P(
                ProgramOp.NOT,
                3,
            ),
        ),

        CausalChapter(
            "C29-XOR-AB-return",
            "long-return",
            P(
                ProgramOp.XOR,
                0,
                1,
            ),
        ),
        CausalChapter(
            "C30-AND-ABC-return",
            "long-return",
            P(
                ProgramOp.AND,
                0,
                1,
                2,
            ),
        ),
        CausalChapter(
            "C31-OR-BCD-return",
            "long-return",
            P(
                ProgramOp.OR,
                1,
                2,
                3,
            ),
        ),
    )


def main():
    brain = (
        MegaPrimeCognition()
    )

    cold_ledger = (
        CausalAuthorityLedger()
    )

    persistent_ledger = (
        CausalAuthorityLedger()
    )

    rows = []

    for chapter in curriculum():
        cold = run_program_episode(
            chapter.program,
            priority_program_ids=(),
            authority_ledger=(
                cold_ledger
            ),
        )

        memory = (
            brain.causal_program_memory
        )

        seen_before = (
            chapter.program.program_id
            in memory.entries
        )

        priorities = (
            memory.priority_program_ids(
                limit=8
            )
        )

        persistent = (
            run_program_episode(
                chapter.program,
                priority_program_ids=(
                    priorities
                ),
                authority_ledger=(
                    persistent_ledger
                ),
            )
        )

        target_prior = (
            chapter.program.program_id
            in priorities
        )

        for program_id in (
            persistent.falsified_priority_ids
        ):
            memory.record_reuse(
                program_id,
                success=False,
            )

        memory.ingest(
            persistent.authorization
        )

        if target_prior:
            memory.record_reuse(
                chapter.program.program_id,
                success=True,
            )

        brain.episodic_memory.append(
            context_id=(
                chapter.chapter_id
            ),
            context_tokens=(
                "m24-causal-program-world",
                chapter.role,
            ),
            verified_construction_ids=(
                chapter.program.program_id,
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
                str(configuration)
                for configuration
                in ()
            ),
        )

        rows.append(
            {
                "chapter_id": (
                    chapter.chapter_id
                ),
                "role": (
                    chapter.role
                ),
                "target": (
                    chapter.program.label
                ),
                "cold_interventions": (
                    cold.interventions
                ),
                "persistent_interventions": (
                    persistent.interventions
                ),
                "intervention_gain": (
                    cold.interventions
                    - persistent.interventions
                ),
                "cold_total_steps": (
                    cold.total_steps
                ),
                "persistent_total_steps": (
                    persistent.total_steps
                ),
                "step_gain": (
                    cold.total_steps
                    - persistent.total_steps
                ),
                "certificate_size": (
                    persistent.certificate_size
                ),
                "priority_count": (
                    len(priorities)
                ),
                "target_in_priority": (
                    target_prior
                ),
                "exact_memory_hit": (
                    target_prior
                    and seen_before
                ),
                "schema_or_generalized_hit": (
                    target_prior
                    and not seen_before
                ),
                "attempted_priority_count": len(
                    persistent.attempted_priority_ids
                ),
                "falsified_priority_count": len(
                    persistent.falsified_priority_ids
                ),
                "cold_goal": (
                    cold.goal_reached
                ),
                "persistent_goal": (
                    persistent.goal_reached
                ),
            }
        )

    report = {
        "experiment": (
            "prime-m24-causal-program-development"
        ),
        "status": (
            "DEVELOPMENT_ONLY"
        ),
        "chapter_count": (
            len(rows)
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
        "mean_intervention_gain": (
            sum(
                row[
                    "intervention_gain"
                ]
                for row in rows
            )
            / len(rows)
        ),
        "mean_step_gain": (
            sum(
                row[
                    "step_gain"
                ]
                for row in rows
            )
            / len(rows)
        ),
        "positive_intervention_transfer": sum(
            row[
                "intervention_gain"
            ] > 0
            for row in rows
        ),
        "tied_intervention_transfer": sum(
            row[
                "intervention_gain"
            ] == 0
            for row in rows
        ),
        "negative_intervention_transfer": sum(
            row[
                "intervention_gain"
            ] < 0
            for row in rows
        ),
        "exact_memory_hits": sum(
            row[
                "exact_memory_hit"
            ]
            for row in rows
        ),
        "schema_or_generalized_hits": sum(
            row[
                "schema_or_generalized_hit"
            ]
            for row in rows
        ),
        "causal_memory_size": len(
            brain.causal_program_memory.entries
        ),
        "causal_schema_count": len(
            brain.causal_program_memory.schemas()
        ),
        "causal_schemas": [
            {
                "operator": (
                    schema.operator.value
                ),
                "offsets": list(
                    schema.normalized_offsets
                ),
                "support": (
                    schema.support
                ),
            }
            for schema
            in brain.causal_program_memory.schemas()
        ],
        "cold_authority_chain_valid": (
            cold_ledger.verify_chain()
        ),
        "persistent_authority_chain_valid": (
            persistent_ledger.verify_chain()
        ),
        "episodic_chain_valid": (
            brain.episodic_memory.verify_chain()
        ),
        "rows": rows,
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
