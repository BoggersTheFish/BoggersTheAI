#!/usr/bin/env python3
"""Train the provenance-bound BPE tokenizer for Mega PRIME Native Cortex."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from tokenizers import Tokenizer
from tokenizers.decoders import ByteLevel as ByteLevelDecoder
from tokenizers.models import BPE
from tokenizers.normalizers import NFC
from tokenizers.pre_tokenizers import ByteLevel
from tokenizers.trainers import BpeTrainer


SPECIAL_TOKENS = (
    "<PAD>",
    "<BOS>",
    "<EOS>",
    "<UNK>",
)


def documents(path: Path):
    """Yield TRAIN text only.

    This script must never receive the held-out split.
    """
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            record = json.loads(line)
            yield record["text"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train",
        default="data/native_cortex/splits/train.jsonl",
    )

    parser.add_argument(
        "--output",
        default="data/native_cortex/tokenizer",
    )

    parser.add_argument(
        "--vocab-size",
        type=int,
        default=4096,
    )

    args = parser.parse_args()

    train_path = Path(args.train).resolve()

    if "heldout" in train_path.name.lower():
        raise RuntimeError(
            "refusing to train tokenizer on held-out corpus"
        )

    output = Path(args.output)
    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    tokenizer = Tokenizer(
        BPE(
            unk_token="<UNK>",
        )
    )

    tokenizer.normalizer = NFC()

    tokenizer.pre_tokenizer = ByteLevel(
        add_prefix_space=False,
    )

    tokenizer.decoder = ByteLevelDecoder()

    trainer = BpeTrainer(
        vocab_size=args.vocab_size,
        min_frequency=2,
        special_tokens=list(
            SPECIAL_TOKENS
        ),
        initial_alphabet=(
            ByteLevel.alphabet()
        ),
        show_progress=True,
    )

    tokenizer.train_from_iterator(
        documents(train_path),
        trainer=trainer,
    )

    tokenizer_path = (
        output / "tokenizer.json"
    )

    tokenizer.save(
        str(tokenizer_path)
    )

    tokenizer_digest = sha256_file(
        tokenizer_path
    )

    train_digest = sha256_file(
        train_path
    )

    manifest = {
        "format": "mega-prime-bpe-v1",
        "vocab_size": (
            tokenizer.get_vocab_size()
        ),
        "requested_vocab_size": (
            args.vocab_size
        ),
        "special_tokens": list(
            SPECIAL_TOKENS
        ),
        "train_corpus": str(
            train_path
        ),
        "train_corpus_sha256": (
            train_digest
        ),
        "tokenizer_sha256": (
            tokenizer_digest
        ),
    }

    manifest_path = (
        output
        / "TOKENIZER_MANIFEST.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest_digest = sha256_file(
        manifest_path
    )

    (
        output
        / "TOKENIZER_MANIFEST.sha256"
    ).write_text(
        (
            f"{manifest_digest}  "
            "TOKENIZER_MANIFEST.json\n"
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
