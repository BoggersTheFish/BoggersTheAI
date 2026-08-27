#!/usr/bin/env python3
"""Train Native Cortex Phase II on prepared BPE streams."""

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
    CortexConfig,
    NativeCortex,
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def save_checkpoint(
    path,
    *,
    model,
    optimizer,
    config,
    step,
    tokenizer_path,
):
    payload = {
        "format": (
            "mega-prime-native-cortex-p2-v1"
        ),
        "step": step,
        "config": asdict(config),
        "model": model.state_dict(),
        "optimizer": (
            optimizer.state_dict()
        ),
        "tokenizer": str(
            tokenizer_path
        ),
        "tokenizer_sha256": (
            sha256_file(
                tokenizer_path
            )
        ),
        "authority": "NONE",
    }

    torch.save(
        payload,
        path,
    )

    return sha256_file(
        path
    )


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
        (batch_size,),
        generator=generator,
    )

    rows = []

    for start in starts.tolist():
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
            torch.from_numpy(row)
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


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train",
        default=(
            "data/native_cortex/tokens/"
            "train.bin"
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
            "artifacts/native_cortex/"
            "phase2-bpe-v1"
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
        default=8,
    )

    parser.add_argument(
        "--sequence-length",
        type=int,
        default=128,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=3e-4,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=260101,
    )

    parser.add_argument(
        "--log-every",
        type=int,
        default=50,
    )

    parser.add_argument(
        "--save-every",
        type=int,
        default=500,
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
        str(tokenizer_path)
    )

    stream = np.memmap(
        args.train,
        dtype=np.uint16,
        mode="r",
    )

    config = CortexConfig(
        vocab_size=(
            tokenizer.vocab_size
        ),
        d_model=96,
        layers=3,
        memory_heads=4,
        experts=4,
        expert_hidden=192,
        dropout=0.0,
    )

    model = NativeCortex(
        config
    ).to(
        args.device
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=0.01,
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

    print(
        "device:",
        args.device,
    )

    print(
        "training tokens:",
        f"{len(stream):,}",
    )

    print(
        "vocab:",
        tokenizer.vocab_size,
    )

    print(
        "parameters:",
        f"{model.parameter_count():,}",
    )

    print(
        "architecture:",
        (
            "BPE + ternary + delta recurrence "
            "+ sparse experts"
        ),
    )

    print(
        "authority:",
        "NONE",
    )

    model.train()

    interval_start = (
        time.perf_counter()
    )

    interval_tokens = 0

    for step in range(
        1,
        args.steps + 1,
    ):
        x, y = sample_batch(
            stream,
            batch_size=args.batch_size,
            sequence_length=(
                args.sequence_length
            ),
            generator=generator,
            device=args.device,
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        result = model(x)

        language_loss = (
            F.cross_entropy(
                result.logits.reshape(
                    -1,
                    tokenizer.vocab_size,
                ),
                y.reshape(-1),
            )
        )

        loss = (
            language_loss
            + 0.01
            * result.auxiliary_loss
        )

        loss.backward()

        torch.nn.utils.clip_grad_norm_(
            model.parameters(),
            1.0,
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
            now = time.perf_counter()

            elapsed = max(
                now - interval_start,
                1e-9,
            )

            throughput = (
                interval_tokens
                / elapsed
            )

            print(
                f"step={step:6d}",
                (
                    f"loss="
                    f"{language_loss.item():.4f}"
                ),
                (
                    f"moe="
                    f"{result.auxiliary_loss.item():.4f}"
                ),
                (
                    f"tok/s="
                    f"{throughput:.0f}"
                ),
            )

            interval_start = now
            interval_tokens = 0

        if (
            step
            % args.save_every
            == 0
        ):
            path = (
                output
                / (
                    f"cortex-step-"
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

    final = (
        output
        / "cortex-final.pt"
    )

    digest = save_checkpoint(
        final,
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
        final,
    )

    print(
        "final sha256:",
        digest,
    )


if __name__ == "__main__":
    main()
