"""Invariant and adversarial tests for PRIME benchmark v1.3."""

from copy import deepcopy
import unittest

from experiments.prime_canonical_agent_benchmark_v1_2.receipts import (
    ReceiptChain,
    verify_receipt_chain,
)

from .adaptive_runner import (
    _promote_policy,
    run_adaptive_condition,
)
from .factor_verifier import (
    CARRIER_COST,
    COORDINATE_COST,
    FactorizedVerifierEpoch,
    WitnessEvidence,
    active_witness_lags,
    required_depth_for_lag,
)


class WitnessMathTests(
    unittest.TestCase
):
    def test_mapping(self):
        self.assertEqual(
            required_depth_for_lag(1),
            1,
        )
        self.assertEqual(
            required_depth_for_lag(2),
            2,
        )
        self.assertEqual(
            required_depth_for_lag(3),
            4,
        )
        self.assertEqual(
            required_depth_for_lag(4),
            4,
        )

    def test_active_stream_count(self):
        self.assertEqual(
            active_witness_lags(0),
            (1, 2, 3, 4),
        )
        self.assertEqual(
            active_witness_lags(1),
            (2, 3, 4),
        )
        self.assertEqual(
            active_witness_lags(2),
            (3, 4),
        )
        self.assertEqual(
            active_witness_lags(4),
            (),
        )

        self.assertEqual(
            4 + 3 + 2,
            9,
        )

    def test_anytime_threshold_boundary(self):
        evidence = WitnessEvidence(
            lag=1,
            wins=15,
            losses=0,
        )

        self.assertFalse(
            evidence.statistical_pass
        )

        evidence.wins = 16

        self.assertTrue(
            evidence.statistical_pass
        )

    def test_carrier_h4_cost_is_30(self):
        evidence = WitnessEvidence(
            lag=4
        )

        self.assertEqual(
            evidence.complexity_cost(
                0,
                CARRIER_COST,
            ),
            30,
        )

    def test_coordinate_h4_cost_is_4(self):
        evidence = WitnessEvidence(
            lag=4
        )

        self.assertEqual(
            evidence.complexity_cost(
                0,
                COORDINATE_COST,
            ),
            4,
        )

    def test_factorized_state_is_not_h4_carrier(self):
        verifier = (
            FactorizedVerifierEpoch(
                current_depth=0,
                complexity_rule=(
                    COORDINATE_COST
                ),
            )
        )

        frozen = (
            verifier.freeze_prediction(
                1,
                (1,),
            )
        )

        # H0 + one witness coordinate.
        self.assertEqual(
            len(
                frozen.witness_states[
                    4
                ]
            ),
            2,
        )

        # Policy remains H0.
        self.assertEqual(
            len(
                frozen.current_state
            ),
            1,
        )

    def test_selection_prefers_smallest_policy_depth(self):
        verifier = (
            FactorizedVerifierEpoch(
                current_depth=0,
                complexity_rule=(
                    COORDINATE_COST
                ),
            )
        )

        # Artificial evidence only for
        # selection-rule invariant.
        verifier.evidence[2].wins = 20
        verifier.evidence[4].wins = 20

        self.assertEqual(
            verifier.selected_supported_lag(),
            2,
        )

    def test_equal_depth_prefers_smaller_lag(self):
        verifier = (
            FactorizedVerifierEpoch(
                current_depth=0,
                complexity_rule=(
                    COORDINATE_COST
                ),
            )
        )

        verifier.evidence[3].wins = 20
        verifier.evidence[4].wins = 20

        self.assertEqual(
            verifier.selected_supported_lag(),
            3,
        )


    def test_same_evidence_separates_cost_ablations(self):
        evidence = WitnessEvidence(
            lag=4,
            wins=16,
            losses=0,
        )

        self.assertTrue(
            evidence.statistical_pass
        )

        self.assertTrue(
            evidence.supported(
                0,
                COORDINATE_COST,
            )
        )

        self.assertFalse(
            evidence.supported(
                0,
                CARRIER_COST,
            )
        )

    def test_mid_episode_h0_to_h4_does_not_copy_private_history(self):
        # Build a verifier with deep private history while the
        # authorized policy remains H0.
        old_verifier = FactorizedVerifierEpoch(
            current_depth=0,
            complexity_rule=COORDINATE_COST,
        )

        policy_state = None

        for observation in (
            1,
            0,
            1,
            1,
            1,
        ):
            policy_state = (
                observation,
            )

            old_verifier.freeze_prediction(
                observation,
                policy_state,
            )

        self.assertEqual(
            policy_state,
            (1,),
        )

        # Direct H0 -> H4 authorization.
        new_policy = _promote_policy(
            policy_state,
            4,
        )

        new_verifier = FactorizedVerifierEpoch(
            current_depth=4,
            complexity_rule=COORDINATE_COST,
        )

        # Critically, seed from authorized H0 state only.
        new_verifier.seed_mid_episode(
            policy_state
        )

        next_observation = 0

        next_policy_state = (
            new_policy.observe(
                next_observation
            )
        )

        frozen = (
            new_verifier.freeze_prediction(
                next_observation,
                next_policy_state,
            )
        )

        # Policy and verifier agree after the jump.
        self.assertEqual(
            frozen.current_state,
            next_policy_state,
        )

        # If private pre-authorization history had leaked into
        # the new policy, this state would differ.
        leaked_h4_state = (
            0,
            1,
            1,
            1,
            0,
        )

        self.assertNotEqual(
            next_policy_state,
            leaked_h4_state,
        )


