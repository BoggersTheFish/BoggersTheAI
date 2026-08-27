"""PRIME M22 weighted hypothesis ecology tests."""

from fractions import Fraction
import unittest

from core.cognition.hypothesis_ecology import (
    WeightedEvidenceEpoch,
    allocate_hypothesis_mass,
)
from core.construction.evidence import (
    global_epoch_alpha_denominator,
)
from core.construction.grammar import (
    binary,
    generate_bounded_candidates,
    lag,
)
from core.construction.types import (
    ConstructionSpec,
    FeatureOp,
)

from experiments.prime_m22_developmental_world.ecological_engine import (
    EcologicalConstructionEngine,
)


class AllocationTests(
    unittest.TestCase
):
    def setUp(self):
        self.candidates = tuple(
            generate_bounded_candidates(
                max_lag=4,
                max_candidates=32,
            )
        )

    def test_equal_mass_reproduces_uniform_threshold(
        self,
    ):
        allocation = (
            allocate_hypothesis_mass(
                self.candidates,
                priority_ids=(),
            )
        )

        epoch = WeightedEvidenceEpoch(
            self.candidates,
            epoch_index=0,
            allocation=allocation,
        )

        expected = (
            global_epoch_alpha_denominator(
                0
            )
            * len(
                self.candidates
            )
        )

        self.assertTrue(
            all(
                threshold
                == expected
                for threshold
                in epoch.thresholds.values()
            )
        )

    def test_priority_gets_more_alpha_budget(
        self,
    ):
        priority = (
            self.candidates[
                0
            ].construction_id
        )

        allocation = (
            allocate_hypothesis_mass(
                self.candidates,
                priority_ids=(
                    priority,
                ),
            )
        )

        epoch = WeightedEvidenceEpoch(
            self.candidates,
            epoch_index=0,
            allocation=allocation,
        )

        other = (
            self.candidates[
                -1
            ].construction_id
        )

        self.assertLess(
            epoch.threshold_for(
                priority
            ),
            epoch.threshold_for(
                other
            ),
        )

    def test_weighted_alpha_sum_stays_inside_epoch_budget(
        self,
    ):
        priority = tuple(
            spec.construction_id
            for spec
            in self.candidates[:7]
        )

        allocation = (
            allocate_hypothesis_mass(
                self.candidates,
                priority_ids=(
                    priority
                ),
            )
        )

        epoch = WeightedEvidenceEpoch(
            self.candidates,
            epoch_index=0,
            allocation=allocation,
        )

        spent_upper_bound = sum(
            (
                Fraction(
                    1,
                    threshold,
                )
                for threshold
                in epoch.thresholds.values()
            ),
            Fraction(
                0,
                1,
            ),
        )

        epoch_budget = Fraction(
            1,
            global_epoch_alpha_denominator(
                0
            ),
        )

        self.assertLessEqual(
            spent_upper_bound,
            epoch_budget,
        )


class CoverageTests(
    unittest.TestCase
):
    def test_prior_never_removes_universal_candidates(
        self,
    ):
        cold = (
            EcologicalConstructionEngine()
        )

        priorities = (
            ConstructionSpec(
                expression=lag(1)
            ),
            ConstructionSpec(
                expression=binary(
                    FeatureOp.XOR,
                    lag(1),
                    lag(4),
                )
            ),
        )

        primed = (
            EcologicalConstructionEngine(
                priority_specs=(
                    priorities
                )
            )
        )

        cold_ids = set(
            cold.candidate_construction_ids
        )

        primed_ids = set(
            primed.candidate_construction_ids
        )

        self.assertTrue(
            cold_ids.issubset(
                primed_ids
            )
        )

    def test_higher_order_safety_field_survives_priming(
        self,
    ):
        priorities = tuple(
            ConstructionSpec(
                expression=lag(k)
            )
            for k in range(
                1,
                9,
            )
        )

        engine = (
            EcologicalConstructionEngine(
                priority_specs=(
                    priorities
                )
            )
        )

        # The critical property is that priming does not collapse
        # candidate coverage back to 64.
        self.assertGreaterEqual(
            len(
                engine.candidate_construction_ids
            ),
            256,
        )

        ecology = (
            engine.ecology_snapshot()
        )

        self.assertGreater(
            ecology.priority_candidate_count,
            0,
        )

        self.assertGreater(
            ecology.maximum_threshold,
            ecology.minimum_threshold,
        )


if __name__ == "__main__":
    unittest.main()
