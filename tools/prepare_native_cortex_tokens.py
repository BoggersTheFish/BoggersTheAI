#!/usr/bin/env python3
"""Prepare deterministic BPE token streams for Native Cortex Phase II."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from core.cortex import BPETokenizer


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def prepare_split(
    source: Path,
    destination: Path,
    tokenizer: BPETokenizer,
):
    if "heldout" in source.name.lower():
        raise RuntimeError(
            "Phase II preparation refuses held-out data"
        )

    encoded_documents = []

    document_count = 0
    token_count = 0
    utf8_bytes = 0

    with source.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            record = json.loads(line)

            text = record["text"]

            tokens = tokenizer.encode(
                text,
                add_bos=True,
                add_eos=True,
            )

            encoded_documents.append(
                np.asarray(
                    tokens,
                    dtype=np.uint16,
                )
            )

            document_count += 1
            token_count += len(tokens)
            utf8_bytes += len(
                text.encode("utf-8")
            )

    stream = np.concatenate(
        encoded_documents
    )

    stream.tofile(
        destination
    )

    return {
        "documents": document_count,
        "tokens": token_count,
        "utf8_bytes": utf8_bytes,
        "bytes_on_disk": (
            destination.stat().st_size
        ),
        "sha256": sha256_file(
            destination
        ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tokenizer",
        default=(
            "data/native_cortex/tokenizer/"
            "tokenizer.json"
        ),
    )

    parser.add_argument(
        "--splits",
        default=(
            "data/native_cortex/splits"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "data/native_cortex/tokens"
        ),
    )

    args = parser.parse_args()

    tokenizer = BPETokenizer(
        args.tokenizer
    )

    split_root = Path(
        args.splits
    )

    output = Path(
        args.output
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    report = {
        "format": (
            "mega-prime-native-cortex-"
            "token-stream-v1"
        ),
        "dtype": "uint16",
        "vocab_size": (
            tokenizer.vocab_size
        ),
        "splits": {},
    }

    for split in (
        "train",
        "development",
    ):
        source = (
            split_root
            / f"{split}.jsonl"
        )

        destination = (
            output
            / f"{split}.bin"
        )

        report["splits"][split] = (
            prepare_split(
                source,
                destination,
                tokenizer,
            )
        )

    manifest = (
        output
        / "TOKEN_STREAM_MANIFEST.json"
    )

    manifest.write_text(
        json.dumps(
            report,
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
