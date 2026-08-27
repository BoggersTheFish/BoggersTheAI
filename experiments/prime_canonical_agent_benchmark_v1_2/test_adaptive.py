"""Invariant and adversarial tests for benchmark v1.2."""

from copy import deepcopy
import unittest

from .adaptive_runner import (
    run_adaptive_condition,
)
from .receipts import (
    ReceiptChain,
    verify_receipt_chain,
)
from .verifier import (
    CandidateEvidence,
    PrequentialPredictor,
    SequentialVerifierEpoch,
)


class EvidenceTests(unittest.TestCase):
    def test_anytime_threshold_exact_boundary(self):
        evidence = CandidateEvidence(
            depth=1,
            wins=14,
            losses=0,
        )

        self.assertFalse(
            evidence.statistical_pass
        )

        evidence.wins = 15

        self.assertTrue(
            evidence.statistical_pass
        )

    def test_h4_complexity_requires_more_than_30_net(self):
        evidence = CandidateEvidence(
            depth=4,
            wins=30,
            losses=0,
        )

        self.assertTrue(
            evidence.statistical_pass
        )

        self.assertFalse(
            evidence.complexity_pass(0)
        )

        evidence.wins = 31

        self.assertTrue(
            evidence.supported(0)
        )

    def test_predictor_is_prequential(self):
        predictor = PrequentialPredictor()
        state = (0,)

        self.assertEqual(
            predictor.predict(state),
            0,
        )

        predictor.update(
            state,
            1,
        )

        self.assertEqual(
            predictor.predict(state),
            1,
        )

    def test_verifier_private_history_matches_current_policy_only(self):
        verifier = SequentialVerifierEpoch(
            current_depth=0
        )

        frozen = verifier.freeze_prediction(
            1,
            (1,),
        )

        self.assertEqual(
            frozen.current_state,
            (1,),
        )

        self.assertIn(
            4,
            frozen.candidate_states,
        )

        # H4 verifier state exists, but policy current state remains H0.
        self.assertEqual(
            len(frozen.current_state),
            1,
        )
        self.assertEqual(
            len(frozen.candidate_states[4]),
            5,
        )


class ReceiptTamperTests(unittest.TestCase):
    def _chain(self):
        chain = ReceiptChain()

        for sequence in range(3):
            chain.append(
                {
                    "benchmark_version": "test",
                    "condition": "FULL-PRIME-V1.2",
                    "world_seed": 100,
                    "candidate_depths": [1, 2, 4],
                    "verifier_evidence": [
                        {
                            "candidate_depth": 1,
                            "wins": 15 + sequence,
                            "losses": 0,
                            "complexity_cost": 2,
                        }
                    ],
                    "authorized_depth": 1,
                }
            )

        return (
            chain.records,
            chain.count,
            chain.tip,
        )

    def _assert_tampered(self, mutator):
        records, count, tip = self._chain()

        self.assertTrue(
            verify_receipt_chain(
                records,
                expected_count=count,
                expected_tip=tip,
            )
        )

        damaged = deepcopy(records)
        mutator(damaged)

        self.assertFalse(
            verify_receipt_chain(
                damaged,
                expected_count=count,
                expected_tip=tip,
            )
        )

    def test_changed_w(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "verifier_evidence"
            ][0].__setitem__(
                "wins",
                999,
            )
        )

    def test_changed_l(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "verifier_evidence"
            ][0].__setitem__(
                "losses",
                999,
            )
        )

    def test_changed_candidate_depth(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "verifier_evidence"
            ][0].__setitem__(
                "candidate_depth",
                4,
            )
        )

    def test_changed_complexity_cost(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "verifier_evidence"
            ][0].__setitem__(
                "complexity_cost",
                999,
            )
        )

    def test_changed_authorization_depth(self):
        self._assert_tampered(
            lambda r: r[0]["payload"].__setitem__(
                "authorized_depth",
                4,
            )
        )

    def test_changed_previous_hash(self):
        self._assert_tampered(
            lambda r: r[1]["payload"].__setitem__(
                "previous_receipt_hash",
                "f" * 64,
            )
        )

    def test_changed_world_seed(self):
        self._assert_tampered(
            lambda r: r[0]["payload"].__setitem__(
                "world_seed",
                999,
            )
        )

    def test_receipt_deletion(self):
        self._assert_tampered(
            lambda r: r.pop()
        )

    def test_receipt_insertion(self):
        self._assert_tampered(
            lambda r: r.insert(
                1,
                deepcopy(r[0]),
            )
        )

    def test_receipt_reordering(self):
        def mutate(records):
            records[0], records[1] = (
                records[1],
                records[0],
            )

        self._assert_tampered(
            mutate
        )


class RunnerTests(unittest.TestCase):
    def test_v1_2_evaluation_seed_blocked(self):
        with self.assertRaises(RuntimeError):
            run_adaptive_condition(
                2000,
                "FULL-PRIME-V1.2",
            )

    def test_nondevelopment_seed_blocked(self):
        with self.assertRaises(RuntimeError):
            run_adaptive_condition(
                999,
                "FULL-PRIME-V1.2",
            )

    def test_development_run_byte_reproducible(self):
        first = run_adaptive_condition(
            101,
            "FULL-PRIME-V1.2",
        )
        second = run_adaptive_condition(
            101,
            "FULL-PRIME-V1.2",
        )

        self.assertEqual(
            first.canonical_bytes(),
            second.canonical_bytes(),
        )

        self.assertEqual(
            first.sha256(),
            second.sha256(),
        )

    def test_receipts_verify_with_anchors(self):
        result = run_adaptive_condition(
            102,
            "FULL-PRIME-V1.2",
        ).payload

        self.assertTrue(
            verify_receipt_chain(
                result["repair_receipts"],
                expected_count=(
                    result["canonical_receipt_count"]
                ),
                expected_tip=(
                    result["repair_receipt_chain_tip"]
                ),
            )
        )

    def test_no_native_floats(self):
        payload = run_adaptive_condition(
            103,
            "ADAPTIVE-NO-VERIFIER",
        ).payload

        def walk(value):
            self.assertNotIsInstance(
                value,
                float,
            )

            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertIsInstance(
                        key,
                        str,
                    )
                    walk(item)

            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(payload)


if __name__ == "__main__":
    unittest.main()
