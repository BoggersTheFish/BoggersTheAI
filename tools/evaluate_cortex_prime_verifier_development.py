#!/usr/bin/env python3
"""Development-only evaluation of Cortex prediction of PRIME verdicts.

This evaluates whether the neural cortex can predict PRIME's behaviour.
It does not grant the cortex verifier authority.

HELDOUT IS FORBIDDEN.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import torch

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


def load_model(
    checkpoint_path: Path,
    device: str,
):
    checkpoint = torch.load(
        checkpoint_path,
        map_location=device,
        weights_only=False,
    )

    config = CortexV1Config(
        **checkpoint["config"]
    )

    tokenizer = BPETokenizer(
        checkpoint["tokenizer"]
    )

    model = NativeCortexV1(
        config
    ).to(device)

    model.load_state_dict(
        checkpoint["model"]
    )

    model.eval()

    return (
        checkpoint,
        model,
        tokenizer,
    )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--checkpoint",
        required=True,
    )

    parser.add_argument(
        "--development",
        default=(
            "data/native_cortex/"
            "prime_bridge/curriculum/"
            "development.jsonl"
        ),
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=192,
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

    development_path = Path(
        args.development
    )

    if "heldout" in str(
        development_path
    ).lower():
        raise RuntimeError(
            "HELDOUT EVALUATION IS FORBIDDEN"
        )

    checkpoint_path = Path(
        args.checkpoint
    )

    (
        checkpoint,
        model,
        tokenizer,
    ) = load_model(
        checkpoint_path,
        args.device,
    )

    label_count = len(
        VERIFIER_LABELS
    )

    confusion = [
        [
            0
            for _ in range(
                label_count
            )
        ]
        for _ in range(
            label_count
        )
    ]

    class_total = Counter()
    class_correct = Counter()

    total = 0
    correct = 0

    prediction_counts = Counter()

    with torch.no_grad():
        with development_path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line in handle:
                if not line.strip():
                    continue

                record = json.loads(
                    line
                )

                prompt = (
                    format_verifier_prompt(
                        record
                    )
                )

                ids = tokenizer.encode(
                    prompt,
                    add_bos=True,
                    add_eos=True,
                )

                ids = ids[
                    -args.max_length:
                ]

                x = torch.tensor(
                    ids,
                    dtype=torch.long,
                    device=args.device,
                ).unsqueeze(0)

                result = model(
                    x
                )

                logits = (
                    result
                    .verifier_logits[
                        0,
                        -1,
                        :
                    ]
                )

                prediction = int(
                    torch.argmax(
                        logits
                    ).item()
                )

                target = int(
                    record[
                        "verifier_label_id"
                    ]
                )

                if not (
                    0
                    <= target
                    < label_count
                ):
                    raise RuntimeError(
                        "invalid target label"
                    )

                confusion[
                    target
                ][
                    prediction
                ] += 1

                class_total[
                    target
                ] += 1

                prediction_counts[
                    prediction
                ] += 1

                total += 1

                if (
                    prediction
                    == target
                ):
                    correct += 1

                    class_correct[
                        target
                    ] += 1

    accuracy = (
        correct / total
        if total
        else 0.0
    )

    per_class = {}

    for index, label in enumerate(
        VERIFIER_LABELS
    ):
        denominator = (
            class_total[
                index
            ]
        )

        per_class[
            label
        ] = (
            class_correct[index]
            / denominator
            if denominator
            else 0.0
        )

    macro_accuracy = (
        sum(
            per_class.values()
        )
        / label_count
    )

    minimum_class_accuracy = min(
        per_class.values()
    )

    print("=" * 92)
    print(
        "MEGA PRIME — CORTEX PRIME "
        "VERIFIER DEVELOPMENT"
    )
    print("=" * 92)

    print(
        "checkpoint:",
        checkpoint_path,
    )

    print(
        "checkpoint format:",
        checkpoint.get(
            "format",
            "unknown",
        ),
    )

    print(
        "parameters:",
        f"{model.parameter_count():,}",
    )

    print(
        "records:",
        total,
    )

    print(
        "authority:",
        "NONE",
    )

    print()

    print(
        "accuracy:",
        f"{accuracy:.4f}",
    )

    print(
        "macro accuracy:",
        f"{macro_accuracy:.4f}",
    )

    print(
        "minimum class accuracy:",
        f"{minimum_class_accuracy:.4f}",
    )

    print()

    print(
        "=== PER CLASS ==="
    )

    for label in (
        VERIFIER_LABELS
    ):
        print(
            f"{label:8s}",
            f"{per_class[label]:.4f}",
        )

    print()

    print(
        "=== PREDICTION DISTRIBUTION ==="
    )

    for index, label in enumerate(
        VERIFIER_LABELS
    ):
        print(
            f"{label:8s}",
            prediction_counts[
                index
            ],
        )

    print()

    print(
        "=== CONFUSION MATRIX ==="
    )

    print(
        "true\\pred",
        *[
            f"{label[:4]:>5s}"
            for label in VERIFIER_LABELS
        ],
    )

    for index, label in enumerate(
        VERIFIER_LABELS
    ):
        print(
            f"{label[:8]:>8s}",
            *[
                f"{value:5d}"
                for value
                in confusion[
                    index
                ]
            ],
        )

    print()

    chance = (
        1.0 / label_count
    )

    print(
        "balanced chance:",
        f"{chance:.4f}",
    )

    print()

    print(
        "PRE-REGISTERED DEVELOPMENT GATES"
    )

    print(
        "overall > 0.60:",
        accuracy > 0.60,
    )

    print(
        "macro > 0.60:",
        macro_accuracy > 0.60,
    )

    print(
        "every class > 0.35:",
        minimum_class_accuracy > 0.35,
    )

    print("=" * 92)


if __name__ == "__main__":
    main()
