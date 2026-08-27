"""Frozen evaluation-apparatus tests without held-out execution."""

import unittest

from experiments.prime_m20_universal_arena.run_evaluation_v0_3 import (
    BOOTSTRAP_REPLICATES,
    LOWER_INDEX,
    UPPER_INDEX,
    cluster_bootstrap,
)
from experiments.prime_m20_universal_arena.runner_v0_3 import (
    EVALUATION_SEEDS,
)
from experiments.prime_m20_universal_arena.tasks import (
    TASKS,
)


class ClusterBootstrapTests(
    unittest.TestCase
):
    def test_contract_constants(
        self,
    ):
        self.assertEqual(
            BOOTSTRAP_REPLICATES,
            16384,
        )

        self.assertEqual(
            LOWER_INDEX,
            409,
        )

        self.assertEqual(
            UPPER_INDEX,
            15974,
        )

        self.assertEqual(
            len(EVALUATION_SEEDS),
            32,
        )

        self.assertEqual(
            len(TASKS),
            12,
        )

    def test_constant_positive_effect(
        self,
    ):
        rows = [
            {
                "seed": seed,
                "task": task.name,
                "delta": 100,
            }
            for seed
            in EVALUATION_SEEDS
            for task
            in TASKS
        ]

        result = (
            cluster_bootstrap(
                rows
            )
        )

        self.assertEqual(
            result[
                "lower_ppm"
            ],
            100,
        )

        self.assertEqual(
            result[
                "upper_ppm"
            ],
            100,
        )

    def test_cluster_structure_required(
        self,
    ):
        rows = [
            {
                "seed": seed,
                "task": task.name,
                "delta": 1,
            }
            for seed
            in EVALUATION_SEEDS
            for task
            in TASKS
        ]

        rows.pop()

        with self.assertRaises(
            RuntimeError
        ):
            cluster_bootstrap(
                rows
            )


if __name__ == "__main__":
    unittest.main()
