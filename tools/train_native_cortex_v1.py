#!/usr/bin/env python3
"""Train Mega PRIME Native Cortex V1."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import torch
import torch.nn.functional as F

from core.cortex import (
    BPETokenizer,
    CortexV1Config,
    NativeCortexV1,
)


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
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


def sample_batch(
    stream,
    *,
    batch_size,
    sequence_length,
    generator,
    device,
):
    maximum = (
        len(stream)
        - sequence_length
        - 1
    )

    starts = torch.randint(
        0,
        maximum,
        (
            batch_size,
        ),
        generator=generator,
    )

    rows = []

    for start in (
        starts.tolist()
    ):
        row = np.asarray(
            stream[
                start:
                start
                + sequence_length
                + 1
            ],
            dtype=np.int64,
        )

        rows.append(
            torch.from_numpy(
                row
            )
        )

    batch = torch.stack(
        rows
    ).to(
        device
    )

    return (
        batch[:, :-1],
        batch[:, 1:],
    )


def save_checkpoint(
    path,
    *,
    model,
    optimizer,
    config,
    step,
    tokenizer_path,
):
    torch.save(
        {
            "format": (
                "mega-prime-native-cortex-v1"
            ),
            "architecture": (
                "multi-timescale-delta-"
                "local-attention-top2-moe"
            ),
            "step": step,
            "config": (
                asdict(
                    config
                )
            ),
            "model": (
                model.state_dict()
            ),
            "optimizer": (
                optimizer.state_dict()
            ),
            "tokenizer": (
                str(
                    tokenizer_path
                )
            ),
            "tokenizer_sha256": (
                sha256_file(
                    tokenizer_path
                )
            ),
            "authority": "NONE",
        },
        path,
    )

    return sha256_file(
        path
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train",
        default=(
            "data/native_cortex/"
            "tokens/train.bin"
        ),
    )

    parser.add_argument(
        "--token-manifest",
        default=(
            "data/native_cortex/tokens/"
            "TOKEN_STREAM_MANIFEST.json"
        ),
    )

    parser.add_argument(
        "--tokenizer",
        default=(
            "data/native_cortex/tokenizer/"
            "tokenizer.json"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "artifacts/native_cortex/v1"
        ),
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=2000,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=4,
    )

    parser.add_argument(
        "--sequence-length",
        type=int,
        default=128,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-4,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=260823,
    )

    parser.add_argument(
        "--log-every",
        type=int,
        default=25,
    )

    parser.add_argument(
        "--save-every",
        type=int,
        default=500,
    )

    parser.add_argument(
        "--resume",
        default=None,
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

    tokenizer_path = Path(
        args.tokenizer
    )

    tokenizer = BPETokenizer(
        str(
            tokenizer_path
        )
    )

    stream = np.memmap(
        args.train,
        dtype=np.uint16,
        mode="r",
    )

    config = CortexV1Config(
        vocab_size=(
            tokenizer.vocab_size
        )
    )

    model = NativeCortexV1(
        config
    ).to(
        args.device
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        betas=(
            0.9,
            0.95,
        ),
        weight_decay=0.01,
    )

    start_step = 0

    if args.resume:
        checkpoint = torch.load(
            args.resume,
            map_location=args.device,
            weights_only=False,
        )

        model.load_state_dict(
            checkpoint[
                "model"
            ]
        )

        optimizer.load_state_dict(
            checkpoint[
                "optimizer"
            ]
        )

        start_step = int(
            checkpoint[
                "step"
            ]
        )

        print(
            "resumed:",
            args.resume,
        )

        print(
            "start step:",
            start_step,
        )

    generator = torch.Generator()
    generator.manual_seed(
        args.seed
    )

    output = Path(
        args.output
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    bytes_per_token = None

    manifest_path = Path(
        args.token_manifest
    )

    if manifest_path.exists():
        manifest = json.loads(
            manifest_path.read_text()
        )

        train_info = (
            manifest[
                "splits"
            ][
                "train"
            ]
        )

        bytes_per_token = (
            train_info[
                "utf8_bytes"
            ]
            / train_info[
                "tokens"
            ]
        )

    print("=" * 88)
    print(
        "MEGA PRIME — NATIVE CORTEX V1"
    )
    print("=" * 88)

    print(
        "device:",
        args.device,
    )

    print(
        "training tokens:",
        f"{len(stream):,}",
    )

    print(
        "parameters:",
        f"{model.parameter_count():,}",
    )

    print(
        "vocab:",
        tokenizer.vocab_size,
    )

    print(
        "model width:",
        config.d_model,
    )

    print(
        "layers:",
        config.layers,
    )

    print(
        "experts:",
        config.experts,
    )

    print(
        "train routing:",
        "TOP-2",
    )

    print(
        "inference routing:",
        "TOP-1",
    )

    print(
        "local attention window:",
        config.attention_window,
    )

    print(
        "authority:",
        "NONE",
    )

    print("=" * 88)

    interval_start = (
        time.perf_counter()
    )

    interval_tokens = 0

    model.train()

    for step in range(
        start_step + 1,
        args.steps + 1,
    ):
        x, y = sample_batch(
            stream,
            batch_size=(
                args.batch_size
            ),
            sequence_length=(
                args.sequence_length
            ),
            generator=generator,
            device=args.device,
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        result = model(
            x
        )

        language_loss = (
            F.cross_entropy(
                result.logits.reshape(
                    -1,
                    tokenizer.vocab_size,
                ),
                y.reshape(-1),
            )
        )

        future_offset = 8

        if (
            result.hidden.shape[1]
            > future_offset
        ):
            predicted_future = (
                model.future_predictor(
                    result.hidden[
                        :,
                        :-future_offset,
                        :
                    ]
                )
            )

            predicted_future = (
                F.normalize(
                    predicted_future,
                    dim=-1,
                )
            )

            target_future = (
                F.normalize(
                    result.hidden[
                        :,
                        future_offset:,
                        :
                    ].detach(),
                    dim=-1,
                )
            )

            future_loss = (
                1.0
                - (
                    predicted_future
                    * target_future
                ).sum(
                    dim=-1
                )
            ).mean()

        else:
            future_loss = (
                language_loss
                .new_zeros(())
            )

        training_progress = (
            step
            / max(
                args.steps,
                1,
            )
        )

        anneal = min(
            training_progress
            / 0.70,
            1.0,
        )

        balance_weight = (
            0.15
            * (
                1.0
                - anneal
            )
            + 0.03
            * anneal
        )

        entropy_weight = (
            0.03
            * (
                1.0
                - anneal
            )
            + 0.003
            * anneal
        )

        z_weight = 0.001

        total_loss = (
            language_loss
            + 0.05
            * future_loss
            + balance_weight
            * result.router_balance_loss
            + z_weight
            * result.router_z_loss
            - entropy_weight
            * result.router_entropy_normalized
        )

        total_loss.backward()

        gradient_norm = (
            torch.nn.utils
            .clip_grad_norm_(
                model.parameters(),
                1.0,
            )
        )

        optimizer.step()

        interval_tokens += (
            x.numel()
        )

        if (
            step == 1
            or step
            % args.log_every
            == 0
        ):
            now = (
                time.perf_counter()
            )

            elapsed = max(
                now
                - interval_start,
                1e-9,
            )

            tokens_per_second = (
                interval_tokens
                / elapsed
            )

            pieces = [
                f"step={step:6d}",
                (
                    f"lm="
                    f"{language_loss.item():.4f}"
                ),
                (
                    f"future="
                    f"{future_loss.item():.4f}"
                ),
                (
                    f"balance="
                    f"{result.router_balance_loss.item():.3f}"
                ),
                (
                    f"H="
                    f"{result.router_entropy_normalized.item():.3f}"
                ),
                (
                    f"grad="
                    f"{float(gradient_norm):.3f}"
                ),
                (
                    f"tok/s="
                    f"{tokens_per_second:.0f}"
                ),
            ]

            if (
                bytes_per_token
                is not None
            ):
                pieces.append(
                    (
                        f"raw-B/s="
                        f"{tokens_per_second * bytes_per_token:.0f}"
                    )
                )

            print(
                " ".join(
                    pieces
                )
            )

            interval_tokens = 0
            interval_start = now

        if (
            step
            % args.save_every
            == 0
        ):
            path = (
                output
                / (
                    f"cortex-v1-step-"
                    f"{step:06d}.pt"
                )
            )

            digest = save_checkpoint(
                path,
                model=model,
                optimizer=optimizer,
                config=config,
                step=step,
                tokenizer_path=(
                    tokenizer_path
                ),
            )

            print(
                "checkpoint:",
                path,
            )

            print(
                "sha256:",
                digest,
            )

    final_path = (
        output
        / "cortex-v1-final.pt"
    )

    digest = save_checkpoint(
        final_path,
        model=model,
        optimizer=optimizer,
        config=config,
        step=args.steps,
        tokenizer_path=(
            tokenizer_path
        ),
    )

    print()
    print(
        "final checkpoint:",
        final_path,
    )

    print(
        "final sha256:",
        digest,
    )


if __name__ == "__main__":
    main()