class ReceiptTamperTests(
    unittest.TestCase
):
    def _chain(self):
        chain = ReceiptChain()

        payload = {
            "benchmark_version": (
                "prime-canonical-agent-benchmark-v1.3"
            ),
            "condition": (
                "FULL-PRIME-V1.3"
            ),
            "world_seed": 300,
            "canonical_depth_before": 0,
            "candidate_witness_lags": [
                1,
                2,
                3,
                4,
            ],
            "witness_to_policy_depth": {
                "1": 1,
                "2": 2,
                "3": 4,
                "4": 4,
            },
            "witness_evidence": [
                {
                    "witness_lag": 4,
                    "required_policy_depth": 4,
                    "wins": 20,
                    "losses": 0,
                    "complexity_rule": (
                        COORDINATE_COST
                    ),
                    "complexity_cost": 4,
                }
            ],
            "supported_witness_lags": [
                4
            ],
            "selected_witness_lag": 4,
            "selected_required_depth": 4,
            "authorized_depth": 4,
        }

        chain.append(payload)
        chain.append(
            {
                **payload,
                "canonical_depth_before": 4,
                "candidate_witness_lags": [],
                "supported_witness_lags": [],
                "selected_witness_lag": None,
                "selected_required_depth": None,
                "authorized_depth": None,
            }
        )

        return (
            chain.records,
            chain.count,
            chain.tip,
        )

    def _assert_tampered(
        self,
        mutation,
    ):
        records, count, tip = (
            self._chain()
        )

        self.assertTrue(
            verify_receipt_chain(
                records,
                expected_count=count,
                expected_tip=tip,
            )
        )

        damaged = deepcopy(
            records
        )

        mutation(damaged)

        self.assertFalse(
            verify_receipt_chain(
                damaged,
                expected_count=count,
                expected_tip=tip,
            )
        )

    def test_witness_lag(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "witness_evidence"
            ][0].__setitem__(
                "witness_lag",
                3,
            )
        )

    def test_witness_w(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "witness_evidence"
            ][0].__setitem__(
                "wins",
                999,
            )
        )

    def test_witness_l(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "witness_evidence"
            ][0].__setitem__(
                "losses",
                999,
            )
        )

    def test_mapped_depth(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "witness_to_policy_depth"
            ].__setitem__(
                "4",
                2,
            )
        )

    def test_complexity_rule(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "witness_evidence"
            ][0].__setitem__(
                "complexity_rule",
                CARRIER_COST,
            )
        )

    def test_complexity_cost(self):
        self._assert_tampered(
            lambda r: r[0]["payload"][
                "witness_evidence"
            ][0].__setitem__(
                "complexity_cost",
                30,
            )
        )

    def test_authorized_depth(self):
        self._assert_tampered(
            lambda r: r[0]["payload"].__setitem__(
                "authorized_depth",
                2,
            )
        )

    def test_world_seed(self):
        self._assert_tampered(
            lambda r: r[0]["payload"].__setitem__(
                "world_seed",
                999,
            )
        )

    def test_previous_hash(self):
        self._assert_tampered(
            lambda r: r[1]["payload"].__setitem__(
                "previous_receipt_hash",
                "f" * 64,
            )
        )

    def test_deletion(self):
        self._assert_tampered(
            lambda r: r.pop()
        )

    def test_insertion(self):
        self._assert_tampered(
            lambda r: r.insert(
                1,
                deepcopy(r[0]),
            )
        )

    def test_reordering(self):
        def mutate(records):
            records[0], records[1] = (
                records[1],
                records[0],
            )

        self._assert_tampered(
            mutate
        )


