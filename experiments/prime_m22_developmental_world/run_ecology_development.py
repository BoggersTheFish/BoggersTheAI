"""PRIME M22 developmental accumulation experiment."""

from __future__ import annotations

import json

from .runner_ecological import (
    run_curriculum,
)


def mean_floor(
    values,
):
    values = list(
        values
    )

    if not values:
        return None

    return (
        sum(values)
        // len(values)
    )


def main() -> None:
    cold, _ = run_curriculum(
        persistent=False
    )

    persistent, brain = (
        run_curriculum(
            persistent=True
        )
    )

    assert brain is not None

    cold_by_id = {
        row["chapter_id"]: row
        for row in cold
    }

    persistent_by_id = {
        row["chapter_id"]: row
        for row in persistent
    }

    if (
        set(cold_by_id)
        != set(persistent_by_id)
    ):
        raise RuntimeError(
            "cold/persistent curriculum mismatch"
        )

    comparisons = []

    for chapter_id in cold_by_id:
        c = cold_by_id[
            chapter_id
        ]

        p = persistent_by_id[
            chapter_id
        ]

        cold_event = c[
            "first_recovery_event"
        ]

        persistent_event = p[
            "first_recovery_event"
        ]

        transfer_gain = None

        if (
            cold_event is not None
            and persistent_event
            is not None
        ):
            transfer_gain = (
                cold_event
                - persistent_event
            )

        comparisons.append(
            {
                "chapter_id": (
                    chapter_id
                ),
                "developmental_role": (
                    c[
                        "developmental_role"
                    ]
                ),
                "cold_recovered": (
                    c["recovered"]
                ),
                "persistent_recovered": (
                    p["recovered"]
                ),
                "cold_recovery_event": (
                    cold_event
                ),
                "persistent_recovery_event": (
                    persistent_event
                ),
                "transfer_gain_events": (
                    transfer_gain
                ),
                "cold_aulc_ppm": (
                    c["aulc_ppm"]
                ),
                "persistent_aulc_ppm": (
                    p["aulc_ppm"]
                ),
                "aulc_gain_ppm": (
                    p["aulc_ppm"]
                    - c["aulc_ppm"]
                ),
                "cold_candidates": (
                    c[
                        "initial_candidate_count"
                    ]
                ),
                "persistent_candidates": (
                    p[
                        "initial_candidate_count"
                    ]
                ),
                "persistent_primed": (
                    p["primed"]
                ),
                "persistent_priority_candidates": (
                    p[
                        "priority_candidate_count"
                    ]
                ),
                "persistent_accepted_priority": (
                    p[
                        "accepted_priority_count"
                    ]
                ),
            }
        )

    comparable = [
        row
        for row in comparisons
        if row[
            "transfer_gain_events"
        ]
        is not None
    ]

    primed = [
        row
        for row in comparisons
        if row[
            "persistent_primed"
        ]
    ]

    by_role = {}

    roles = sorted(
        {
            row[
                "developmental_role"
            ]
            for row
            in comparisons
        }
    )

    for role in roles:
        subset = [
            row
            for row in comparisons
            if row[
                "developmental_role"
            ] == role
        ]

        gains = [
            row[
                "transfer_gain_events"
            ]
            for row in subset
            if row[
                "transfer_gain_events"
            ]
            is not None
        ]

        by_role[
            role
        ] = {
            "chapter_count": (
                len(subset)
            ),
            "mean_transfer_gain_events": (
                mean_floor(
                    gains
                )
            ),
            "positive_transfer": sum(
                gain > 0
                for gain in gains
            ),
            "ties": sum(
                gain == 0
                for gain in gains
            ),
            "negative_transfer": sum(
                gain < 0
                for gain in gains
            ),
            "mean_aulc_gain_ppm": (
                mean_floor(
                    row[
                        "aulc_gain_ppm"
                    ]
                    for row
                    in subset
                )
            ),
        }

    schemas = (
        brain.mine_schemas()
    )

    report = {
        "experiment": (
            "prime-m22-cognitive-search-ecology"
        ),
        "status": (
            "DEVELOPMENT_ONLY"
        ),
        "chapter_count": (
            len(comparisons)
        ),
        "cold_recovery_count": sum(
            row[
                "cold_recovered"
            ]
            for row
            in comparisons
        ),
        "persistent_recovery_count": sum(
            row[
                "persistent_recovered"
            ]
            for row
            in comparisons
        ),
        "comparable_recovery_count": (
            len(comparable)
        ),
        "mean_transfer_gain_events": (
            mean_floor(
                row[
                    "transfer_gain_events"
                ]
                for row
                in comparable
            )
        ),
        "positive_transfer_chapters": sum(
            row[
                "transfer_gain_events"
            ] > 0
            for row
            in comparable
        ),
        "tied_transfer_chapters": sum(
            row[
                "transfer_gain_events"
            ] == 0
            for row
            in comparable
        ),
        "negative_transfer_chapters": sum(
            row[
                "transfer_gain_events"
            ] < 0
            for row
            in comparable
        ),
        "mean_aulc_gain_ppm": (
            mean_floor(
                row[
                    "aulc_gain_ppm"
                ]
                for row
                in comparisons
            )
        ),
        "primed_chapter_count": (
            len(primed)
        ),
        "semantic_memory_classes": (
            len(
                brain.semantic_memory.entries
            )
        ),
        "episodic_memory_count": (
            len(
                brain.episodic_memory.records
            )
        ),
        "episode_chain_valid": (
            brain.episodic_memory.verify_chain()
        ),
        "schema_count": (
            len(schemas)
        ),
        "schemas": [
            {
                "schema_id": (
                    schema.schema_id
                ),
                "operator": (
                    schema.operator
                ),
                "normalized_offsets": list(
                    schema.normalized_offsets
                ),
                "support": (
                    schema.support
                ),
            }
            for schema in schemas
        ],
        "meta_sources": {
            source: {
                "attempts": stats.attempts,
                "accepted": stats.accepted,
                "rejected": stats.rejected,
                "cumulative_gain_ppm": (
                    stats.cumulative_gain_ppm
                ),
                "priority": stats.priority,
            }
            for source, stats
            in sorted(
                brain.meta_memory.sources.items()
            )
        },
        "by_role": (
            by_role
        ),
        "comparisons": (
            comparisons
        ),
        "cold_rows": (
            cold
        ),
        "persistent_rows": (
            persistent
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
