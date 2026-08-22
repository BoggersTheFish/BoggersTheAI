"""Development-only invariant tests for adaptive benchmark v1.1."""

from copy import deepcopy
import unittest

from .adaptive_runner import run_adaptive_condition
from .receipts import ReceiptChain, verify_receipt_chain
from .verifier import ProbeEvent, evaluate_candidates


def paired_events(
    count: int,
    *,
    informative_depths: tuple[int, ...],
) -> list[ProbeEvent]:
    events = []

    # Each train event is followed by a matching validation event.
    for pair_index in range(count // 2):
        target = pair_index % 2

        for _ in range(2):
            candidates = {}

            for depth in (1, 2, 4):
                if depth in informative_depths:
                    state = (target,) + (0,) * depth
                else:
                    state = (0,) * (depth + 1)

                candidates[depth] = state

            events.append(
                ProbeEvent(
                    current_state=(0,),
                    candidate_states=candidates,
                    target=target,
                )
            )

    return events


class VerifierTests(unittest.TestCase):
    def test_smallest_supported_candidate_is_recoverable(self):
        events = paired_events(
            160,
            informative_depths=(1, 2, 4),
        )

        summaries, supported = evaluate_candidates(
            current_depth=0,
            candidate_depths=(1, 2, 4),
            events=events,
        )

        self.assertTrue(supported)
        self.assertEqual(min(supported), 1)

        by_depth = {
            row["candidate_depth"]: row
            for row in summaries
        }

        self.assertTrue(by_depth[1]["supported"])

    def test_complexity_can_reject_large_representation(self):
        events = paired_events(
            80,
            informative_depths=(4,),
        )

        summaries, supported = evaluate_candidates(
            current_depth=0,
            candidate_depths=(4,),
            events=events,
        )

        row = summaries[0]

        self.assertEqual(row["candidate_depth"], 4)
        self.assertFalse(row["supported"])
        self.assertEqual(supported, ())
        self.assertGreaterEqual(
            row["complexity_cost"],
            row["net_advantage"],
        )

    def test_clear_strong_h4_evidence_can_pass(self):
        events = paired_events(
            200,
            informative_depths=(4,),
        )

        summaries, supported = evaluate_candidates(
            current_depth=0,
            candidate_depths=(4,),
            events=events,
        )

        self.assertEqual(supported, (4,))
        self.assertTrue(summaries[0]["supported"])


class ReceiptTests(unittest.TestCase):
    def test_receipt_chain_detects_tampering(self):
        chain = ReceiptChain()

        chain.append(
            {
                "benchmark_version": "test",
                "condition": "FULL-PRIME",
                "world_seed": 0,
            }
        )

        chain.append(
            {
                "benchmark_version": "test",
                "condition": "FULL-PRIME",
                "world_seed": 0,
            }
        )

        records = chain.records
        self.assertTrue(verify_receipt_chain(records))

        tampered = deepcopy(records)
        tampered[0]["payload"]["world_seed"] = 999

        self.assertFalse(verify_receipt_chain(tampered))


class AdaptiveRunnerTests(unittest.TestCase):
    def test_evaluation_seed_is_blocked_by_default(self):
        with self.assertRaises(RuntimeError):
            run_adaptive_condition(
                1000,
                "FULL-PRIME",
            )

    def test_development_run_is_byte_reproducible(self):
        first = run_adaptive_condition(
            1,
            "FULL-PRIME",
        )
        second = run_adaptive_condition(
            1,
            "FULL-PRIME",
        )

        self.assertEqual(
            first.canonical_bytes(),
            second.canonical_bytes(),
        )
        self.assertEqual(
            first.sha256(),
            second.sha256(),
        )

    def test_result_has_valid_receipt_chain(self):
        result = run_adaptive_condition(
            2,
            "FULL-PRIME",
        )

        self.assertTrue(
            verify_receipt_chain(
                result.payload["repair_receipts"]
            )
        )

    def test_no_native_floats(self):
        result = run_adaptive_condition(
            3,
            "ADAPTIVE-NO-VERIFIER",
        ).payload

        def walk(value):
            self.assertNotIsInstance(value, float)

            if isinstance(value, dict):
                for key, item in value.items():
                    self.assertIsInstance(key, str)
                    walk(item)

            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(result)


if __name__ == "__main__":
    unittest.main()
