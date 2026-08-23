"""Mega PRIME Native Cortex V1 tests."""

import unittest

import torch

from core.cortex import (
    CortexV1Config,
    NativeCortexV1,
)


class NativeCortexV1Tests(
    unittest.TestCase
):
    def setUp(
        self,
    ):
        torch.manual_seed(
            20260823
        )

        self.config = CortexV1Config(
            vocab_size=512,
            d_model=96,
            layers=4,
            memory_heads=6,
            attention_heads=6,
            attention_every=2,
            attention_window=8,
            experts=4,
            expert_hidden=128,
            output_rank=32,
        )

        self.model = NativeCortexV1(
            self.config
        )

    def test_forward_shapes(
        self,
    ):
        tokens = torch.randint(
            0,
            self.config.vocab_size,
            (
                2,
                12,
            ),
        )

        result = self.model(
            tokens
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
            result.hidden.shape,
            (
                2,
                12,
                self.config.d_model,
            ),
        )

    def test_recurrence_changes_output(
        self,
    ):
        tokens = torch.randint(
            0,
            self.config.vocab_size,
            (
                1,
                12,
            ),
        )

        self.model.eval()

        with torch.no_grad():
            normal = self.model(
                tokens
            ).logits

            reset = self.model(
                tokens,
                reset_recurrence=True,
            ).logits

        difference = (
            normal
            - reset
        ).abs().sum().item()

        self.assertGreater(
            difference,
            0.0,
        )

    def test_local_attention_changes_output(
        self,
    ):
        tokens = torch.randint(
            0,
            self.config.vocab_size,
            (
                1,
                12,
            ),
        )

        self.model.eval()

        with torch.no_grad():
            normal = self.model(
                tokens
            ).logits

            disabled = self.model(
                tokens,
                disable_attention=True,
            ).logits

        difference = (
            normal
            - disabled
        ).abs().sum().item()

        self.assertGreater(
            difference,
            0.0,
        )

    def test_attention_cache_is_bounded(
        self,
    ):
        states = None

        self.model.eval()

        with torch.no_grad():
            for _ in range(20):
                token = torch.randint(
                    0,
                    self.config.vocab_size,
                    (1,),
                )

                (
                    _,
                    _,
                    _,
                    states,
                    _,
                    _,
                    _,
                    _,
                ) = self.model.step(
                    token,
                    states,
                )

        for block, state in zip(
            self.model.blocks,
            states,
        ):
            if block.use_attention:
                self.assertLessEqual(
                    state.attention_keys.shape[2],
                    self.config.attention_window,
                )

    def test_diagnostics_exist(
        self,
    ):
        tokens = torch.randint(
            0,
            self.config.vocab_size,
            (
                1,
                8,
            ),
        )

        self.model.eval()

        with torch.no_grad():
            result = self.model(
                tokens,
                collect_diagnostics=True,
            )

        self.assertEqual(
            len(
                result.diagnostics
            ),
            self.config.layers,
        )

    def test_no_authority_interface(
        self,
    ):
        forbidden = {
            "authorize",
            "canonicalize",
            "commit",
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


class FullArchitectureTests(
    unittest.TestCase
):
    def test_full_model_is_mega_scale(
        self,
    ):
        model = NativeCortexV1(
            CortexV1Config()
        )

        parameters = (
            model.parameter_count()
        )

        print(
            "Native Cortex V1 parameters:",
            f"{parameters:,}",
        )

        self.assertGreater(
            parameters,
            5_000_000,
        )

        self.assertLess(
            parameters,
            10_000_000,
        )


if __name__ == "__main__":
    unittest.main()
