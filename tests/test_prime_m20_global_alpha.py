"""Global sequential alpha-spending tests for PRIME M20."""

from fractions import Fraction
import unittest

from core.construction.compositional_engine import (
    CompositionalAdaptiveConstructionEngine,
)
from core.construction.evidence import (
    EvidenceEpoch,
    RUN_LEVEL_ALPHA_DENOMINATOR,
    global_epoch_alpha_denominator,
)
from core.construction.grammar import (
    generate_bounded_candidates,
)


class AlphaScheduleTests(
    unittest.TestCase
):
    def setUp(self):
        self.candidates = tuple(
            generate_bounded_candidates(
                max_lag=2,
                max_candidates=8,
            )
        )

    def test_legacy_single_epoch_semantics_preserved(
        self,
    ):
        epoch = EvidenceEpoch(
            self.candidates
        )

        self.assertEqual(
            epoch.alpha_denominator,
            64,
        )

        self.assertEqual(
            epoch.threshold,
            64 * len(
                self.candidates
            ),
        )

    def test_adaptive_epoch_zero_reserves_future_budget(
        self,
    ):
        epoch = EvidenceEpoch(
            self.candidates,
            epoch_index=0,
        )

        self.assertEqual(
            epoch.alpha_denominator,
            128,
        )

        self.assertEqual(
            epoch.threshold,
            128 * len(
                self.candidates
            ),
        )

    def test_dyadic_schedule(
        self,
    ):
        expected = (
            128,
            256,
            512,
            1024,
            2048,
        )

        observed = tuple(
            global_epoch_alpha_denominator(
                epoch
            )
            for epoch
            in range(
                len(expected)
            )
        )

        self.assertEqual(
            observed,
            expected,
        )

    def test_negative_epoch_rejected(
        self,
    ):
        with self.assertRaises(
            ValueError
        ):
            global_epoch_alpha_denominator(
                -1
            )

    def test_infinite_schedule_sums_to_run_budget(
        self,
    ):
        # Explicitly verify a finite prefix plus its exact
        # geometric tail equals 1/64.
        prefix_length = 20

        prefix = sum(
            (
                Fraction(
                    1,
                    global_epoch_alpha_denominator(
                        epoch
                    ),
                )
                for epoch
                in range(
                    prefix_length
                )
            ),
            Fraction(0, 1),
        )

        tail = Fraction(
            1,
            (
                RUN_LEVEL_ALPHA_DENOMINATOR
                * (1 << prefix_length)
            ),
        )

        self.assertEqual(
            prefix + tail,
            Fraction(
                1,
                RUN_LEVEL_ALPHA_DENOMINATOR,
            ),
        )


class CompositionalEngineTests(
    unittest.TestCase
):
    def test_engine_epoch_zero_uses_global_schedule(
        self,
    ):
        engine = (
            CompositionalAdaptiveConstructionEngine(
                max_lag=2,
                max_candidates=8,
                enable_scaffolds=False,
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


if __name__ == "__main__":
    unittest.main()
