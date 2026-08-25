#!/usr/bin/env python3
"""Build provenance-bound Cortex <-> PRIME supervision.

HELDOUT IS FORBIDDEN.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from core.cortex.prime_bridge import (
    PrimeCortexBridge,
    canonical_json,
    stable_hash,
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


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        default=(
            "data/native_cortex/"
            "splits/train.jsonl"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "data/native_cortex/"
            "prime_bridge/train"
        ),
    )

    parser.add_argument(
        "--max-docs",
        type=int,
        default=6000,
    )

    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
    )

    args = parser.parse_args()

    source_path = Path(
        args.source
    )

    if (
        "heldout"
        in source_path.name.lower()
    ):
        raise RuntimeError(
            "HELDOUT BRIDGE ACCESS FORBIDDEN"
        )

    output = Path(
        args.output
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    semantic_path = (
        output
        / "semantic.jsonl"
    )

    verifier_path = (
        output
        / "verifier.jsonl"
    )

    bridge = PrimeCortexBridge()

    semantic_count = 0
    verifier_count = 0
    action_counts = Counter()
    label_counts = Counter()

    parent_hash = ""

    with (
        source_path.open(
            "r",
            encoding="utf-8",
        ) as source,
        semantic_path.open(
            "w",
            encoding="utf-8",
        ) as semantic_file,
        verifier_path.open(
            "w",
            encoding="utf-8",
        ) as verifier_file,
    ):
        for document_index, line in enumerate(
            source
        ):
            if (
                document_index
                >= args.max_docs
            ):
                break

            source_record = json.loads(
                line
            )

            text = str(
                source_record["text"]
            )[
                :args.max_chars
            ]

            source_hash = (
                source_record.get(
                    "sha256"
                )
                or stable_hash(
                    text
                )
            )

            compiled = (
                bridge.compile_source(
                    text
                )
            )

            proposal = (
                bridge.semantic_proposal(
                    text
                )
            )

            semantic_record = {
                "source_sha256": (
                    source_hash
                ),
                "source_text": text,
                "proposal": proposal,
                "proposal_text": (
                    canonical_json(
                        proposal
                    )
                ),
                "proposal_sha256": (
                    stable_hash(
                        proposal
                    )
                ),
                "teacher": (
                    "TSLCCompiler"
                ),
                "authority": "NONE",
            }

            semantic_file.write(
                json.dumps(
                    semantic_record,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                + "\n"
            )

            semantic_count += 1

            experiences = (
                bridge.verify_proposal(
                    source_text=text,
                    source_sha256=(
                        source_hash
                    ),
                    proposal=proposal,
                    parent_hash=(
                        parent_hash
                    ),
                )
            )

            for experience in (
                experiences
            ):
                payload = (
                    experience
                    .__dict__
                    .copy()
                )

                verifier_file.write(
                    json.dumps(
                        payload,
                        sort_keys=True,
                        ensure_ascii=False,
                        default=str,
                    )
                    + "\n"
                )

                parent_hash = (
                    experience.record_hash
                )

                verifier_count += 1

                action_counts[
                    experience.verifier_action
                ] += 1

                label_counts[
                    experience.verifier_label
                ] += 1

            if (
                document_index + 1
            ) % 250 == 0:
                print(
                    "documents:",
                    document_index + 1,
                    "semantic:",
                    semantic_count,
                    "verifier:",
                    verifier_count,
                    "labels:",
                    dict(
                        label_counts
                    ),
                )

    manifest = {
        "format": (
            "mega-prime-cortex-"
            "verifier-experience-v1"
        ),
        "source": str(
            source_path
        ),
        "source_sha256": (
            sha256_file(
                source_path
            )
        ),
        "max_docs": (
            args.max_docs
        ),
        "semantic_records": (
            semantic_count
        ),
        "verifier_records": (
            verifier_count
        ),
        "actions": dict(
            sorted(
                action_counts.items()
            )
        ),
        "labels": dict(
            sorted(
                label_counts.items()
            )
        ),
        "semantic_sha256": (
            sha256_file(
                semantic_path
            )
        ),
        "verifier_sha256": (
            sha256_file(
                verifier_path
            )
        ),
        "final_experience_hash": (
            parent_hash
        ),
        "authority": "NONE",
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

    print()
    print(
        json.dumps(
            manifest,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
