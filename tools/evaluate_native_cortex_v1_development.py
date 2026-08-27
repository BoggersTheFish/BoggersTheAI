#!/usr/bin/env python3
"""Development-only evaluator for Mega PRIME Native Cortex V1."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
import torch.nn.functional as F

from core.cortex import (
    BPETokenizer,
    CortexV1Config,
    NativeCortexV1,
)


def empty_layer_stats(
    layers,
    experts,
):
    return [
        {
            "expert_counts": [
                0
                for _ in range(
                    experts
                )
            ],
            "router_confidence_sum": 0.0,
            "router_entropy_sum": 0.0,
            "state_norm_sum": 0.0,
            "read_norm_sum": 0.0,
            "erase_sum": 0.0,
            "write_sum": 0.0,
            "retention_sum": 0.0,
            "attention_entropy_sum": 0.0,
            "attention_steps": 0,
            "steps": 0,
        }
        for _ in range(
            layers
        )
    ]


def merge_diagnostics(
    totals,
    diagnostics,
):
    for layer_index, row in enumerate(
        diagnostics
    ):
        target = totals[
            layer_index
        ]

        counts = (
            row[
                "expert_counts"
            ].tolist()
        )

        for index, value in enumerate(
            counts
        ):
            target[
                "expert_counts"
            ][index] += int(
                value
            )

        target[
            "router_confidence_sum"
        ] += (
            row[
                "router_confidence_sum"
            ]
        )

        target[
            "router_entropy_sum"
        ] += (
            row[
                "router_entropy_sum"
            ]
        )

        target[
            "state_norm_sum"
        ] += (
            row[
                "state_norm_sum"
            ]
        )

        target[
            "read_norm_sum"
        ] += (
            row[
                "read_norm_sum"
            ]
        )

        target[
            "erase_sum"
        ] += row[
            "erase_sum"
        ]

        target[
            "write_sum"
        ] += row[
            "write_sum"
        ]

        target[
            "retention_sum"
        ] += (
            row[
                "retention_sum"
            ]
        )

        target[
            "attention_entropy_sum"
        ] += (
            row[
                "attention_entropy_sum"
            ]
        )

        target[
            "attention_steps"
        ] += int(
            row[
                "attention_steps"
            ]
        )

        target[
            "steps"
        ] += int(
            row[
                "steps"
            ]
        )


def evaluate_mode(
    model,
    tokenizer,
    development_path,
    *,
    device,
    reset_recurrence,
    disable_attention,
    chunk_length=128,
):
    total_nll = 0.0
    total_tokens = 0
    total_utf8_bytes = 0

    layer_totals = (
        empty_layer_stats(
            model.config.layers,
            model.config.experts,
        )
    )

    with open(
        development_path,
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            record = json.loads(
                line
            )

            text = record[
                "text"
            ]

            total_utf8_bytes += len(
                text.encode(
                    "utf-8"
                )
            )

            ids = tokenizer.encode(
                text,
                add_bos=True,
                add_eos=True,
            )

            if len(ids) < 2:
                continue

            states = None

            for start in range(
                0,
                len(ids) - 1,
                chunk_length,
            ):
                remaining = (
                    len(ids)
                    - 1
                    - start
                )

                take = min(
                    chunk_length,
                    remaining,
                )

                source_ids = ids[
                    start:
                    start + take
                ]

                target_ids = ids[
                    start + 1:
                    start + 1 + take
                ]

                if (
                    len(source_ids)
                    != len(target_ids)
                ):
                    raise RuntimeError(
                        "source/target alignment failure"
                    )

                source = torch.tensor(
                    source_ids,
                    dtype=torch.long,
                    device=device,
                ).unsqueeze(
                    0
                )

                target = torch.tensor(
                    target_ids,
                    dtype=torch.long,
                    device=device,
                ).unsqueeze(
                    0
                )

                result = model(
                    source,
                    states,
                    reset_recurrence=(
                        reset_recurrence
                    ),
                    disable_attention=(
                        disable_attention
                    ),
                    collect_diagnostics=True,
                )

                states = (
                    result.states
                )

                loss = F.cross_entropy(
                    result.logits.reshape(
                        -1,
                        tokenizer.vocab_size,
                    ),
                    target.reshape(
                        -1
                    ),
                    reduction="sum",
                )

                total_nll += float(
                    loss.item()
                )

                total_tokens += (
                    target.numel()
                )

                merge_diagnostics(
                    layer_totals,
                    result.diagnostics,
                )

    mean_nll = (
        total_nll
        / total_tokens
    )

    bits_per_byte = (
        total_nll
        / math.log(2)
        / total_utf8_bytes
    )

    layers = []

    for layer_index, stats in enumerate(
        layer_totals
    ):
        total_assignments = sum(
            stats[
                "expert_counts"
            ]
        )

        shares = [
            (
                count
                / total_assignments
            )
            if total_assignments
            else 0.0
            for count
            in stats[
                "expert_counts"
            ]
        ]

        entropy = -sum(
            p
            * math.log(
                p + 1e-12
            )
            for p in shares
        )

        normalized_entropy = (
            entropy
            / math.log(
                model.config.experts
            )
            if total_assignments
            else 0.0
        )

        steps = max(
            stats[
                "steps"
            ],
            1,
        )

        attention_steps = max(
            stats[
                "attention_steps"
            ],
            1,
        )

        layers.append(
            {
                "layer": (
                    layer_index
                ),
                "expert_shares": (
                    shares
                ),
                "max_expert_share": (
                    max(shares)
                    if shares
                    else 0.0
                ),
                "routing_entropy": (
                    normalized_entropy
                ),
                "router_confidence": (
                    stats[
                        "router_confidence_sum"
                    ]
                    / steps
                ),
                "state_norm": (
                    stats[
                        "state_norm_sum"
                    ]
                    / steps
                ),
                "read_norm": (
                    stats[
                        "read_norm_sum"
                    ]
                    / steps
                ),
                "erase": (
                    stats[
                        "erase_sum"
                    ]
                    / steps
                ),
                "write": (
                    stats[
                        "write_sum"
                    ]
                    / steps
                ),
                "retention": (
                    stats[
                        "retention_sum"
                    ]
                    / steps
                ),
                "attention_entropy": (
                    stats[
                        "attention_entropy_sum"
                    ]
                    / attention_steps
                ),
            }
        )

    return {
        "cross_entropy": (
            mean_nll
        ),
        "perplexity": math.exp(
            min(
                mean_nll,
                50.0,
            )
        ),
        "bits_per_byte": (
            bits_per_byte
        ),
        "tokens": (
            total_tokens
        ),
        "utf8_bytes": (
            total_utf8_bytes
        ),
        "layers": layers,
    }


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
            "splits/development.jsonl"
        ),
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

    if (
        "heldout"
        in Path(
            args.development
        ).name.lower()
    ):
        raise RuntimeError(
            "HELDOUT EVALUATION IS FORBIDDEN"
        )

    checkpoint = torch.load(
        args.checkpoint,
        map_location=args.device,
        weights_only=False,
    )

    config = CortexV1Config(
        **checkpoint[
            "config"
        ]
    )

    tokenizer = BPETokenizer(
        checkpoint[
            "tokenizer"
        ]
    )

    model = NativeCortexV1(
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

    print("=" * 96)
    print(
        "MEGA PRIME — NATIVE CORTEX V1 DEVELOPMENT"
    )
    print("=" * 96)

    print(
        "parameters:",
        f"{model.parameter_count():,}",
    )

    print(
        "authority:",
        "NONE",
    )

    modes = {
        "NORMAL": (
            False,
            False,
        ),
        "RESET_RECURRENCE": (
            True,
            False,
        ),
        "NO_LOCAL_ATTENTION": (
            False,
            True,
        ),
    }

    results = {}

    with torch.no_grad():
        for name, (
            reset,
            no_attention,
        ) in modes.items():
            print()
            print(
                "running:",
                name,
            )

            results[name] = (
                evaluate_mode(
                    model,
                    tokenizer,
                    args.development,
                    device=args.device,
                    reset_recurrence=(
                        reset
                    ),
                    disable_attention=(
                        no_attention
                    ),
                )
            )

    print()
    print("=== LANGUAGE ===")

    for name, result in (
        results.items()
    ):
        print(
            f"{name:20s}",
            (
                f"CE="
                f"{result['cross_entropy']:.4f}"
            ),
            (
                f"PPL="
                f"{result['perplexity']:.2f}"
            ),
            (
                f"BPB="
                f"{result['bits_per_byte']:.4f}"
            ),
        )

    normal = results[
        "NORMAL"
    ]

    print()
    print(
        "RECURRENT BPB CONTRIBUTION:",
        (
            f"{results['RESET_RECURRENCE']['bits_per_byte'] - normal['bits_per_byte']:+.4f}"
        ),
    )

    print(
        "LOCAL ATTENTION BPB CONTRIBUTION:",
        (
            f"{results['NO_LOCAL_ATTENTION']['bits_per_byte'] - normal['bits_per_byte']:+.4f}"
        ),
    )

    print()
    print(
        "=== NORMAL ROUTING / MEMORY ==="
    )

    for row in normal[
        "layers"
    ]:
        print(
            f"L{row['layer']}",
            (
                "experts="
                + ",".join(
                    f"{value:.3f}"
                    for value
                    in row[
                        "expert_shares"
                    ]
                )
            ),
            (
                f"max="
                f"{row['max_expert_share']:.3f}"
            ),
            (
                f"H="
                f"{row['routing_entropy']:.3f}"
            ),
            (
                f"conf="
                f"{row['router_confidence']:.3f}"
            ),
            (
                f"state="
                f"{row['state_norm']:.3f}"
            ),
            (
                f"read="
                f"{row['read_norm']:.3f}"
            ),
            (
                f"erase="
                f"{row['erase']:.4f}"
            ),
            (
                f"write="
                f"{row['write']:.4f}"
            ),
            (
                f"retain="
                f"{row['retention']:.4f}"
            ),
            (
                f"attnH="
                f"{row['attention_entropy']:.3f}"
            ),
        )

    print()
    print("=" * 96)


if __name__ == "__main__":
    main()
