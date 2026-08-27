"""Mega PRIME Native Cortex tests."""

import unittest

import torch

from core.cortex import (
    ByteTokenizer,
    CortexConfig,
    NativeCortex,
    TernaryLinear,
)


class TokenizerTests(
    unittest.TestCase
):
    def test_utf8_roundtrip(
        self,
    ):
        tokenizer = (
            ByteTokenizer()
        )

        source = (
            "PRIME learns ⚡ relations."
        )

        tokens = tokenizer.encode(
            source
        )

        self.assertEqual(
            tokenizer.decode(
                tokens
            ),
            source,
        )


class TernaryTests(
    unittest.TestCase
):
    def test_effective_weight_has_at_most_three_scaled_values_per_row(
        self,
    ):
        layer = TernaryLinear(
            16,
            8,
        )

        weight = (
            layer.effective_weight()
            .detach()
        )

        for row in weight:
            self.assertLessEqual(
                torch.unique(
                    row
                ).numel(),
                3,
            )


class CortexTests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        torch.manual_seed(
            123
        )

        self.config = (
            CortexConfig(
                d_model=48,
                layers=2,
                memory_heads=4,
                experts=3,
                expert_hidden=96,
            )
        )

        self.model = (
            NativeCortex(
                self.config
            )
        )

    def test_forward_shape(
        self,
    ):
        x = torch.randint(
            0,
            self.config.vocab_size,
            (
                2,
                12,
            ),
        )

        result = self.model(
            x
        )

        self.assertEqual(
            result.logits.shape,
            (
                2,
                12,
                self.config.vocab_size,
            ),
        )

        self.assertEqual(
            result.verifier_logits.shape,
            (
                2,
                12,
                self.config.verifier_classes,
            ),
        )

    def test_recurrent_state_changes(
        self,
    ):
        token = torch.tensor(
            [
                65
            ]
        )

        (
            _,
            _,
            states_a,
            _,
            _,
        ) = self.model.step(
            token
        )

        (
            _,
            _,
            states_b,
            _,
            _,
        ) = self.model.step(
            token,
            states_a,
        )

        difference = sum(
            (
                b
                - a
            ).abs().sum().item()
            for a, b
            in zip(
                states_a,
                states_b,
            )
        )

        self.assertGreater(
            difference,
            0.0,
        )

    def test_native_observability(
        self,
    ):
        token = torch.tensor(
            [
                65
            ]
        )

        (
            _,
            _,
            _,
            _,
            telemetry,
        ) = self.model.step(
            token,
            telemetry=True,
        )

        self.assertEqual(
            len(telemetry),
            self.config.layers,
        )

        for row in telemetry:
            self.assertGreaterEqual(
                row.write_mean,
                0.0,
            )

            self.assertGreaterEqual(
                row.erase_mean,
                0.0,
            )

            self.assertGreaterEqual(
                row.selected_expert,
                0,
            )

    def test_cortex_exposes_no_authority_method(
        self,
    ):
        forbidden = {
            "authorize",
            "commit",
            "canonicalize",
        }

        self.assertTrue(
            forbidden.isdisjoint(
                set(
                    dir(
                        self.model
                    )
                )
            )
        )


if __name__ == "__main__":
    unittest.main()
