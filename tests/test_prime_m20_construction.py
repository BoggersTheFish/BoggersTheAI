"""PRIME M20 adaptive construction invariant suite."""

from copy import deepcopy
import unittest

try:
    from core.construction.engine import (
        AdaptiveConstructionEngine,
        VerifierGate,
    )
    from core.construction.evidence import (
        CandidateEvidence,
        BinaryMajorityPredictor,
        EvidenceEpoch,
    )
    from core.construction.grammar import (
        binary,
        description_length,
        evaluate,
        generate_bounded_candidates,
        lag,
    )
    from core.construction.receipts import (
        verify_receipt_chain,
    )
    from core.construction.registry import (
        ConstructionRegistry,
    )
    from core.construction.state import (
        ConstructionStateBuilder,
    )
    from core.construction.types import (
        AuthorityAction,
        ConstructionSpec,
        EvidenceSnapshot,
        FeatureOp,
        VerifierAuthorization,
    )
except ImportError:
    from BoggersTheAI.core.construction.engine import (
        AdaptiveConstructionEngine,
        VerifierGate,
    )
    from BoggersTheAI.core.construction.evidence import (
        CandidateEvidence,
        BinaryMajorityPredictor,
        EvidenceEpoch,
    )
    from BoggersTheAI.core.construction.grammar import (
        binary,
        description_length,
        evaluate,
        generate_bounded_candidates,
        lag,
    )
    from BoggersTheAI.core.construction.receipts import (
        verify_receipt_chain,
    )
    from BoggersTheAI.core.construction.registry import (
        ConstructionRegistry,
    )
    from BoggersTheAI.core.construction.state import (
        ConstructionStateBuilder,
    )
    from BoggersTheAI.core.construction.types import (
        AuthorityAction,
        ConstructionSpec,
        EvidenceSnapshot,
        FeatureOp,
        VerifierAuthorization,
    )


class GrammarTests(unittest.TestCase):
    def test_lag(self):
        expr = lag(4)

        history = [
            1,
            0,
            1,
            1,
            0,
        ]

        self.assertEqual(
            evaluate(
                expr,
                history,
            ),
            1,
        )

    def test_xor(self):
        expr = binary(
            FeatureOp.XOR,
            lag(1),
            lag(4),
        )

        history = [
            1,
            0,
            1,
            1,
            0,
        ]

        self.assertEqual(
            evaluate(
                expr,
                history,
            ),
            0,
        )

    def test_eq(self):
        expr = binary(
            FeatureOp.EQ,
            lag(1),
            lag(4),
        )

        history = [
            1,
            0,
            1,
            1,
            0,
        ]

        self.assertEqual(
            evaluate(
                expr,
                history,
            ),
            1,
        )

    def test_commutative_normalization(self):
        a = binary(
            FeatureOp.XOR,
            lag(1),
            lag(4),
        )

        b = binary(
            FeatureOp.XOR,
            lag(4),
            lag(1),
        )

        self.assertEqual(
            a.expression_hash,
            b.expression_hash,
        )

    def test_bounded_generator(self):
        candidates = (
            generate_bounded_candidates()
        )

        self.assertLessEqual(
            len(candidates),
            128,
        )

        ids = [
            item.construction_id
            for item in candidates
        ]

        self.assertEqual(
            len(ids),
            len(set(ids)),
        )

    def test_complexity_order(self):
        self.assertLess(
            description_length(
                lag(4)
            ),
            description_length(
                binary(
                    FeatureOp.XOR,
                    lag(1),
                    lag(4),
                )
            ),
        )


class EvidenceTests(unittest.TestCase):
    def test_single_stream_anytime_boundary(self):
        spec = ConstructionSpec(
            expression=lag(4)
        )

        tracker = CandidateEvidence(
            spec=spec,
            predictor=(
                BinaryMajorityPredictor()
            ),
        )

        # One active stream => threshold 64.
        tracker.wins = 10

        self.assertFalse(
            tracker.statistical_pass(
                64
            )
        )

        tracker.wins = 11

        self.assertTrue(
            tracker.statistical_pass(
                64
            )
        )

        self.assertTrue(
            tracker.structural_pass()
        )

    def test_multiplicity_threshold(self):
        candidates = tuple(
            generate_bounded_candidates(
                max_lag=2,
                max_candidates=8,
            )
        )

        epoch = EvidenceEpoch(
            candidates
        )

        self.assertEqual(
            epoch.threshold,
            64 * len(candidates),
        )


