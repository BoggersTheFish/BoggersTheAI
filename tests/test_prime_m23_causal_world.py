"""PRIME M23 causal developmental intelligence tests."""

import unittest

from experiments.prime_m23_causal_world.episode import (
    solve_episode,
)
from experiments.prime_m23_causal_world.lab import (
    ALL_LAWS,
    CausalLab,
    DoorLaw,
    evaluate_law,
)
from experiments.prime_m23_causal_world.scientist import (
    CausalScientist,
)


class LawTests(
    unittest.TestCase
):
    def test_truth_tables_are_distinct(
        self,
    ):
        signatures = {
            tuple(
                evaluate_law(
                    law,
                    a,
                    b,
                )
                for a, b in (
                    (0, 0),
                    (0, 1),
                    (1, 0),
                    (1, 1),
                )
            )
            for law
            in ALL_LAWS
        }

        self.assertEqual(
            len(signatures),
            len(ALL_LAWS),
        )


class ScientistTests(
    unittest.TestCase
):
    def test_every_law_can_be_identified(
        self,
    ):
        for law in ALL_LAWS:
            scientist = (
                CausalScientist()
            )

            while (
                scientist.verified_law
                is None
            ):
                config = (
                    scientist.choose_intervention()
                )

                scientist.observe(
                    config,
                    evaluate_law(
                        law,
                        config[0],
                        config[1],
                    ),
                )

            self.assertEqual(
                scientist.verified_law,
                law,
            )

    def test_wrong_prior_is_falsifiable(
        self,
    ):
        result = solve_episode(
            DoorLaw.XOR,
            prior=DoorLaw.AND,
        )

        self.assertEqual(
            result.verified_law,
            DoorLaw.XOR,
        )

        self.assertTrue(
            result.goal_reached
        )


class WorldTests(
    unittest.TestCase
):
    def test_closed_door_blocks_navigation(
        self,
    ):
        lab = CausalLab(
            DoorLaw.AND
        )

        path = lab.shortest_path(
            lab.state.position,
            lab.layout.goal,
        )

        self.assertIsNone(
            path
        )

    def test_verified_causal_knowledge_reaches_goal(
        self,
    ):
        for law in ALL_LAWS:
            result = solve_episode(
                law
            )

            self.assertTrue(
                result.verified
            )

            self.assertEqual(
                result.verified_law,
                law,
            )

            self.assertTrue(
                result.goal_reached
            )

            self.assertLessEqual(
                result.interventions,
                4,
            )


if __name__ == "__main__":
    unittest.main()
