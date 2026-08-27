#!/usr/bin/env python3
"""Development-only counterfactual verifier-semantics evaluation.

Measures ordinary five-way performance plus matched ACCEPT/REJECT
pair discrimination and score-margin reversal.

The neural cortex has authority NONE.

HELDOUT IS FORBIDDEN.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
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


ACCEPT_ID = VERIFIER_LABELS.index(
    "ACCEPT"
)

REJECT_ID = VERIFIER_LABELS.index(
    "REJECT"
)

REQUIRED_CHANNELS = (
    "arithmetic",
    "structural",
    "code_property",
)


def sha256_file(
    path: Path,
):
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


def stable_token_hash(
    ids,
):
    digest = hashlib.sha256()

    for token_id in ids:
        digest.update(
            int(token_id).to_bytes(
                4,
                "big",
                signed=False,
            )
        )

    return digest.hexdigest()


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
            "verifier_semantics/"
            "counterfactual_v1/"
            "development.jsonl"
        ),
    )

    parser.add_argument(
        "--max-length",
        type=int,
        default=192,
    )

    parser.add_argument(
        "--output-json",
        default="",
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
    prediction_counts = Counter()

    channel_ar_total = Counter()
    channel_ar_correct = Counter()

    pair_members = defaultdict(
        dict
    )

    total = 0
    correct = 0

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

                full_ids = tokenizer.encode(
                    prompt,
                    add_bos=True,
                    add_eos=True,
                )

                ids = full_ids[
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

                probabilities = (
                    torch.softmax(
                        logits,
                        dim=-1,
                    )
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

                is_correct = (
                    prediction
                    == target
                )

                if is_correct:
                    correct += 1

                    class_correct[
                        target
                    ] += 1

                target_label = (
                    VERIFIER_LABELS[
                        target
                    ]
                )

                channel = str(
                    record.get(
                        "verifier_type",
                        "unknown",
                    )
                )

                if target_label in {
                    "ACCEPT",
                    "REJECT",
                }:
                    channel_ar_total[
                        channel
                    ] += 1

                    if is_correct:
                        channel_ar_correct[
                            channel
                        ] += 1

                pair_id = record.get(
                    "pair_id"
                )

                pair_member = record.get(
                    "pair_member"
                )

                if (
                    record.get(
                        "counterfactual_pair"
                    )
                    and pair_id
                    and pair_member
                    in {
                        "ACCEPT",
                        "REJECT",
                    }
                ):
                    margin = float(
                        probabilities[
                            ACCEPT_ID
                        ].item()
                        - probabilities[
                            REJECT_ID
                        ].item()
                    )

                    pair_members[
                        pair_id
                    ][
                        pair_member
                    ] = {
                        "prediction": (
                            VERIFIER_LABELS[
                                prediction
                            ]
                        ),
                        "target": (
                            target_label
                        ),
                        "channel": channel,
                        "margin": margin,
                        "prompt": prompt,
                        "full_token_hash": (
                            stable_token_hash(
                                full_ids
                            )
                        ),
                        "truncated_token_hash": (
                            stable_token_hash(
                                ids
                            )
                        ),
                    }

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

        per_class[label] = (
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

    channel_ar_accuracy = {}

    for channel in REQUIRED_CHANNELS:
        denominator = (
            channel_ar_total[
                channel
            ]
        )

        channel_ar_accuracy[
            channel
        ] = (
            channel_ar_correct[
                channel
            ]
            / denominator
            if denominator
            else 0.0
        )

    pair_total = 0
    pair_correct = 0
    margin_reversal_count = 0

    accept_margins = []
    reject_margins = []
    margin_flips = []

    pair_channel_total = Counter()
    pair_channel_correct = Counter()

    full_prompt_collisions = 0
    truncated_token_collisions = 0
    malformed_pairs = 0

    for pair_id, members in (
        pair_members.items()
    ):
        if set(
            members
        ) != {
            "ACCEPT",
            "REJECT",
        }:
            malformed_pairs += 1
            continue

        positive = members[
            "ACCEPT"
        ]

        negative = members[
            "REJECT"
        ]

        if (
            positive["channel"]
            != negative["channel"]
        ):
            malformed_pairs += 1
            continue

        channel = positive[
            "channel"
        ]

        pair_total += 1

        pair_channel_total[
            channel
        ] += 1

        both_correct = (
            positive[
                "prediction"
            ]
            == "ACCEPT"
            and
            negative[
                "prediction"
            ]
            == "REJECT"
        )

        if both_correct:
            pair_correct += 1

            pair_channel_correct[
                channel
            ] += 1

        positive_margin = (
            positive[
                "margin"
            ]
        )

        negative_margin = (
            negative[
                "margin"
            ]
        )

        accept_margins.append(
            positive_margin
        )

        reject_margins.append(
            negative_margin
        )

        margin_flips.append(
            positive_margin
            - negative_margin
        )

        if (
            positive_margin > 0.0
            and
            negative_margin < 0.0
        ):
            margin_reversal_count += 1

        if (
            positive["prompt"]
            == negative["prompt"]
        ):
            full_prompt_collisions += 1

        if (
            positive[
                "truncated_token_hash"
            ]
            == negative[
                "truncated_token_hash"
            ]
        ):
            truncated_token_collisions += 1

    pair_accuracy = (
        pair_correct / pair_total
        if pair_total
        else 0.0
    )

    margin_reversal_rate = (
        margin_reversal_count
        / pair_total
        if pair_total
        else 0.0
    )

    mean_accept_margin = (
        sum(accept_margins)
        / len(accept_margins)
        if accept_margins
        else 0.0
    )

    mean_reject_margin = (
        sum(reject_margins)
        / len(reject_margins)
        if reject_margins
        else 0.0
    )

    mean_margin_flip = (
        sum(margin_flips)
        / len(margin_flips)
        if margin_flips
        else 0.0
    )

    pair_channel_accuracy = {}

    for channel in REQUIRED_CHANNELS:
        denominator = (
            pair_channel_total[
                channel
            ]
        )

        pair_channel_accuracy[
            channel
        ] = (
            pair_channel_correct[
                channel
            ]
            / denominator
            if denominator
            else 0.0
        )

    gates = {
        "overall_gt_0_60": (
            accuracy > 0.60
        ),
        "macro_gt_0_60": (
            macro_accuracy > 0.60
        ),
        "minimum_class_gt_0_35": (
            minimum_class_accuracy
            > 0.35
        ),
        "accept_gt_0_60": (
            per_class[
                "ACCEPT"
            ] > 0.60
        ),
        "reject_gt_0_60": (
            per_class[
                "REJECT"
            ] > 0.60
        ),
        "pair_accuracy_gt_0_50": (
            pair_accuracy > 0.50
        ),
        "margin_reversal_gt_0_50": (
            margin_reversal_rate
            > 0.50
        ),
        "all_channel_ar_gt_0_60": all(
            channel_ar_accuracy[
                channel
            ] > 0.60
            for channel
            in REQUIRED_CHANNELS
        ),
        "no_full_prompt_collisions": (
            full_prompt_collisions == 0
        ),
        "no_truncated_token_collisions": (
            truncated_token_collisions
            == 0
        ),
        "no_malformed_pairs": (
            malformed_pairs == 0
        ),
    }

    full_gate = all(
        gates.values()
    )

    summary = {
        "format": (
            "mega-prime-counterfactual-"
            "verifier-development-v1"
        ),
        "authority": "NONE",
        "checkpoint": str(
            checkpoint_path
        ),
        "checkpoint_sha256": (
            sha256_file(
                checkpoint_path
            )
        ),
        "checkpoint_format": (
            checkpoint.get(
                "format",
                "unknown",
            )
        ),
        "development": str(
            development_path
        ),
        "development_sha256": (
            sha256_file(
                development_path
            )
        ),
        "records": total,
        "accuracy": accuracy,
        "macro_accuracy": (
            macro_accuracy
        ),
        "minimum_class_accuracy": (
            minimum_class_accuracy
        ),
        "per_class": per_class,
        "prediction_counts": {
            VERIFIER_LABELS[index]: (
                prediction_counts[
                    index
                ]
            )
            for index in range(
                label_count
            )
        },
        "channel_accept_reject_accuracy": (
            channel_ar_accuracy
        ),
        "pairs": pair_total,
        "pair_accuracy": pair_accuracy,
        "pair_channel_accuracy": (
            pair_channel_accuracy
        ),
        "mean_accept_margin": (
            mean_accept_margin
        ),
        "mean_reject_margin": (
            mean_reject_margin
        ),
        "mean_margin_flip": (
            mean_margin_flip
        ),
        "margin_reversal_rate": (
            margin_reversal_rate
        ),
        "full_prompt_collisions": (
            full_prompt_collisions
        ),
        "truncated_token_collisions": (
            truncated_token_collisions
        ),
        "malformed_pairs": (
            malformed_pairs
        ),
        "gates": gates,
        "full_verifier_semantics_gate": (
            full_gate
        ),
        "confusion": confusion,
    }

    print("=" * 92)
    print(
        "MEGA PRIME — COUNTERFACTUAL "
        "VERIFIER SEMANTICS DEVELOPMENT"
    )
    print("=" * 92)

    print(
        "checkpoint:",
        checkpoint_path,
    )

    print(
        "checkpoint sha256:",
        summary[
            "checkpoint_sha256"
        ],
    )

    print(
        "development:",
        development_path,
    )

    print(
        "development sha256:",
        summary[
            "development_sha256"
        ],
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
        "pairs:",
        pair_total,
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

    print("=== PER CLASS ===")

    for label in VERIFIER_LABELS:
        print(
            f"{label:8s}",
            f"{per_class[label]:.4f}",
        )

    print()

    print(
        "=== WITHIN-CHANNEL "
        "ACCEPT/REJECT ==="
    )

    for channel in REQUIRED_CHANNELS:
        print(
            f"{channel:14s}",
            f"{channel_ar_accuracy[channel]:.4f}",
        )

    print()

    print(
        "=== PAIRED SEMANTICS ==="
    )

    print(
        "pair accuracy:",
        f"{pair_accuracy:.4f}",
    )

    print(
        "margin reversal rate:",
        f"{margin_reversal_rate:.4f}",
    )

    print(
        "mean ACCEPT margin:",
        f"{mean_accept_margin:+.6f}",
    )

    print(
        "mean REJECT margin:",
        f"{mean_reject_margin:+.6f}",
    )

    print(
        "mean margin flip:",
        f"{mean_margin_flip:+.6f}",
    )

    print()

    print(
        "pair accuracy by channel:"
    )

    for channel in REQUIRED_CHANNELS:
        print(
            f"{channel:14s}",
            f"{pair_channel_accuracy[channel]:.4f}",
        )

    print()

    print(
        "full prompt collisions:",
        full_prompt_collisions,
    )

    print(
        "truncated token collisions:",
        truncated_token_collisions,
    )

    print(
        "malformed pairs:",
        malformed_pairs,
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
            for label
            in VERIFIER_LABELS
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
                in confusion[index]
            ],
        )

    print()

    print(
        "=== FROZEN SEMANTICS GATES ==="
    )

    for name, passed in (
        gates.items()
    ):
        print(
            f"{name}:",
            passed,
        )

    print()

    print(
        "FULL VERIFIER SEMANTICS GATE:",
        full_gate,
    )

    print("=" * 92)

    if args.output_json:
        output_path = Path(
            args.output_json
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                summary,
                sort_keys=True,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            "result json:",
            output_path,
        )


if __name__ == "__main__":
    main()
