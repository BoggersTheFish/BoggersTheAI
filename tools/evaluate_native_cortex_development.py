#!/usr/bin/env python3
"""Development-only Native Cortex evaluator.

HELDOUT IS EXPLICITLY FORBIDDEN.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
import torch.nn.functional as F

from core.cortex import (
    BPETokenizer,
    CortexConfig,
    NativeCortex,
)


def evaluate(
    model,
    tokenizer,
    path,
    *,
    device,
    reset_every_token,
):
    total_loss = 0.0
    total_tokens = 0
    total_bytes = 0

    expert_counts = [
        [
            0
            for _ in range(
                model.config.experts
            )
        ]
        for _ in range(
            model.config.layers
        )
    ]

    expert_confidence = [
        0.0
        for _ in range(
            model.config.layers
        )
    ]

    gate_erase = [
        0.0
        for _ in range(
            model.config.layers
        )
    ]

    gate_write = [
        0.0
        for _ in range(
            model.config.layers
        )
    ]

    state_norm = [
        0.0
        for _ in range(
            model.config.layers
        )
    ]

    telemetry_steps = 0

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            record = json.loads(line)

            text = record["text"]

            total_bytes += len(
                text.encode("utf-8")
            )

            tokens = tokenizer.encode(
                text,
                add_bos=True,
                add_eos=True,
            )

            if len(tokens) < 2:
                continue

            states = None

            for index in range(
                len(tokens) - 1
            ):
                source = torch.tensor(
                    [tokens[index]],
                    dtype=torch.long,
                    device=device,
                )

                target = torch.tensor(
                    [tokens[index + 1]],
                    dtype=torch.long,
                    device=device,
                )

                if reset_every_token:
                    states = None

                (
                    logits,
                    _,
                    states,
                    _,
                    telemetry,
                ) = model.step(
                    source,
                    states,
                    telemetry=True,
                )

                loss = F.cross_entropy(
                    logits,
                    target,
                    reduction="sum",
                )

                total_loss += float(
                    loss.item()
                )

                total_tokens += 1

                telemetry_steps += 1

                for layer, observation in (
                    enumerate(telemetry)
                ):
                    expert_counts[
                        layer
                    ][
                        observation.selected_expert
                    ] += 1

                    expert_confidence[
                        layer
                    ] += (
                        observation
                        .expert_probability
                    )

                    gate_erase[
                        layer
                    ] += (
                        observation
                        .erase_mean
                    )

                    gate_write[
                        layer
                    ] += (
                        observation
                        .write_mean
                    )

                    state_norm[
                        layer
                    ] += (
                        observation
                        .recurrent_state_norm
                    )

    mean_nll = (
        total_loss
        / total_tokens
    )

    bits_per_byte = (
        total_loss
        / math.log(2)
        / total_bytes
    )

    layers = []

    for layer in range(
        model.config.layers
    ):
        counts = expert_counts[
            layer
        ]

        count_total = sum(
            counts
        )

        probabilities = [
            count / count_total
            for count in counts
        ]

        entropy = -sum(
            p * math.log(
                p + 1e-12
            )
            for p in probabilities
        )

        normalized_entropy = (
            entropy
            / math.log(
                model.config.experts
            )
        )

        layers.append(
            {
                "layer": layer,
                "expert_counts": counts,
                "expert_shares": (
                    probabilities
                ),
                "max_expert_share": (
                    max(probabilities)
                ),
                "routing_entropy_normalized": (
                    normalized_entropy
                ),
                "mean_router_confidence": (
                    expert_confidence[layer]
                    / telemetry_steps
                ),
                "mean_erase": (
                    gate_erase[layer]
                    / telemetry_steps
                ),
                "mean_write": (
                    gate_write[layer]
                    / telemetry_steps
                ),
                "mean_state_norm": (
                    state_norm[layer]
                    / telemetry_steps
                ),
            }
        )

    return {
        "mode": (
            "RESET"
            if reset_every_token
            else "NORMAL"
        ),
        "tokens": total_tokens,
        "utf8_bytes": total_bytes,
        "cross_entropy_nats": (
            mean_nll
        ),
        "perplexity": (
            math.exp(
                min(
                    mean_nll,
                    50.0,
                )
            )
        ),
        "bits_per_byte": (
            bits_per_byte
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
            "data/native_cortex/splits/"
            "development.jsonl"
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

    if "heldout" in (
        Path(
            args.development
        ).name.lower()
    ):
        raise RuntimeError(
            "HELDOUT EVALUATION IS NOT AUTHORIZED"
        )

    checkpoint = torch.load(
        args.checkpoint,
        map_location=args.device,
        weights_only=False,
    )

    config = CortexConfig(
        **checkpoint["config"]
    )

    tokenizer = BPETokenizer(
        checkpoint["tokenizer"]
    )

    model = NativeCortex(
        config
    ).to(
        args.device
    )

    model.load_state_dict(
        checkpoint["model"]
    )

    model.eval()

    print("=" * 90)
    print(
        "MEGA PRIME NATIVE CORTEX — "
        "DEVELOPMENT EVALUATION"
    )
    print("=" * 90)

    print(
        "parameters:",
        f"{model.parameter_count():,}",
    )

    print(
        "vocab:",
        tokenizer.vocab_size,
    )

    print(
        "authority:",
        "NONE",
    )

    with torch.no_grad():
        normal = evaluate(
            model,
            tokenizer,
            args.development,
            device=args.device,
            reset_every_token=False,
        )

        reset = evaluate(
            model,
            tokenizer,
            args.development,
            device=args.device,
            reset_every_token=True,
        )

    print()
    print("=== LANGUAGE GENERALISATION ===")

    for row in (
        normal,
        reset,
    ):
        print(
            f"{row['mode']:7s}",
            (
                f"CE="
                f"{row['cross_entropy_nats']:.4f}"
            ),
            (
                f"PPL="
                f"{row['perplexity']:.2f}"
            ),
            (
                f"BPB="
                f"{row['bits_per_byte']:.4f}"
            ),
        )

    print()
    print(
        "RECURRENT BPB GAIN:",
        (
            f"{reset['bits_per_byte'] - normal['bits_per_byte']:+.4f}"
        ),
    )

    print()
    print("=== ROUTING / MEMORY HEALTH ===")

    for layer in (
        normal["layers"]
    ):
        print(
            f"L{layer['layer']}",
            (
                "experts="
                + ",".join(
                    f"{value:.3f}"
                    for value
                    in layer[
                        "expert_shares"
                    ]
                )
            ),
            (
                f"max="
                f"{layer['max_expert_share']:.3f}"
            ),
            (
                f"H="
                f"{layer['routing_entropy_normalized']:.3f}"
            ),
            (
                f"conf="
                f"{layer['mean_router_confidence']:.3f}"
            ),
            (
                f"erase="
                f"{layer['mean_erase']:.4f}"
            ),
            (
                f"write="
                f"{layer['mean_write']:.4f}"
            ),
            (
                f"state="
                f"{layer['mean_state_norm']:.3f}"
            ),
        )

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()
