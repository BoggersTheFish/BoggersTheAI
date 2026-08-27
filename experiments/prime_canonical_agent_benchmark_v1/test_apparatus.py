"""Dependency-free correctness tests for benchmark apparatus.

These tests use development seeds only.
"""

import json
import unittest

from .baselines import HistoryRepresentation
from .environment import MemoryAliasPOMDP
from .runner import run_fixed_condition


class EnvironmentTests(unittest.TestCase):
    def test_environment_is_deterministic(self):
        actions = [0, 1] * 40

        def trace():
            env = MemoryAliasPOMDP(7)
            observation = env.reset(3)
            out = []

            for action in actions[:68]:
                r = env.step(action)
                out.append(
                    (
                        observation,
                        r.reward,
                        r.scored,
                        r.done,
                        r.next_observation,
                    )
                )

                if not r.done:
                    observation = r.next_observation

            return out

        self.assertEqual(trace(), trace())

    def test_all_worlds_have_same_warmup_length(self):
        for seed in range(8):
            env = MemoryAliasPOMDP(seed)
            env.reset(0)
            scored = []
            for _ in range(8):
                scored.append(env.step(0).scored)
            self.assertEqual(
                scored,
                [False, False, False, False, True, True, True, True],
            )


class RepresentationTests(unittest.TestCase):
    def test_depth_zero_is_current_observation_only(self):
        rep = HistoryRepresentation(depth=0)
        self.assertEqual(rep.observe(1), (1,))
        self.assertEqual(rep.observe(0), (0,))
        self.assertEqual(rep.observe(1), (1,))

    def test_depth_four_tracks_five_symbols(self):
        rep = HistoryRepresentation(depth=4)
        for bit in (1, 0, 1, 1, 0):
            state = rep.observe(bit)
        self.assertEqual(state, (1, 0, 1, 1, 0))


class RunnerTests(unittest.TestCase):
    def test_result_is_byte_reproducible(self):
        first = run_fixed_condition(3, "FIXED-H2")
        second = run_fixed_condition(3, "FIXED-H2")

        self.assertEqual(first.canonical_bytes(), second.canonical_bytes())
        self.assertEqual(first.sha256(), second.sha256())

    def test_result_contains_no_native_floats(self):
        result = run_fixed_condition(4, "REACTIVE").payload

        def walk(value):
            self.assertNotIsInstance(value, float)
            if isinstance(value, dict):
                for k, v in value.items():
                    self.assertIsInstance(k, str)
                    walk(v)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(result)

    def test_canonical_json_round_trip(self):
        result = run_fixed_condition(5, "FIXED-H1")
        decoded = json.loads(result.canonical_bytes())
        self.assertEqual(decoded, result.payload)

    def test_fixed_conditions_have_zero_repairs(self):
        for condition in (
            "REACTIVE",
            "FIXED-H1",
            "FIXED-H2",
            "FIXED-H4",
        ):
            payload = run_fixed_condition(6, condition).payload
            self.assertEqual(payload["proposed_repairs"], 0)
            self.assertEqual(payload["accepted_repairs"], 0)
            self.assertEqual(payload["rejected_repairs"], 0)


if __name__ == "__main__":
    unittest.main()