class AuthorityTests(unittest.TestCase):
    def test_registry_proposal_is_not_authority(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        registry.propose(
            spec
        )

        self.assertEqual(
            registry.active_ids(),
            (),
        )

    def test_failed_verdict_cannot_authorize(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        registry.propose(
            spec
        )

        bad = VerifierAuthorization(
            action=(
                AuthorityAction.AUTHORIZE
            ),
            construction_id=(
                spec.construction_id
            ),
            verdict=False,
            evidence_hash="x" * 64,
            reason="FAILED",
        )

        with self.assertRaises(
            PermissionError
        ):
            registry.apply(
                bad
            )

    def test_gate_rejects_unsupported_evidence(self):
        gate = VerifierGate()

        evidence = EvidenceSnapshot(
            construction_id="cx:test",
            wins=1,
            losses=0,
            threshold=64,
            evidence_lhs=3,
            evidence_rhs=128,
            statistical_pass=False,
            structural_cost=4,
            structural_pass=False,
            supported=False,
            obstruction_event_index=10,
            authorization_event_index=10,
        )

        with self.assertRaises(
            PermissionError
        ):
            gate.authorize(
                evidence
            )


class MemoryBoundaryTests(unittest.TestCase):
    def test_authorization_does_not_backfill_private_history(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(4)
        )

        registry.propose(
            spec
        )

        auth = VerifierAuthorization(
            action=(
                AuthorityAction.AUTHORIZE
            ),
            construction_id=(
                spec.construction_id
            ),
            verdict=True,
            evidence_hash="a" * 64,
            reason="TEST_AUTH",
        )

        registry.apply(
            auth
        )

        builder = (
            ConstructionStateBuilder(
                registry
            )
        )

        # Pretend verifier privately saw:
        #
        #   1 0 1 1 1
        #
        # None of it is supplied to builder.

        state = builder.observe(
            0
        )

        # Newly authorized LAG(4) is zero-padded
        # because policy has only prospectively seen
        # the current observation.
        self.assertEqual(
            state,
            (0, 0),
        )

    def test_retirement_removes_policy_feature(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(1)
        )

        registry.propose(
            spec
        )

        registry.apply(
            VerifierAuthorization(
                action=(
                    AuthorityAction.AUTHORIZE
                ),
                construction_id=(
                    spec.construction_id
                ),
                verdict=True,
                evidence_hash="b" * 64,
                reason="TEST",
            )
        )

        builder = (
            ConstructionStateBuilder(
                registry
            )
        )

        self.assertEqual(
            len(
                builder.observe(1)
            ),
            2,
        )

        registry.apply(
            VerifierAuthorization(
                action=(
                    AuthorityAction.RETIRE
                ),
                construction_id=(
                    spec.construction_id
                ),
                verdict=True,
                evidence_hash="c" * 64,
                reason="TEST_RETIRE",
            )
        )

        self.assertEqual(
            builder.observe(0),
            (0,),
        )


class ReceiptTests(unittest.TestCase):
    def test_receipt_tamper_detected(self):
        registry = (
            ConstructionRegistry()
        )

        spec = ConstructionSpec(
            expression=lag(2)
        )

        registry.propose(
            spec
        )

        registry.apply(
            VerifierAuthorization(
                action=(
                    AuthorityAction.AUTHORIZE
                ),
                construction_id=(
                    spec.construction_id
                ),
                verdict=True,
                evidence_hash="d" * 64,
                reason="TEST",
            )
        )

        records = (
            registry.receipts.records
        )

        self.assertTrue(
            verify_receipt_chain(
                records,
                expected_count=(
                    registry.receipts.count
                ),
                expected_tip=(
                    registry.receipts.tip
                ),
            )
        )

        damaged = deepcopy(
            records
        )

        damaged[0][
            "payload"
        ][
            "reason"
        ] = "TAMPER"

        self.assertFalse(
            verify_receipt_chain(
                damaged,
                expected_count=1,
                expected_tip=(
                    registry.receipts.tip
                ),
            )
        )


class EngineTests(unittest.TestCase):
    def test_engine_can_discover_lag4(self):
        spec = ConstructionSpec(
            expression=lag(4)
        )

        engine = (
            AdaptiveConstructionEngine(
                candidates=(spec,)
            )
        )

        engine.begin_episode()

        history = []

        x = 0x12345678

        authorized = False

        for _ in range(2000):
            x = (
                1103515245 * x
                + 12345
            ) & 0x7FFFFFFF

            observation = (
                x >> 29
            ) & 1

            history.append(
                observation
            )

            target = (
                history[-5]
                if len(history) >= 5
                else 0
            )

            engine.observe(
                observation
            )

            decision = (
                engine.finalize(
                    target
                )
            )

            if decision.authorized:
                authorized = True
                break

        self.assertTrue(
            authorized
        )

        self.assertEqual(
            engine.active_construction_ids,
            (
                spec.construction_id,
            ),
        )

        self.assertTrue(
            verify_receipt_chain(
                engine.receipt_chain,
                expected_count=1,
            )
        )


if __name__ == "__main__":
    unittest.main()
