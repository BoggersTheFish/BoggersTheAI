#!/usr/bin/env python3
"""Streaming generation with native TSObs telemetry."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import torch

from core.cortex import (
    ByteTokenizer,
    CortexConfig,
    NativeCortex,
    TSObs,
    append_jsonl,
)


def sha256_file(
    path,
):
    digest = hashlib.sha256()

    with open(
        path,
        "rb",
    ) as handle:
        for chunk in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def sample_token(
    logits,
    *,
    temperature,
    top_k,
):
    logits = (
        logits
        / max(
            temperature,
            1e-5,
        )
    )

    if top_k > 0:
        values, indices = (
            torch.topk(
                logits,
                min(
                    top_k,
                    logits.shape[-1],
                ),
            )
        )

        probabilities = (
            torch.softmax(
                values,
                dim=-1,
            )
        )

        selected = (
            torch.multinomial(
                probabilities,
                num_samples=1,
            )
        )

        return indices[
            selected
        ].item()

    probabilities = (
        torch.softmax(
            logits,
            dim=-1,
        )
    )

    return torch.multinomial(
        probabilities,
        num_samples=1,
    ).item()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--checkpoint",
        required=True,
    )

    parser.add_argument(
        "--prompt",
        required=True,
    )

    parser.add_argument(
        "--tokens",
        type=int,
        default=200,
    )

    parser.add_argument(
        "--temperature",
        type=float,
        default=0.8,
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=32,
    )

    parser.add_argument(
        "--telemetry",
        default=(
            "/tmp/native-cortex-tsobs.jsonl"
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=260002,
    )

    parser.add_argument(
        "--device",
        default=(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        ),
    )

    args = parser.parse_args()

    torch.manual_seed(
        args.seed
    )

    checkpoint = torch.load(
        args.checkpoint,
        map_location=(
            args.device
        ),
        weights_only=False,
    )

    config = CortexConfig(
        **checkpoint[
            "config"
        ]
    )

    tokenizer = (
        ByteTokenizer()
    )

    model = NativeCortex(
        config
    ).to(
        args.device
    )

    model.load_state_dict(
        checkpoint[
            "model"
        ]
    )

    model.eval()

    model_id = (
        sha256_file(
            args.checkpoint
        )[
            :16
        ]
    )

    telemetry_path = Path(
        args.telemetry
    )

    if telemetry_path.exists():
        telemetry_path.unlink()

    prompt_tokens = (
        tokenizer.encode(
            args.prompt,
            add_bos=True,
            add_eos=False,
        )
    )

    states = None

    logits = None

    sequence = 0

    with torch.no_grad():
        for token in (
            prompt_tokens
        ):
            token_tensor = torch.tensor(
                [
                    token
                ],
                dtype=torch.long,
                device=(
                    args.device
                ),
            )

            (
                logits,
                verifier_logits,
                states,
                _,
                _,
            ) = model.step(
                token_tensor,
                states,
                telemetry=False,
            )

    generated = []

    for _ in range(
        args.tokens
    ):
        next_token = sample_token(
            logits[
                0
            ],
            temperature=(
                args.temperature
            ),
            top_k=(
                args.top_k
            ),
        )

        if (
            next_token
            == tokenizer.EOS
        ):
            break

        generated.append(
            next_token
        )

        token_tensor = torch.tensor(
            [
                next_token
            ],
            dtype=torch.long,
            device=args.device,
        )

        with torch.no_grad():
            (
                logits,
                verifier_logits,
                states,
                _,
                layer_observations,
            ) = model.step(
                token_tensor,
                states,
                telemetry=True,
            )

        verifier_probabilities = (
            torch.softmax(
                verifier_logits[
                    0
                ],
                dim=-1,
            )
        )

        verifier_confidence, verifier_index = (
            verifier_probabilities.max(
                dim=-1
            )
        )

        top_values, top_indices = (
            torch.topk(
                torch.softmax(
                    logits[
                        0
                    ],
                    dim=-1,
                ),
                5,
            )
        )

        observation = TSObs(
            sequence=sequence,
            model_id=(
                model_id
            ),
            token_id=(
                next_token
            ),
            token_label=(
                tokenizer.token_label(
                    next_token
                )
            ),
            authority="NONE",
            verifier_prediction=(
                int(
                    verifier_index.item()
                )
            ),
            verifier_confidence=(
                float(
                    verifier_confidence.item()
                )
            ),
            top_output_tokens=tuple(
                (
                    int(
                        token.item()
                    ),
                    float(
                        probability.item()
                    ),
                )
                for probability, token
                in zip(
                    top_values,
                    top_indices,
                )
            ),
            layers=tuple(
                layer_observations
            ),
        )

        append_jsonl(
            telemetry_path,
            observation,
        )

        sequence += 1

    print(
        args.prompt
        + tokenizer.decode(
            generated
        )
    )

    print()
    print(
        "TSObs:",
        telemetry_path,
    )

    print(
        "model:",
        model_id,
    )


if __name__ == "__main__":
    main()
