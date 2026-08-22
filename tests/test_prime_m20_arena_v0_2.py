"""Corrected Arena v0.2 invariants."""

import unittest

from core.construction.grammar import (
    binary,
    lag,
)
from core.construction.quotient import (
    RELATION_COMPLEMENT,
    semantic_relation,
)
from core.construction.types import (
    FeatureOp,
)

from experiments.prime_m20_universal_arena.runner_v0_2 import (
    run_world,
)
from experiments.prime_m20_universal_arena.tasks import (
    TASK_BY_NAME,
)


class PairingTests(
    unittest.TestCase
):
    def test_heldout_still_blocked(self):
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


class QuotientTests(
    unittest.TestCase
):
    def test_xor_eq_relation_frozen(self):
        xor_expr = binary(
            FeatureOp.XOR,
            lag(2),
            lag(7),
        )

        eq_expr = binary(
            FeatureOp.EQ,
            lag(2),
            lag(7),
        )

        self.assertEqual(
            semantic_relation(
                xor_expr,
                eq_expr,
            ),
            RELATION_COMPLEMENT,
        )

    def test_xor27_partition_recovery(self):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "XOR-2-7"
                ]
            ),
            stream_seed=600,
            condition=(
                "M20-CONSTRUCTION"
            ),
        ).payload

        self.assertTrue(
            result[
                "predictive_partition_recovered"
            ]
        )

    def test_eq14_partition_recovery(self):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "EQ-1-4"
                ]
            ),
            stream_seed=601,
            condition=(
                "M20-CONSTRUCTION"
            ),
        ).payload

        self.assertTrue(
            result[
                "predictive_partition_recovered"
            ]
        )


class ImbalanceTests(
    unittest.TestCase
):
    def test_and_task_reports_constant_baseline(self):
        result = run_world(
            task=(
                TASK_BY_NAME[
                    "AND-1-2-4"
                ]
            ),
            stream_seed=602,
            condition="REACTIVE",
        ).payload

        self.assertIsNotNone(
            result[
                "balanced_accuracy_ppm"
            ]
        )

        self.assertGreater(
            result[
                "best_constant_accuracy_ppm"
            ],
            500000,
        )


if __name__ == "__main__":
    unittest.main()
