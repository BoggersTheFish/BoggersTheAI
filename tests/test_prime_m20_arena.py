"""Structural tests for PRIME M20 Universal Arena."""

import unittest

from core.construction.grammar import (
    evaluate,
)
from core.construction.scaffold import (
    generate_scaffold_candidates,
)

from experiments.prime_m20_universal_arena.runner import (
    run_world,
)
from experiments.prime_m20_universal_arena.tasks import (
    TASK_BY_NAME,
)


class ScaffoldTests(
    unittest.TestCase
):
    def test_three_way_xor_exists(self):
        target = TASK_BY_NAME[
            "XOR-1-2-3"
        ].expression

        self.assertIsNotNone(
            target
        )

        candidates = (
            generate_scaffold_candidates(
                max_lag=8,
                max_candidates=256,
            )
        )

        hashes = {
            spec.expression.expression_hash
            for spec in candidates
        }

        self.assertIn(
            target.expression_hash,
            hashes,
        )

    def test_three_way_semantics(self):
        task = TASK_BY_NAME[
            "XOR-1-2-3"
        ]

        history = (
            1,
            0,
            1,
            1,
        )

        self.assertEqual(
            task.target(
                history
            ),
            (
                history[-2]
                ^ history[-3]
                ^ history[-4]
            ),
        )


class GuardTests(
    unittest.TestCase
):
    def test_heldout_blocked(self):
        with self.assertRaises(
            RuntimeError
        ):
            run_world(
                task=(
                    TASK_BY_NAME[
                        "LAG-4"
                    ]
                ),
                stream_seed=6000,
                condition=(
                    "M20-CONSTRUCTION"
                ),
            )

    def test_unknown_seed_blocked(self):
        with self.assertRaises(
            RuntimeError
        ):
            run_world(
                task=(
                    TASK_BY_NAME[
                        "LAG-4"
                    ]
                ),
                stream_seed=999,
                condition=(
                    "M20-CONSTRUCTION"
                ),
            )


class DevelopmentSmokeTests(
    unittest.TestCase
):
    def test_current_does_not_construct(self):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "CURRENT"
                ]
            ),
            stream_seed=600,
            condition=(
                "M20-CONSTRUCTION"
            ),
        ).payload

        self.assertEqual(
            result[
                "authorized_construction_count"
            ],
            0,
        )

        self.assertTrue(
            result[
                "exact_target_construction_active"
            ]
        )

        self.assertTrue(
            result[
                "receipt_chain_valid"
            ]
        )

    def test_lag4_constructs_target(self):
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

        self.assertTrue(
            result[
                "exact_target_construction_active"
            ]
        )

        self.assertTrue(
            result[
                "receipt_chain_valid"
            ]
        )

    def test_xor_pair_constructs_target(self):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "XOR-1-4"
                ]
            ),
            stream_seed=602,
            condition=(
                "M20-CONSTRUCTION"
            ),
        ).payload

        self.assertTrue(
            result[
                "exact_target_construction_active"
            ]
        )

    def test_xor3_scaffold_constructs_target(self):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "XOR-1-2-3"
                ]
            ),
            stream_seed=603,
            condition=(
                "M20-CONSTRUCTION"
            ),
        ).payload

        self.assertTrue(
            result[
                "exact_target_construction_active"
            ]
        )

        self.assertTrue(
            result[
                "receipt_chain_valid"
            ]
        )


if __name__ == "__main__":
    unittest.main()
