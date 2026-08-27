#!/usr/bin/env python3
"""Train Native Cortex V1 from PRIME semantic and verifier feedback.

The cortex learns to predict PRIME.
It never becomes PRIME's authority.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
import torch.nn.functional as F

from core.cortex import (
    BPETokenizer,
    CortexV1Config,
    NativeCortexV1,
)

from core.cortex.prime_bridge import (
    VERIFIER_LABELS,
)

from core.cortex.verifier_prompt import (
    format_verifier_prompt,
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


def load_jsonl(path: str):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        return [
            json.loads(line)
            for line in handle
            if line.strip()
        ]


def lm_batch(
    stream,
    *,
    batch_size,
    sequence_length,
    rng,
    device,
):
    rows = []

    maximum = (
        len(stream)
        - sequence_length
        - 1
    )

    for _ in range(batch_size):
        start = rng.randrange(
            0,
            maximum,
        )

        row = np.asarray(
            stream[
                start:
                start + sequence_length + 1
            ],
            dtype=np.int64,
        )

        rows.append(
            torch.from_numpy(row)
        )

    batch = torch.stack(
        rows
    ).to(device)

    return (
        batch[:, :-1],
        batch[:, 1:],
    )


def semantic_example(
    tokenizer,
    record,
    *,
    max_length,
    device,
):
    prefix_text = (
        "SOURCE:\n"
        + str(record["source_text"])
        + "\n\nTSIR_PROPOSAL:\n"
    )

    target_text = str(
        record["proposal_text"]
    )

    target = tokenizer.encode(
        target_text,
        add_bos=False,
        add_eos=True,
    )

    # Avoid examples whose answer alone fills the context.
    if len(target) >= max_length - 8:
        return None

    prefix = tokenizer.encode(
        prefix_text,
        add_bos=True,
        add_eos=False,
    )

    available_prefix = (
        max_length
        - len(target)
    )

    if len(prefix) > available_prefix:
        prefix = (
            [tokenizer.BOS]
            + prefix[
                -(available_prefix - 1):
            ]
        )

    tokens = (
        prefix
        + target
    )

    x = torch.tensor(
        tokens[:-1],
        dtype=torch.long,
        device=device,
    ).unsqueeze(0)

    y = torch.tensor(
        tokens[1:],
        dtype=torch.long,
        device=device,
    ).unsqueeze(0)

    mask = torch.zeros_like(
        y,
        dtype=torch.bool,
    )

    first_target_prediction = (
        len(prefix)
        - 1
    )

    mask[
        :,
        first_target_prediction:
    ] = True

    return (
        x,
        y,
        mask,
    )


def verifier_example(
    tokenizer,
    record,
    *,
    max_length,
    device,
):
    text = format_verifier_prompt(
        record
    )

    ids = tokenizer.encode(
        text,
        add_bos=True,
        add_eos=True,
    )

    ids = ids[
        -max_length:
    ]

    x = torch.tensor(
        ids,
        dtype=torch.long,
        device=device,
    ).unsqueeze(0)

    label = int(
        record[
            "verifier_label_id"
        ]
    )

    return (
        x,
        label,
    )


def router_regularizer(result):
    return (
        0.025
        * result.router_balance_loss
        + 0.001
        * result.router_z_loss
        - 0.002
        * result.router_entropy_normalized
    )


def save_checkpoint(
    path,
    *,
    model,
    optimizer,
    config,
    tokenizer_path,
    base_checkpoint_hash,
    step,
):
    torch.save(
        {
            "format": (
                "mega-prime-cortex-bridge-v1"
            ),
            "step": step,
            "config": asdict(
                config
            ),
            "model": model.state_dict(),
            "optimizer": (
                optimizer.state_dict()
            ),
            "tokenizer": str(
                tokenizer_path
            ),
            "base_checkpoint_sha256": (
                base_checkpoint_hash
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
        "--checkpoint",
        default=(
            "artifacts/native_cortex/v1/"
            "cortex-v1-final.pt"
        ),
    )

    parser.add_argument(
        "--semantic",
        default=(
            "data/native_cortex/"
            "prime_bridge/train/"
            "semantic.jsonl"
        ),
    )

    parser.add_argument(
        "--verifier",
        default=(
            "data/native_cortex/"
            "prime_bridge/curriculum/"
            "train.jsonl"
        ),
    )

    parser.add_argument(
        "--lm-stream",
        default=(
            "data/native_cortex/"
            "tokens/train.bin"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "artifacts/native_cortex/"
            "prime-bridge-v1"
        ),
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=2000,
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=192,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=8e-5,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=26082301,
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
        "--device",
        default=(
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        ),
    )

    args = parser.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)

    rng = random.Random(
        args.seed
    )

    device = args.device

    checkpoint_path = Path(
        args.checkpoint
    )

    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=False,
    )

    config = CortexV1Config(
        **checkpoint["config"]
    )

    tokenizer_path = Path(
        checkpoint["tokenizer"]
    )

    tokenizer = BPETokenizer(
        str(tokenizer_path)
    )

    model = NativeCortexV1(
        config
    ).to(device)

    model.load_state_dict(
        checkpoint["model"]
    )

    semantic_records = load_jsonl(
        args.semantic
    )

    verifier_records = load_jsonl(
        args.verifier
    )

    if not semantic_records:
        raise RuntimeError(
            "semantic supervision is empty"
        )

    if not verifier_records:
        raise RuntimeError(
            "verifier curriculum is empty"
        )

    label_counts = Counter(
        int(
            row["verifier_label_id"]
        )
        for row in verifier_records
    )

    expected_labels = set(
        range(
            len(VERIFIER_LABELS)
        )
    )

    if set(label_counts) != expected_labels:
        raise RuntimeError(
            "verifier curriculum does not "
            "contain every verdict class: "
            + str(label_counts)
        )

    class_weights = torch.tensor(
        [
            len(verifier_records)
            / (
                len(VERIFIER_LABELS)
                * label_counts[index]
            )
            for index in range(
                len(VERIFIER_LABELS)
            )
        ],
        dtype=torch.float32,
        device=device,
    )

    stream = np.memmap(
        args.lm_stream,
        dtype=np.uint16,
        mode="r",
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        betas=(0.9, 0.95),
        weight_decay=0.01,
    )

    output = Path(
        args.output
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    base_hash = sha256_file(
        checkpoint_path
    )

    print("=" * 92)
    print(
        "MEGA PRIME — CORTEX <-> PRIME TRAINING"
    )
    print("=" * 92)

    print(
        "device:",
        device,
    )

    print(
        "parameters:",
        f"{model.parameter_count():,}",
    )

    print(
        "base checkpoint:",
        base_hash,
    )

    print(
        "semantic records:",
        len(semantic_records),
    )

    print(
        "verifier records:",
        len(verifier_records),
    )

    print(
        "verifier labels:",
        {
            VERIFIER_LABELS[index]:
            label_counts[index]
            for index in range(
                len(VERIFIER_LABELS)
            )
        },
    )

    print(
        "class weights:",
        [
            round(
                float(value),
                4,
            )
            for value
            in class_weights
        ],
    )

    print(
        "task schedule:",
        "50% LM / 30% semantics / 20% verifier",
    )

    print(
        "authority:",
        "NONE",
    )

    print("=" * 92)

    model.train()

    accumulators = {
        "lm": [],
        "semantic": [],
        "verifier": [],
    }

    started = (
        time.perf_counter()
    )

    for step in range(
        1,
        args.steps + 1,
    ):
        slot = (
            step - 1
        ) % 10

        optimizer.zero_grad(
            set_to_none=True
        )

        if slot < 5:
            task = "lm"

            x, y = lm_batch(
                stream,
                batch_size=2,
                sequence_length=128,
                rng=rng,
                device=device,
            )

            result = model(
                x
            )

            task_loss = (
                F.cross_entropy(
                    result.logits.reshape(
                        -1,
                        config.vocab_size,
                    ),
                    y.reshape(-1),
                )
            )

        elif slot < 8:
            task = "semantic"

            example = None

            attempts = 0

            while (
                example is None
            ):
                attempts += 1

                if attempts > 100:
                    raise RuntimeError(
                        "could not construct "
                        "semantic example"
                    )

                record = rng.choice(
                    semantic_records
                )

                example = (
                    semantic_example(
                        tokenizer,
                        record,
                        max_length=(
                            args.max_length
                        ),
                        device=device,
                    )
                )

            x, y, mask = example

            result = model(
                x
            )

            selected_logits = (
                result.logits[
                    mask
                ]
            )

            selected_targets = (
                y[
                    mask
                ]
            )

            task_loss = (
                F.cross_entropy(
                    selected_logits,
                    selected_targets,
                )
            )

        else:
            task = "verifier"

            record = rng.choice(
                verifier_records
            )

            x, label = (
                verifier_example(
                    tokenizer,
                    record,
                    max_length=(
                        args.max_length
                    ),
                    device=device,
                )
            )

            result = model(
                x
            )

            verifier_logits = (
                result.verifier_logits[
                    :,
                    -1,
                    :
                ]
            )

            target = torch.tensor(
                [label],
                dtype=torch.long,
                device=device,
            )

            task_loss = (
                F.cross_entropy(
                    verifier_logits,
                    target,
                    weight=(
                        class_weights
                    ),
                )
            )

        total_loss = (
            task_loss
            + router_regularizer(
                result
            )
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

        accumulators[
            task
        ].append(
            float(
                task_loss.item()
            )
        )

        if (
            step == 1
            or step
            % args.log_every
            == 0
        ):
            def mean(name):
                values = (
                    accumulators[
                        name
                    ]
                )

                if not values:
                    return float(
                        "nan"
                    )

                return (
                    sum(values)
                    / len(values)
                )

            elapsed = (
                time.perf_counter()
                - started
            )

            print(
                f"step={step:6d}",
                f"lm={mean('lm'):.4f}",
                (
                    "semantic="
                    f"{mean('semantic'):.4f}"
                ),
                (
                    "verifier="
                    f"{mean('verifier'):.4f}"
                ),
                (
                    "H="
                    f"{result.router_entropy_normalized.item():.3f}"
                ),
                (
                    "grad="
                    f"{float(gradient_norm):.3f}"
                ),
                (
                    "elapsed="
                    f"{elapsed:.0f}s"
                ),
            )

            accumulators = {
                "lm": [],
                "semantic": [],
                "verifier": [],
            }

        if (
            step
            % args.save_every
            == 0
        ):
            path = (
                output
                / (
                    "cortex-prime-step-"
                    f"{step:06d}.pt"
                )
            )

            digest = save_checkpoint(
                path,
                model=model,
                optimizer=optimizer,
                config=config,
                tokenizer_path=(
                    tokenizer_path
                ),
                base_checkpoint_hash=(
                    base_hash
                ),
                step=step,
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
        / "cortex-prime-final.pt"
    )

    digest = save_checkpoint(
        final_path,
        model=model,
        optimizer=optimizer,
        config=config,
        tokenizer_path=(
            tokenizer_path
        ),
        base_checkpoint_hash=(
            base_hash
        ),
        step=args.steps,
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
