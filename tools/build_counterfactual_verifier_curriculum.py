#!/usr/bin/env python3
"""Build matched counterfactual Cortex-PRIME verifier curriculum.

ACCEPT and REJECT are newly generated matched pairs using canonical
typed PRIME verifiers.

UNKNOWN, REPAIR and ABSTAIN are copied from the frozen v1 curriculum.

HELDOUT IS NEVER ACCESSED.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from core.cortex.counterfactual_verifier import (
    PAIR_CHANNELS,
    build_counterfactual_pair,
)

from core.cortex.prime_bridge import (
    stable_hash,
)


FROZEN_TRAIN_SHA256 = (
    "09a08d5924c7f0616d16beecce6c75f03e52ce6cfe100afa3f00c2d9cf4c6516"
)

FROZEN_DEVELOPMENT_SHA256 = (
    "071305f8af9974b9014a297dbcf2058aa768ccb80224ef962b184447c61c2f57"
)

CONTROL_LABELS = (
    "UNKNOWN",
    "REPAIR",
    "ABSTAIN",
)


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


def load_jsonl(
    path: Path,
):
    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        return [
            json.loads(line)
            for line in handle
            if line.strip()
        ]


def copy_control_records(
    records,
    *,
    count_per_label: int,
    source_name: str,
):
    selected = []

    for label in CONTROL_LABELS:
        candidates = [
            row
            for row in records
            if row.get(
                "verifier_label"
            ) == label
        ]

        if len(candidates) < count_per_label:
            raise RuntimeError(
                f"not enough {label} controls "
                f"in {source_name}: "
                f"{len(candidates)} "
                f"< {count_per_label}"
            )

        for source in candidates[
            :count_per_label
        ]:
            row = dict(source)

            source_record_hash = row.pop(
                "record_hash",
                ""
            )

            source_experience_hash = row.pop(
                "experience_hash",
                ""
            )

            source_parent_hash = row.pop(
                "parent_hash",
                ""
            )

            row[
                "counterfactual_pair"
            ] = False

            row[
                "curriculum_origin"
            ] = (
                "frozen_v1_control"
            )

            row[
                "source_curriculum"
            ] = source_name

            row[
                "source_record_hash"
            ] = source_record_hash

            if source_experience_hash:
                row[
                    "source_experience_hash"
                ] = source_experience_hash

            if source_parent_hash:
                row[
                    "source_parent_hash"
                ] = source_parent_hash

            row["record_hash"] = (
                stable_hash(row)
            )

            selected.append(
                row
            )

    return selected


def build_split(
    *,
    split_name: str,
    pair_count: int,
    index_offset: int,
    control_source,
    output_path: Path,
    rng_seed: int,
):
    records = []
    pair_hashes = []

    for pair_number in range(
        pair_count
    ):
        channel = PAIR_CHANNELS[
            pair_number
            % len(PAIR_CHANNELS)
        ]

        pair_index = (
            index_offset
            + pair_number
        )

        pair = (
            build_counterfactual_pair(
                channel,
                pair_index,
                split=split_name,
            )
        )

        if len(pair) != 2:
            raise RuntimeError(
                "counterfactual pair "
                "must contain exactly "
                "two records"
            )

        labels = {
            row[
                "verifier_label"
            ]
            for row in pair
        }

        if labels != {
            "ACCEPT",
            "REJECT",
        }:
            raise RuntimeError(
                "counterfactual pair "
                "must contain exactly "
                "ACCEPT and REJECT"
            )

        pair_hash = pair[0][
            "pair_hash"
        ]

        if pair[1][
            "pair_hash"
        ] != pair_hash:
            raise RuntimeError(
                "pair hash mismatch"
            )

        pair_hashes.append(
            pair_hash
        )

        records.extend(
            pair
        )

    controls = copy_control_records(
        control_source,
        count_per_label=pair_count,
        source_name=split_name,
    )

    records.extend(
        controls
    )

    label_counts = Counter(
        row[
            "verifier_label"
        ]
        for row in records
    )

    expected = {
        "UNKNOWN": pair_count,
        "ACCEPT": pair_count,
        "REJECT": pair_count,
        "REPAIR": pair_count,
        "ABSTAIN": pair_count,
    }

    if dict(
        sorted(
            label_counts.items()
        )
    ) != expected:
        raise RuntimeError(
            "unexpected label balance: "
            + str(label_counts)
        )

    rng = random.Random(
        rng_seed
    )

    rng.shuffle(
        records
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in records:
            handle.write(
                json.dumps(
                    row,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            )

    channel_counts = Counter(
        row["verifier_type"]
        for row in records
        if row.get(
            "counterfactual_pair"
        )
    )

    return {
        "split": split_name,
        "records": len(records),
        "pairs": pair_count,
        "labels": dict(
            sorted(
                label_counts.items()
            )
        ),
        "paired_channels": dict(
            sorted(
                channel_counts.items()
            )
        ),
        "pair_set_sha256": stable_hash(
            sorted(
                pair_hashes
            )
        ),
        "sha256": sha256_file(
            output_path
        ),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source-train",
        default=(
            "data/native_cortex/"
            "prime_bridge/curriculum/"
            "train.jsonl"
        ),
    )

    parser.add_argument(
        "--source-development",
        default=(
            "data/native_cortex/"
            "prime_bridge/curriculum/"
            "development.jsonl"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "data/native_cortex/"
            "verifier_semantics/"
            "counterfactual_v1"
        ),
    )

    parser.add_argument(
        "--train-pairs",
        type=int,
        default=500,
    )

    parser.add_argument(
        "--development-pairs",
        type=int,
        default=100,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=26082501,
    )

    args = parser.parse_args()

    train_path = Path(
        args.source_train
    )

    development_path = Path(
        args.source_development
    )

    for path in (
        train_path,
        development_path,
    ):
        if "heldout" in str(
            path
        ).lower():
            raise RuntimeError(
                "HELDOUT ACCESS FORBIDDEN"
            )

    observed_train_sha = (
        sha256_file(
            train_path
        )
    )

    observed_development_sha = (
        sha256_file(
            development_path
        )
    )

    if (
        observed_train_sha
        != FROZEN_TRAIN_SHA256
    ):
        raise RuntimeError(
            "frozen train curriculum "
            "hash mismatch: "
            + observed_train_sha
        )

    if (
        observed_development_sha
        != FROZEN_DEVELOPMENT_SHA256
    ):
        raise RuntimeError(
            "frozen development "
            "curriculum hash mismatch: "
            + observed_development_sha
        )

    train_source = load_jsonl(
        train_path
    )

    development_source = load_jsonl(
        development_path
    )

    output = Path(
        args.output
    )

    train_result = build_split(
        split_name="train",
        pair_count=args.train_pairs,
        index_offset=0,
        control_source=train_source,
        output_path=(
            output
            / "train.jsonl"
        ),
        rng_seed=args.seed,
    )

    development_result = build_split(
        split_name="development",
        pair_count=(
            args.development_pairs
        ),
        index_offset=100000,
        control_source=(
            development_source
        ),
        output_path=(
            output
            / "development.jsonl"
        ),
        rng_seed=(
            args.seed
            + 1
        ),
    )

    manifest = {
        "format": (
            "mega-prime-counterfactual-"
            "verifier-curriculum-v1"
        ),
        "authority": "NONE",
        "construction": (
            "matched ACCEPT/REJECT "
            "canonical typed verifier pairs "
            "plus frozen v1 UNKNOWN/REPAIR/"
            "ABSTAIN controls"
        ),
        "source_train_sha256": (
            observed_train_sha
        ),
        "source_development_sha256": (
            observed_development_sha
        ),
        "builder_sha256": sha256_file(
            Path(__file__)
        ),
        "seed": args.seed,
        "splits": {
            "train": train_result,
            "development": (
                development_result
            ),
        },
    }

    manifest_path = (
        output
        / "MANIFEST.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
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
