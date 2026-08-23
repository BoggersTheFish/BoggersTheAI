"""PRIME M24 causal program induction tests."""

import unittest

from core.cognition import (
    MegaPrimeCognition,
)
from core.cognition.causal_certificate import (
    CausalAuthorityLedger,
    compatible_program_ids,
    minimal_certificate,
)
from core.cognition.causal_program import (
    CausalProgram,
    ProgramOp,
    program_universe,
)

from experiments.prime_m24_causal_program_world.episode import (
    run_program_episode,
)


class ProgramUniverseTests(
    unittest.TestCase
):
    def test_universe_has_47_distinct_programs(
        self,
    ):
        universe = (
            program_universe()
        )

        self.assertEqual(
            len(universe),
            47,
        )

        self.assertEqual(
            len(
                {
                    program.signature
                    for program
                    in universe
                }
            ),
            47,
        )


class CertificateTests(
    unittest.TestCase
):
    def test_certificate_uniquely_identifies_program(
        self,
    ):
        target = CausalProgram(
            ProgramOp.XOR,
            (
                0,
                1,
            ),
        )

        certificate = (
            minimal_certificate(
                target.program_id
            )
        )

        observations = {
            configuration: (
                target.evaluate(
                    configuration
                )
            )
            for configuration
            in certificate
        }

        self.assertEqual(
            compatible_program_ids(
                observations
            ),
            (
                target.program_id,
            ),
        )

        self.assertLessEqual(
            len(certificate),
            5,
        )

    def test_authority_rejects_insufficient_evidence(
        self,
    ):
        target = CausalProgram(
            ProgramOp.XOR,
            (
                0,
                1,
            ),
        )

        ledger = (
            CausalAuthorityLedger()
        )

        auth = ledger.authorize(
            target.program_id,
            {
                (0, 0, 0, 0): 0,
            },
        )

        self.assertFalse(
            auth.verdict
        )

        self.assertTrue(
            ledger.verify_chain()
        )


class DevelopmentalTransferTests(
    unittest.TestCase
):
    def test_correct_prior_reduces_xor_experiment_count(
        self,
    ):
        target = CausalProgram(
            ProgramOp.XOR,
            (
                0,
                1,
            ),
        )

        cold = (
            run_program_episode(
                target
            )
        )

        primed = (
            run_program_episode(
                target,
                priority_program_ids=(
                    target.program_id,
                ),
            )
        )

        self.assertLess(
            primed.interventions,
            cold.interventions,
        )

        self.assertTrue(
            primed.authorization.verdict
        )

        self.assertTrue(
            primed.goal_reached
        )

    def test_wrong_prior_cannot_authorize(
        self,
    ):
        target = CausalProgram(
            ProgramOp.XOR,
            (
                0,
                1,
            ),
        )

        wrong = CausalProgram(
            ProgramOp.AND,
            (
                0,
                1,
            ),
        )

        result = (
            run_program_episode(
                target,
                priority_program_ids=(
                    wrong.program_id,
                ),
            )
        )

        self.assertEqual(
            result.authorization.program_id,
            target.program_id,
        )

        self.assertTrue(
            result.authorization.verdict
        )

        self.assertIn(
            wrong.program_id,
            result.falsified_priority_ids,
        )


class CausalSchemaTests(
    unittest.TestCase
):
    def test_shifted_causal_schema_proposes_unseen_program(
        self,
    ):
        brain = (
            MegaPrimeCognition()
        )

        ledger = (
            CausalAuthorityLedger()
        )

        first = CausalProgram(
            ProgramOp.XOR,
            (
                0,
                1,
            ),
        )

        second = CausalProgram(
            ProgramOp.XOR,
            (
                1,
                2,
            ),
        )

        for program in (
            first,
            second,
        ):
            certificate = (
                minimal_certificate(
                    program.program_id
                )
            )

            observations = {
                configuration: (
                    program.evaluate(
                        configuration
                    )
                )
                for configuration
                in certificate
            }

            authorization = (
                ledger.authorize(
                    program.program_id,
                    observations,
                )
            )

            self.assertTrue(
                authorization.verdict
            )

            brain.causal_program_memory.ingest(
                authorization
            )

        unseen = (
            CausalProgram(
                ProgramOp.XOR,
                (
                    2,
                    3,
                ),
            )
        )

        priorities = (
            brain.causal_program_memory.priority_program_ids(
                limit=16
            )
        )

        self.assertIn(
            unseen.program_id,
            priorities,
        )


if __name__ == "__main__":
    unittest.main()
