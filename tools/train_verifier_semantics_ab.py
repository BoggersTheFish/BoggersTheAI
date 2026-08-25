#!/usr/bin/env python3
"""Controlled A/B verifier-semantics training for PRIME Native Cortex.

Condition A:
    frozen original verifier curriculum

Condition B:
    matched counterfactual verifier curriculum

Everything else is held constant.

The cortex has authority NONE.
HELDOUT IS FORBIDDEN.
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


CONDITIONS = {
    "exposure_control": {
        "verifier": (
            "data/native_cortex/"
            "prime_bridge/curriculum/"
            "train.jsonl"
        ),
        "expected_sha256": (
            "09a08d5924c7f0616d16beecce6c75f03e52ce6cfe100afa3f00c2d9cf4c6516"
        ),
    },
    "counterfactual_paired": {
        "verifier": (
            "data/native_cortex/"
            "verifier_semantics/"
            "counterfactual_v1/"
            "train.jsonl"
        ),
        "expected_sha256": (
            "b7ebab7b3b8bcee3a476a7a13cc41e356b2e25ba8c6f2c15b2c83e7994252025"
        ),
    },
}

EXPECTED_BASE_SHA256 = (
    "aa1119618e4668de79dce8d783a016d5699bd53df3232b0cffbada6938a59ca1"
)

EXPECTED_SEMANTIC_SHA256 = (
    "4f0bd8a514a6160a466c52ab719f9035d29777558faecbcc7feb161c36336d4b"
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


def load_jsonl(path: Path):
    with path.open(
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

    tokens = prefix + target

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
        len(prefix) - 1
    )

    mask[
        :,
        first_target_prediction:
    ] = True

    return x, y, mask


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

    return x, label


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
    condition,
    verifier_curriculum_hash,
    step,
):
    torch.save(
        {
            "format": (
                "mega-prime-verifier-"
                "semantics-ab-v1"
            ),
            "condition": condition,
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
            "verifier_curriculum_sha256": (
                verifier_curriculum_hash
            ),
            "authority": "NONE",
        },
        path,
    )

    return sha256_file(
        path
    )


def task_for_step(step: int) -> str:
    slot = (
        step - 1
    ) % 10

    if slot < 3:
        return "lm"

    if slot < 5:
        return "semantic"

    return "verifier"


def planned_counts(
    steps: int,
    verifier_batch_size: int,
):
    counts = Counter(
        task_for_step(step)
        for step in range(
            1,
            steps + 1,
        )
    )

    return {
        "optimizer_steps": steps,
        "lm_optimizer_steps": (
            counts["lm"]
        ),
        "semantic_optimizer_steps": (
            counts["semantic"]
        ),
        "verifier_optimizer_steps": (
            counts["verifier"]
        ),
        "verifier_batch_size": (
            verifier_batch_size
        ),
        "verifier_presentations": (
            counts["verifier"]
            * verifier_batch_size
        ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--condition",
        required=True,
        choices=sorted(
            CONDITIONS
        ),
    )

    parser.add_argument(
        "--checkpoint",
        default=(
            "artifacts/native_cortex/"
            "prime-bridge-v1/"
            "cortex-prime-final.pt"
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
        "--lm-stream",
        default=(
            "data/native_cortex/"
            "tokens/train.bin"
        ),
    )

    parser.add_argument(
        "--input-lock",
        default=(
            "docs/native_cortex/"
            "verifier_semantics/"
            "AB_INPUTS.json"
        ),
    )

    parser.add_argument(
        "--output-root",
        default=(
            "artifacts/native_cortex/"
            "verifier-semantics-ab-v1"
        ),
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--verifier-batch-size",
        type=int,
        default=5,
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
        default=26082511,
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
        "--dry-run",
        action="store_true",
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

    if args.steps % 10 != 0:
        raise RuntimeError(
            "steps must be divisible by 10"
        )

    condition = CONDITIONS[
        args.condition
    ]

    verifier_path = Path(
        condition["verifier"]
    )

    semantic_path = Path(
        args.semantic
    )

    checkpoint_path = Path(
        args.checkpoint
    )

    lm_path = Path(
        args.lm_stream
    )

    input_lock_path = Path(
        args.input_lock
    )

    for path in (
        verifier_path,
        semantic_path,
        checkpoint_path,
        lm_path,
        input_lock_path,
    ):
        if "heldout" in str(
            path
        ).lower():
            raise RuntimeError(
                "HELDOUT ACCESS FORBIDDEN"
            )

        if not path.exists():
            raise RuntimeError(
                f"missing required input: {path}"
            )

    input_lock = json.loads(
        input_lock_path.read_text(
            encoding="utf-8"
        )
    )

    base_hash = sha256_file(
        checkpoint_path
    )

    semantic_hash = sha256_file(
        semantic_path
    )

    verifier_hash = sha256_file(
        verifier_path
    )

    lm_hash = sha256_file(
        lm_path
    )

    if (
        base_hash
        != EXPECTED_BASE_SHA256
    ):
        raise RuntimeError(
            "base checkpoint hash mismatch: "
            + base_hash
        )

    if (
        semantic_hash
        != EXPECTED_SEMANTIC_SHA256
    ):
        raise RuntimeError(
            "semantic stream hash mismatch: "
            + semantic_hash
        )

    if (
        verifier_hash
        != condition[
            "expected_sha256"
        ]
    ):
        raise RuntimeError(
            "verifier curriculum hash mismatch: "
            + verifier_hash
        )

    locked_lm_hash = (
        input_lock[
            "lm_stream_sha256"
        ]
    )

    if lm_hash != locked_lm_hash:
        raise RuntimeError(
            "LM stream differs from "
            "frozen A/B input lock: "
            + lm_hash
        )

    verifier_records = load_jsonl(
        verifier_path
    )

    semantic_records = load_jsonl(
        semantic_path
    )

    if not verifier_records:
        raise RuntimeError(
            "empty verifier curriculum"
        )

    if not semantic_records:
        raise RuntimeError(
            "empty semantic supervision"
        )

    label_counts = Counter(
        int(
            row[
                "verifier_label_id"
            ]
        )
        for row in verifier_records
    )

    expected_labels = set(
        range(
            len(
                VERIFIER_LABELS
            )
        )
    )

    if set(
        label_counts
    ) != expected_labels:
        raise RuntimeError(
            "curriculum does not contain "
            "all five verifier labels"
        )

    plan = planned_counts(
        args.steps,
        args.verifier_batch_size,
    )

    if (
        plan[
            "verifier_presentations"
        ]
        != len(
            verifier_records
        )
    ):
        raise RuntimeError(
            "Stage-1 protocol requires "
            "exactly one full verifier "
            "curriculum presentation: "
            f"planned="
            f"{plan['verifier_presentations']} "
            f"records="
            f"{len(verifier_records)}"
        )

    print("=" * 92)
    print(
        "MEGA PRIME — VERIFIER SEMANTICS A/B"
    )
    print("=" * 92)

    print(
        "condition:",
        args.condition,
    )

    print(
        "device:",
        args.device,
    )

    print(
        "base checkpoint:",
        base_hash,
    )

    print(
        "semantic sha256:",
        semantic_hash,
    )

    print(
        "LM stream sha256:",
        lm_hash,
    )

    print(
        "verifier curriculum:",
        verifier_path,
    )

    print(
        "verifier sha256:",
        verifier_hash,
    )

    print(
        "verifier records:",
        len(
            verifier_records
        ),
    )

    print(
        "verifier labels:",
        {
            VERIFIER_LABELS[
                index
            ]:
            label_counts[index]
            for index
            in range(
                len(
                    VERIFIER_LABELS
                )
            )
        },
    )

    print(
        "plan:",
        plan,
    )

    print(
        "task schedule:",
        "30% LM / 20% semantic / "
        "50% verifier optimizer steps",
    )

    print(
        "verifier sampling:",
        "deterministic shuffled "
        "without replacement",
    )

    print(
        "optimizer:",
        "continued AdamW state "
        "from frozen bridge checkpoint",
    )

    print(
        "authority:",
        "NONE",
    )

    if args.dry_run:
        print(
            "DRY RUN: validation passed; "
            "no model training performed."
        )
        print("=" * 92)
        return

    random.seed(
        args.seed
    )

    torch.manual_seed(
        args.seed
    )

    rng_main = random.Random(
        args.seed
    )

    rng_verifier = random.Random(
        args.seed + 1
    )

    checkpoint = torch.load(
        checkpoint_path,
        map_location=args.device,
        weights_only=False,
    )

    config = CortexV1Config(
        **checkpoint["config"]
    )

    tokenizer_path = Path(
        checkpoint["tokenizer"]
    )

    tokenizer = BPETokenizer(
        str(
            tokenizer_path
        )
    )

    model = NativeCortexV1(
        config
    ).to(
        args.device
    )

    model.load_state_dict(
        checkpoint["model"]
    )

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        betas=(0.9, 0.95),
        weight_decay=0.01,
    )

    if "optimizer" not in checkpoint:
        raise RuntimeError(
            "base checkpoint has no "
            "optimizer state"
        )

    optimizer.load_state_dict(
        checkpoint["optimizer"]
    )

    for group in (
        optimizer.param_groups
    ):
        group["lr"] = (
            args.learning_rate
        )

    stream = np.memmap(
        lm_path,
        dtype=np.uint16,
        mode="r",
    )

    verifier_order = list(
        range(
            len(
                verifier_records
            )
        )
    )

    rng_verifier.shuffle(
        verifier_order
    )

    verifier_cursor = 0

    output = (
        Path(
            args.output_root
        )
        / args.condition
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    model.train()

    accumulators = {
        "lm": [],
        "semantic": [],
        "verifier": [],
    }

    total_task_counts = Counter()

    verifier_label_presentations = (
        Counter()
    )

    verifier_record_hashes_seen = set()

    started = time.perf_counter()

    for step in range(
        1,
        args.steps + 1,
    ):
        task = task_for_step(
            step
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        if task == "lm":
            x, y = lm_batch(
                stream,
                batch_size=2,
                sequence_length=128,
                rng=rng_main,
                device=args.device,
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

            total_loss = (
                task_loss
                + router_regularizer(
                    result
                )
            )

            total_loss.backward()

            raw_task_loss = float(
                task_loss.item()
            )

        elif task == "semantic":
            example = None
            attempts = 0

            while example is None:
                attempts += 1

                if attempts > 100:
                    raise RuntimeError(
                        "could not construct "
                        "semantic example"
                    )

                record = rng_main.choice(
                    semantic_records
                )

                example = semantic_example(
                    tokenizer,
                    record,
                    max_length=(
                        args.max_length
                    ),
                    device=args.device,
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

            total_loss = (
                task_loss
                + router_regularizer(
                    result
                )
            )

            total_loss.backward()

            raw_task_loss = float(
                task_loss.item()
            )

        else:
            batch_losses = []

            for _ in range(
                args.verifier_batch_size
            ):
                if (
                    verifier_cursor
                    >= len(
                        verifier_order
                    )
                ):
                    raise RuntimeError(
                        "verifier curriculum "
                        "exhausted before "
                        "protocol completion"
                    )

                record_index = (
                    verifier_order[
                        verifier_cursor
                    ]
                )

                verifier_cursor += 1

                record = (
                    verifier_records[
                        record_index
                    ]
                )

                x, label = (
                    verifier_example(
                        tokenizer,
                        record,
                        max_length=(
                            args.max_length
                        ),
                        device=args.device,
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
                    device=args.device,
                )

                one_loss = (
                    F.cross_entropy(
                        verifier_logits,
                        target,
                    )
                )

                scaled_loss = (
                    one_loss
                    + router_regularizer(
                        result
                    )
                ) / (
                    args.verifier_batch_size
                )

                scaled_loss.backward()

                batch_losses.append(
                    float(
                        one_loss.item()
                    )
                )

                verifier_label_presentations[
                    VERIFIER_LABELS[
                        label
                    ]
                ] += 1

                record_hash = record.get(
                    "record_hash",
                    f"index:{record_index}",
                )

                verifier_record_hashes_seen.add(
                    record_hash
                )

            raw_task_loss = (
                sum(
                    batch_losses
                )
                / len(
                    batch_losses
                )
            )

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
            raw_task_loss
        )

        total_task_counts[
            task
        ] += 1

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
                f"step={step:04d} "
                f"task={task:8s} "
                f"lm={mean('lm'):.4f} "
                f"semantic="
                f"{mean('semantic'):.4f} "
                f"verifier="
                f"{mean('verifier'):.4f} "
                f"grad="
                f"{float(gradient_norm):.4f} "
                f"verifier_seen="
                f"{verifier_cursor}/"
                f"{len(verifier_records)} "
                f"elapsed="
                f"{elapsed:.1f}s"
            )

            for key in (
                accumulators
            ):
                accumulators[
                    key
                ].clear()

        if (
            step
            % args.save_every
            == 0
        ):
            checkpoint_out = (
                output
                / (
                    "cortex-step-"
                    f"{step:06d}.pt"
                )
            )

            checkpoint_hash = (
                save_checkpoint(
                    checkpoint_out,
                    model=model,
                    optimizer=optimizer,
                    config=config,
                    tokenizer_path=(
                        tokenizer_path
                    ),
                    base_checkpoint_hash=(
                        base_hash
                    ),
                    condition=(
                        args.condition
                    ),
                    verifier_curriculum_hash=(
                        verifier_hash
                    ),
                    step=step,
                )
            )

            print(
                "checkpoint:",
                checkpoint_out,
            )

            print(
                "checkpoint sha256:",
                checkpoint_hash,
            )

    if (
        verifier_cursor
        != len(
            verifier_records
        )
    ):
        raise RuntimeError(
            "Stage-1 verifier coverage "
            "did not finish exactly one "
            "curriculum epoch: "
            f"{verifier_cursor}/"
            f"{len(verifier_records)}"
        )

    if (
        len(
            verifier_record_hashes_seen
        )
        != len(
            verifier_records
        )
    ):
        raise RuntimeError(
            "verifier record coverage "
            "was not unique: "
            f"{len(verifier_record_hashes_seen)} "
            f"unique of "
            f"{len(verifier_records)}"
        )

    final_path = (
        output
        / "cortex-final.pt"
    )

    final_hash = save_checkpoint(
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
        condition=args.condition,
        verifier_curriculum_hash=(
            verifier_hash
        ),
        step=args.steps,
    )

    elapsed = (
        time.perf_counter()
        - started
    )

    manifest = {
        "format": (
            "mega-prime-verifier-"
            "semantics-ab-training-v1"
        ),
        "condition": (
            args.condition
        ),
        "authority": "NONE",
        "seed": args.seed,
        "steps": args.steps,
        "schedule": (
            "30% LM / 20% semantic / "
            "50% verifier optimizer steps"
        ),
        "verifier_batch_size": (
            args.verifier_batch_size
        ),
        "base_checkpoint": str(
            checkpoint_path
        ),
        "base_checkpoint_sha256": (
            base_hash
        ),
        "semantic_path": str(
            semantic_path
        ),
        "semantic_sha256": (
            semantic_hash
        ),
        "lm_stream": str(
            lm_path
        ),
        "lm_stream_sha256": (
            lm_hash
        ),
        "verifier_curriculum": str(
            verifier_path
        ),
        "verifier_curriculum_sha256": (
            verifier_hash
        ),
        "verifier_records": len(
            verifier_records
        ),
        "verifier_presentations": (
            verifier_cursor
        ),
        "unique_verifier_records_seen": (
            len(
                verifier_record_hashes_seen
            )
        ),
        "verifier_label_presentations": (
            dict(
                sorted(
                    verifier_label_presentations.items()
                )
            )
        ),
        "optimizer_task_counts": (
            dict(
                sorted(
                    total_task_counts.items()
                )
            )
        ),
        "optimizer_state_continued": (
            True
        ),
        "learning_rate": (
            args.learning_rate
        ),
        "max_length": (
            args.max_length
        ),
        "final_checkpoint": str(
            final_path
        ),
        "final_checkpoint_sha256": (
            final_hash
        ),
        "elapsed_seconds": (
            elapsed
        ),
    }

    manifest_path = (
        output
        / "TRAINING_MANIFEST.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 92)
    print(
        "A/B CONDITION COMPLETE"
    )
    print("=" * 92)

    print(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
