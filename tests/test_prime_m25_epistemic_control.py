"""PRIME M25 epistemic-control tests."""

import unittest

from core.cognition import (
    MegaPrimeCognition,
)
from core.cognition.causal_certificate import (
    CausalAuthorityLedger,
    minimal_certificate,
)
from core.cognition.causal_ecology import (
    WeightedCausalStudySelector,
    build_causal_mass_field,
)
from core.cognition.causal_program import (
    CausalProgram,
    ProgramOp,
    program_universe,
)

from experiments.prime_m24_causal_program_world.lab import (
    ProgramLab,
)
from experiments.prime_m25_epistemic_control.development import (
    curriculum,
)
from experiments.prime_m25_epistemic_control.episode import (
    run_epistemic_episode,
)


class EcologyTests(
    unittest.TestCase
):
    def test_every_program_keeps_positive_mass(
        self,
    ):
        brain = (
            MegaPrimeCognition()
        )

        field = (
            build_causal_mass_field(
                brain.causal_program_memory
            )
        )

        self.assertTrue(
            all(
                field.mass(
                    program.program_id
                ) > 0
                for program
                in program_universe()
            )
        )

    def test_prior_bonus_cannot_exceed_universal_mass(
        self,
    ):
        brain = (
            MegaPrimeCognition()
        )

        ledger = (
            CausalAuthorityLedger()
        )

        for program in (
            program_universe()[:20]
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

            auth = ledger.authorize(
                program.program_id,
                observations,
            )

            self.assertTrue(
                auth.verdict
            )

            brain.causal_program_memory.ingest(
                auth
            )

        field = (
            build_causal_mass_field(
                brain.causal_program_memory
            )
        )

        self.assertLessEqual(
            field.bonus_mass,
            field.universal_mass,
        )

    def test_verified_exact_memory_gets_extra_mass(
        self,
    ):
        brain = (
            MegaPrimeCognition()
        )

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

        certificate = (
            minimal_certificate(
                target.program_id
            )
        )

        auth = ledger.authorize(
            target.program_id,
            {
                configuration: (
                    target.evaluate(
                        configuration
                    )
                )
                for configuration
                in certificate
            },
        )

        brain.causal_program_memory.ingest(
            auth
        )

        field = (
            build_causal_mass_field(
                brain.causal_program_memory
            )
        )

        self.assertGreater(
            field.mass(
                target.program_id
            ),
            field.base_mass,
        )


class SelectorTests(
    unittest.TestCase
):
    def test_selector_prices_physical_cost(
        self,
    ):
        field = (
            build_causal_mass_field(
                None
            )
        )

        lab = ProgramLab(
            CausalProgram(
                ProgramOp.XOR,
                (
                    0,
                    1,
                ),
            )
        )

        selector = (
            WeightedCausalStudySelector()
        )

        study = selector.choose(
            surviving_program_ids={
                program.program_id
                for program
                in program_universe()
            },
            observations={},
            mass_field=field,
            intervention_cost=(
                lab.cost_to_probe
            ),
        )

        self.assertGreater(
            study.information_product,
            0,
        )

        self.assertGreater(
            study.primitive_cost,
            0,
        )


class AuthorityTests(
    unittest.TestCase
):
    def test_weighted_prior_cannot_change_truth(
        self,
    ):
        target = CausalProgram(
            ProgramOp.XOR,
            (
                0,
                1,
            ),
        )

        brain = (
            MegaPrimeCognition()
        )

        wrong = CausalProgram(
            ProgramOp.AND,
            (
                0,
                1,
            ),
        )

        ledger = (
            CausalAuthorityLedger()
        )

        certificate = (
            minimal_certificate(
                wrong.program_id
            )
        )

        wrong_auth = (
            ledger.authorize(
                wrong.program_id,
                {
                    configuration: (
                        wrong.evaluate(
                            configuration
                        )
                    )
                    for configuration
                    in certificate
                },
            )
        )

        brain.causal_program_memory.ingest(
            wrong_auth
        )

        field = (
            build_causal_mass_field(
                brain.causal_program_memory
            )
        )

        result = (
            run_epistemic_episode(
                target,
                mass_field=field,
            )
        )

        self.assertEqual(
            result.target_program_id,
            target.program_id,
        )

        self.assertTrue(
            result.goal_reached
        )


class CurriculumTests(
    unittest.TestCase
):
    def test_lifetime_has_128_chapters(
        self,
    ):
        rows = curriculum()

        self.assertEqual(
            len(rows),
            128,
        )

        self.assertEqual(
            len(
                {
                    program.program_id
                    for _, program
                    in rows[:24]
                }
            ),
            24,
        )


if __name__ == "__main__":
    unittest.main()
