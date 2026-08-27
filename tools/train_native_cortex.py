#!/usr/bin/env python3
"""Train Mega PRIME Native Cortex on provenance-bound prose."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import time

import torch
import torch.nn.functional as F

from core.cortex import (
    ByteTokenizer,
    CortexConfig,
    NativeCortex,
)


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
}


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


def discover_files(
    inputs,
):
    files = []

    for raw in inputs:
        path = Path(
            raw
        )

        if path.is_file():
            files.append(
                path
            )

        elif path.is_dir():
            files.extend(
                candidate
                for candidate
                in path.rglob("*")
                if (
                    candidate.is_file()
                    and candidate.suffix.lower()
                    in TEXT_EXTENSIONS
                )
            )

        else:
            raise FileNotFoundError(
                path
            )

    unique = sorted(
        {
            path.resolve()
            for path in files
        }
    )

    if not unique:
        raise RuntimeError(
            "no prose files discovered"
        )

    return unique


def build_corpus(
    paths,
    tokenizer,
):
    tokens = []

    provenance = []

    for path in paths:
        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        encoded = (
            tokenizer.encode(
                text,
                add_bos=True,
                add_eos=True,
            )
        )

        tokens.extend(
            encoded
        )

        provenance.append(
            {
                "path": str(
                    path
                ),
                "sha256": (
                    sha256_file(
                        path
                    )
                ),
                "characters": (
                    len(text)
                ),
                "tokens": (
                    len(encoded)
                ),
            }
        )

    return (
        torch.tensor(
            tokens,
            dtype=torch.long,
        ),
        provenance,
    )


def sample_batch(
    corpus,
    *,
    batch_size,
    sequence_length,
    generator,
    device,
):
    maximum = (
        corpus.numel()
        - sequence_length
        - 1
    )

    if maximum <= 0:
        raise RuntimeError(
            "corpus smaller than one sequence"
        )

    starts = torch.randint(
        0,
        maximum,
        (
            batch_size,
        ),
        generator=generator,
    )

    offsets = torch.arange(
        sequence_length + 1
    )

    indices = (
        starts[:, None]
        + offsets[None, :]
    )

    batch = corpus[
        indices
    ].to(
        device
    )

    return (
        batch[
            :,
            :-1,
        ],
        batch[
            :,
            1:,
        ],
    )


def save_checkpoint(
    path,
    *,
    model,
    optimizer,
    config,
    step,
    provenance,
):
    payload = {
        "format": (
            "mega-prime-native-cortex-v0"
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
        "provenance": (
            provenance
        ),
    }

    torch.save(
        payload,
        path,
    )

    digest = sha256_file(
        Path(
            path
        )
    )

    Path(
        str(path)
        + ".sha256"
    ).write_text(
        (
            f"{digest}  "
            f"{Path(path).name}\n"
        ),
        encoding="utf-8",
    )

    return digest


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--paths",
        nargs="+",
        required=True,
    )

    parser.add_argument(
        "--output",
        default=(
            "artifacts/native_cortex"
        ),
    )

    parser.add_argument(
        "--steps",
        type=int,
        default=1000,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
    )

    parser.add_argument(
        "--sequence-length",
        type=int,
        default=96,
    )

    parser.add_argument(
        "--learning-rate",
        type=float,
        default=3e-4,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=260001,
    )

    parser.add_argument(
        "--log-every",
        type=int,
        default=25,
    )

    parser.add_argument(
        "--save-every",
        type=int,
        default=250,
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

    random.seed(
        args.seed
    )

    torch.manual_seed(
        args.seed
    )

    if (
        torch.cuda.is_available()
        and args.device.startswith(
            "cuda"
        )
    ):
        torch.cuda.manual_seed_all(
            args.seed
        )

    tokenizer = (
        ByteTokenizer()
    )

    paths = discover_files(
        args.paths
    )

    corpus, provenance = (
        build_corpus(
            paths,
            tokenizer,
        )
    )

    output = Path(
        args.output
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    (
        output
        / "provenance.json"
    ).write_text(
        json.dumps(
            provenance,
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
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

    optimizer = (
        torch.optim.AdamW(
            model.parameters(),
            lr=(
                args.learning_rate
            ),
            weight_decay=0.01,
        )
    )

    generator = (
        torch.Generator(
            device="cpu"
        )
    )

    generator.manual_seed(
        args.seed
    )

    telemetry_path = (
        output
        / "training_telemetry.jsonl"
    )

    print(
        "device:",
        args.device,
    )

    print(
        "files:",
        len(paths),
    )

    print(
        "corpus tokens:",
        corpus.numel(),
    )

    print(
        "parameters:",
        model.parameter_count(),
    )

    print(
        "effective architecture:",
        (
            "ternary-delta-recurrent-"
            "sparse-moe"
        ),
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
            corpus,
            batch_size=(
                args.batch_size
            ),
            sequence_length=(
                args.sequence_length
            ),
            generator=generator,
            device=(
                args.device
            ),
        )

        optimizer.zero_grad(
            set_to_none=True
        )

        output_batch = model(
            x
        )

        language_loss = (
            F.cross_entropy(
                output_batch.logits.reshape(
                    -1,
                    tokenizer.vocab_size,
                ),
                y.reshape(
                    -1
                ),
            )
        )

        auxiliary_loss = (
            output_batch.auxiliary_loss
        )

        loss = (
            language_loss
            + 0.01
            * auxiliary_loss
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
            step
            % args.log_every
            == 0
            or step == 1
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

            with torch.no_grad():
                probe = model(
                    x[
                        :1,
                        :min(
                            16,
                            x.shape[1],
                        ),
                    ],
                    telemetry=True,
                )

            last_layers = (
                probe.telemetry[
                    -1
                ]
            )

            telemetry_row = {
                "step": step,
                "language_loss": (
                    float(
                        language_loss
                        .detach()
                        .cpu()
                        .item()
                    )
                ),
                "auxiliary_loss": (
                    float(
                        auxiliary_loss
                        .detach()
                        .cpu()
                        .item()
                    )
                ),
                "tokens_per_second": (
                    tokens_per_second
                ),
                "layers": [
                    {
                        "layer": (
                            row.layer
                        ),
                        "state_norm": (
                            row.recurrent_state_norm
                        ),
                        "read_norm": (
                            row.read_norm
                        ),
                        "erase_mean": (
                            row.erase_mean
                        ),
                        "write_mean": (
                            row.write_mean
                        ),
                        "expert": (
                            row.selected_expert
                        ),
                        "expert_probability": (
                            row.expert_probability
                        ),
                    }
                    for row in (
                        last_layers
                    )
                ],
            }

            with telemetry_path.open(
                "a",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    json.dumps(
                        telemetry_row,
                        sort_keys=True,
                    )
                )

                handle.write(
                    "\n"
                )

            print(
                f"step={step:6d}",
                (
                    f"loss="
                    f"{language_loss.item():.4f}"
                ),
                (
                    f"moe="
                    f"{auxiliary_loss.item():.4f}"
                ),
                (
                    f"tok/s="
                    f"{tokens_per_second:.0f}"
                ),
            )

            interval_start = (
                now
            )

            interval_tokens = 0

        if (
            step
            % args.save_every
            == 0
        ):
            checkpoint = (
                output
                / (
                    f"cortex-step-"
                    f"{step:06d}.pt"
                )
            )

            digest = (
                save_checkpoint(
                    checkpoint,
                    model=model,
                    optimizer=optimizer,
                    config=config,
                    step=step,
                    provenance=(
                        provenance
                    ),
                )
            )

            print(
                "checkpoint:",
                checkpoint,
            )

            print(
                "sha256:",
                digest,
            )

    final_path = (
        output
        / "cortex-final.pt"
    )

    digest = save_checkpoint(
        final_path,
        model=model,
        optimizer=optimizer,
        config=config,
        step=args.steps,
        provenance=provenance,
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
