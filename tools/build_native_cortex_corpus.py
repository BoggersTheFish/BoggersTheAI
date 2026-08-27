#!/usr/bin/env python3
"""Build a deterministic provenance-bound Native Cortex language corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm


def digest_text(text: str) -> str:
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def split_from_hash(
    digest: str,
) -> str:
    """Document-level deterministic split.

    ~98% train
    ~1% development
    ~1% heldout

    The split depends only on document content.
    """

    value = int(
        digest[:16],
        16,
    ) % 10_000

    if value < 100:
        return "heldout"

    if value < 200:
        return "development"

    return "train"


def write_record(
    handles,
    *,
    source,
    source_split,
    index,
    text,
):
    text = text.strip()

    if len(text) < 80:
        return None

    digest = digest_text(
        text
    )

    split = split_from_hash(
        digest
    )

    record = {
        "sha256": digest,
        "source": source,
        "source_split": source_split,
        "source_index": index,
        "characters": len(text),
        "text": text,
    }

    handles[
        split
    ].write(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
        )
        + "\n"
    )

    return split


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        default="data/native_cortex/splits",
    )

    parser.add_argument(
        "--tinystories",
        type=int,
        default=25_000,
        help="Maximum TinyStories documents.",
    )

    parser.add_argument(
        "--wikitext",
        type=int,
        default=20_000,
        help="Maximum non-empty WikiText passages.",
    )

    args = parser.parse_args()

    output = Path(
        args.output
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = {
        split: output / f"{split}.jsonl"
        for split in (
            "train",
            "development",
            "heldout",
        )
    }

    handles = {
        split: path.open(
            "w",
            encoding="utf-8",
        )
        for split, path in paths.items()
    }

    counts = {
        split: 0
        for split in handles
    }

    characters = {
        split: 0
        for split in handles
    }

    provenance = []

    try:
        tiny = load_dataset(
            "roneneldan/TinyStories",
            split="train",
            streaming=True,
        )

        for index, row in enumerate(
            tqdm(
                tiny,
                total=args.tinystories,
                desc="TinyStories",
            )
        ):
            if index >= args.tinystories:
                break

            text = row.get(
                "text",
                "",
            )

            result = write_record(
                handles,
                source="roneneldan/TinyStories",
                source_split="train",
                index=index,
                text=text,
            )

            if result is not None:
                counts[result] += 1
                characters[result] += len(
                    text.strip()
                )

        provenance.append(
            {
                "source": "roneneldan/TinyStories",
                "source_split": "train",
                "maximum_records_examined": args.tinystories,
            }
        )

        wiki = load_dataset(
            "Salesforce/wikitext",
            "wikitext-103-v1",
            split="train",
            streaming=True,
        )

        accepted = 0

        for index, row in enumerate(
            tqdm(
                wiki,
                desc="WikiText",
            )
        ):
            text = row.get(
                "text",
                "",
            ).strip()

            if len(text) < 80:
                continue

            result = write_record(
                handles,
                source="Salesforce/wikitext",
                source_split="train",
                index=index,
                text=text,
            )

            if result is not None:
                counts[result] += 1
                characters[result] += len(
                    text
                )

                accepted += 1

            if accepted >= args.wikitext:
                break

        provenance.append(
            {
                "source": "Salesforce/wikitext",
                "configuration": "wikitext-103-v1",
                "source_split": "train",
                "maximum_accepted_records": args.wikitext,
            }
        )

    finally:
        for handle in handles.values():
            handle.close()

    manifest = {
        "format": "mega-prime-native-cortex-corpus-v1",
        "split_policy": (
            "sha256(document) mod 10000: "
            "0..99 heldout, "
            "100..199 development, "
            "200..9999 train"
        ),
        "counts": counts,
        "characters": characters,
        "sources": provenance,
        "files": {},
    }

    for split, path in paths.items():
        digest = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

        manifest["files"][
            split
        ] = {
            "path": str(path),
            "sha256": digest,
            "bytes": path.stat().st_size,
        }

    manifest_path = (
        output
        / "CORPUS_MANIFEST.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        ),
        encoding="utf-8",
    )

    manifest_digest = hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()

    (
        output
        / "CORPUS_MANIFEST.sha256"
    ).write_text(
        f"{manifest_digest}  CORPUS_MANIFEST.json\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