class RunnerTests(
    unittest.TestCase
):
    def test_v1_3_evaluation_seed_blocked(self):
        with self.assertRaises(
            RuntimeError
        ):
            run_adaptive_condition(
                3000,
                "FULL-PRIME-V1.3",
            )

    def test_nondevelopment_seed_blocked(self):
        with self.assertRaises(
            RuntimeError
        ):
            run_adaptive_condition(
                2999,
                "FULL-PRIME-V1.3",
            )

    def test_full_v13_byte_reproducible(self):
        first = (
            run_adaptive_condition(
                301,
                "FULL-PRIME-V1.3",
            )
        )

        second = (
            run_adaptive_condition(
                301,
                "FULL-PRIME-V1.3",
            )
        )

        self.assertEqual(
            first.canonical_bytes(),
            second.canonical_bytes(),
        )

        self.assertEqual(
            first.sha256(),
            second.sha256(),
        )

    def test_v12_reference_byte_reproducible(self):
        first = (
            run_adaptive_condition(
                302,
                "FULL-PRIME-V1.2-REFERENCE",
            )
        )

        second = (
            run_adaptive_condition(
                302,
                "FULL-PRIME-V1.2-REFERENCE",
            )
        )

        self.assertEqual(
            first.canonical_bytes(),
            second.canonical_bytes(),
        )

    def test_factor_carrier_byte_reproducible(self):
        first = (
            run_adaptive_condition(
                303,
                "FACTOR-WITNESS-CARRIER-COST",
            )
        )

        second = (
            run_adaptive_condition(
                303,
                "FACTOR-WITNESS-CARRIER-COST",
            )
        )

        self.assertEqual(
            first.canonical_bytes(),
            second.canonical_bytes(),
        )

    def test_receipts_verify(self):
        result = (
            run_adaptive_condition(
                304,
                "FULL-PRIME-V1.3",
            ).payload
        )

        self.assertTrue(
            verify_receipt_chain(
                result[
                    "repair_receipts"
                ],
                expected_count=(
                    result[
                        "canonical_receipt_count"
                    ]
                ),
                expected_tip=(
                    result[
                        "repair_receipt_chain_tip"
                    ]
                ),
            )
        )

    def test_no_native_floats_all_conditions(self):
        def walk(value):
            self.assertNotIsInstance(
                value,
                float,
            )

            if isinstance(
                value,
                dict,
            ):
                for key, item in value.items():
                    self.assertIsInstance(
                        key,
                        str,
                    )
                    walk(item)

            elif isinstance(
                value,
                list,
            ):
                for item in value:
                    walk(item)

        for condition in (
            "ADAPTIVE-NO-VERIFIER",
            "FULL-PRIME-V1.2-REFERENCE",
            "FACTOR-WITNESS-CARRIER-COST",
            "FULL-PRIME-V1.3",
        ):
            result = (
                run_adaptive_condition(
                    305,
                    condition,
                ).payload
            )

            walk(result)


if __name__ == "__main__":
    unittest.main()
