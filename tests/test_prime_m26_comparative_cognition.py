"""PRIME M26 comparative cognition tests."""

import unittest

from experiments.prime_m26_comparative_cognition.gru_agent import (
    GRUOnlinePredictor,
)
from experiments.prime_m26_comparative_cognition.runner import (
    EVALUATION_SEEDS,
    run_world,
)
from experiments.prime_m26_comparative_cognition.tasks import (
    tasks,
)


class TaskTests(
    unittest.TestCase
):
    def test_task_families_present(
        self,
    ):
        rows = tasks()

        self.assertEqual(
            len(rows),
            18,
        )

        families = {
            row.family
            for row in rows
        }

        self.assertEqual(
            families,
            {
                "explicit-relational",
                "scaling",
                "recurrent-state",
                "nonstationary",
            },
        )


class GRUTests(
    unittest.TestCase
):
    def test_gru_has_recurrent_parameters(
        self,
    ):
        gru = (
            GRUOnlinePredictor(
                seed=123,
            )
        )

        self.assertGreater(
            gru.parameter_count,
            1000,
        )

        prediction = (
            gru.predict(1)
        )

        self.assertIn(
            prediction,
            (0, 1),
        )

        gru.learn(1)


class GuardTests(
    unittest.TestCase
):
    def test_heldout_blocked(
        self,
    ):
        with self.assertRaises(
            PermissionError
        ):
            run_world(
                tasks()[0],
                EVALUATION_SEEDS[0],
                "GRU32",
            )


class SmokeTests(
    unittest.TestCase
):
    def test_gru_development_world_runs(
        self,
    ):
        result = run_world(
            tasks()[1],
            26000,
            "GRU32",
        ).payload

        self.assertEqual(
            result["condition"],
            "GRU32",
        )

        self.assertGreater(
            result[
                "gru_parameter_count"
            ],
            1000,
        )

    def test_prime_development_world_runs(
        self,
    ):
        result = run_world(
            tasks()[1],
            26000,
            "PRIME",
        ).payload

        self.assertEqual(
            result["condition"],
            "PRIME",
        )

        self.assertTrue(
            result[
                "prime_receipts_valid"
            ]
        )


if __name__ == "__main__":
    unittest.main()
