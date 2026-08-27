"""Arena v0.3 global-alpha invariants."""

import unittest

from core.construction.compositional_engine import (
    CompositionalAdaptiveConstructionEngine,
)

from experiments.prime_m20_universal_arena.runner_v0_3 import (
    run_world,
)
from experiments.prime_m20_universal_arena.tasks import (
    TASK_BY_NAME,
)


class GlobalAlphaArenaTests(
    unittest.TestCase
):
    def test_initial_arena_field_uses_epoch_spending(
        self,
    ):
        engine = (
            CompositionalAdaptiveConstructionEngine(
                max_lag=8,
                max_candidates=256,
                enable_scaffolds=True,
            )
        )

        snapshot = (
            engine.candidate_field_snapshot()
        )

        self.assertEqual(
            snapshot.epoch,
            0,
        )

        self.assertEqual(
            snapshot.alpha_denominator,
            128,
        )

        self.assertEqual(
            snapshot.threshold,
            (
                128
                * snapshot.candidate_count
            ),
        )

    def test_runner_identifies_v03(
        self,
    ):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "CURRENT"
                ]
            ),
            stream_seed=600,
            condition="REACTIVE",
        ).payload

        self.assertEqual(
            result[
                "arena_version"
            ],
            "v0.3",
        )

        self.assertTrue(
            result[
                "global_alpha_spending"
            ]
        )

    def test_m20_reports_alpha_state(
        self,
    ):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "LAG-4"
                ]
            ),
            stream_seed=601,
            condition=(
                "M20-CONSTRUCTION"
            ),
        ).payload

        field = result[
            "candidate_field"
        ]

        self.assertIsNotNone(
            field
        )

        self.assertGreaterEqual(
            field[
                "alpha_denominator"
            ],
            128,
        )

        self.assertTrue(
            result[
                "receipt_chain_valid"
            ]
        )

    def test_heldout_remains_blocked(
        self,
    ):
        with self.assertRaises(
            RuntimeError
        ):
            run_world(
                task=(
                    TASK_BY_NAME[
                        "XOR-1-2-3"
                    ]
                ),
                stream_seed=6000,
                condition=(
                    "M20-CONSTRUCTION"
                ),
            )


if __name__ == "__main__":
    unittest.main()
