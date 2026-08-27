#!/usr/bin/env python3
"""Build balanced supervision from canonical PRIME verifier outcomes.

No labels are invented:
    pass        -> ACCEPT
    fail        -> REJECT
    open_repair -> REPAIR
    unsupported -> ABSTAIN
    error       -> UNKNOWN

HELDOUT IS NEVER ACCESSED.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from core.cortex.prime_bridge import (
    VERIFIER_LABEL_TO_ID,
    stable_hash,
)

from core.kernel.ir import (
    ClaimNode,
    EntityNode,
    Provenance,
    TSIRDocument,
    VerifierObligation,
)

from core.kernel.obligations import (
    ArithmeticVerifier,
    CodePropertyVerifier,
    StructuralVerifier,
)

from core.kernel.transaction import (
    TransactionWorkspace,
)


LABEL_FROM_OUTCOME = {
    "pass": "ACCEPT",
    "fail": "REJECT",
    "unsupported": "ABSTAIN",
    "error": "UNKNOWN",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def workspace(
    document: TSIRDocument | None = None,
):
    return TransactionWorkspace(
        base_graph_hash="curriculum",
        document=(
            document
            if document is not None
            else TSIRDocument()
        ),
        base_nodes={},
        base_edges=[],
    )


def finalize_record(
    *,
    verifier_type,
    source_text,
    premises,
    obligation,
    outcome,
    verifier_result,
):
    label = LABEL_FROM_OUTCOME[
        outcome
    ]

    record = {
        "source_text": source_text,
        "premises": list(premises),
        "obligation": obligation,
        "verifier_type": verifier_type,
        "verifier_action": (
            f"typed_{outcome}"
        ),
        "verifier_label": label,
        "verifier_label_id": (
            VERIFIER_LABEL_TO_ID[
                label
            ]
        ),
        "verifier_result": (
            verifier_result
        ),
        "authority": "NONE",
    }

    record["record_hash"] = (
        stable_hash(record)
    )

    return record


def arithmetic_record(
    index,
    *,
    should_pass,
):
    verifier = ArithmeticVerifier()

    a = (
        3
        + (
            index * 17
        ) % 89
    )

    b = (
        2
        + (
            index * 31
        ) % 73
    )

    correct = a + b

    expected = (
        correct
        if should_pass
        else correct + 1
    )

    expression = (
        f"{a} + {b} = {expected}"
    )

    obligation = VerifierObligation(
        id=f"curriculum:arith:{index}",
        verifier_type="arithmetic",
        target_claim=expression,
        expected_property={
            "expression": expression,
        },
    )

    result = verifier.verify(
        obligation,
        workspace(),
    )

    expected_outcome = (
        "pass"
        if should_pass
        else "fail"
    )

    if (
        result.outcome
        != expected_outcome
    ):
        raise RuntimeError(
            (
                "arithmetic verifier mismatch: "
                f"{result.outcome} "
                f"!= {expected_outcome}"
            )
        )

    return finalize_record(
        verifier_type="arithmetic",
        source_text=(
            "Verify the arithmetic proposition: "
            + expression
        ),
        premises=[],
        obligation=expression,
        outcome=result.outcome,
        verifier_result=(
            result.to_dict()
        ),
    )


def code_record(
    index,
    *,
    should_pass,
):
    verifier = CodePropertyVerifier()

    multiplier = (
        2
        + index % 5
    )

    offset = (
        index % 7
    )

    function = (
        f"transform_{index}"
    )

    body = (
        f"x * {multiplier} + {offset}"
    )

    examples = []

    for value in (
        0,
        1,
        2,
        5,
    ):
        expected = (
            value
            * multiplier
            + offset
        )

        examples.append(
            {
                "input": value,
                "expected": expected,
            }
        )

    if not should_pass:
        examples[-1][
            "expected"
        ] += 1

    spec = {
        "function": function,
        "parameter": "x",
        "body": body,
        "examples": examples,
    }

    obligation = VerifierObligation(
        id=f"curriculum:code:{index}",
        verifier_type="code_property",
        target_claim=function,
        expected_property=spec,
    )

    result = verifier.verify(
        obligation,
        workspace(),
    )

    expected_outcome = (
        "pass"
        if should_pass
        else "fail"
    )

    if (
        result.outcome
        != expected_outcome
    ):
        raise RuntimeError(
            (
                "code verifier mismatch: "
                f"{result.outcome} "
                f"!= {expected_outcome}"
            )
        )

    premise = (
        f"{function}(x) = {body}; "
        f"examples = {examples}"
    )

    return finalize_record(
        verifier_type="code_property",
        source_text=(
            "Verify this bounded code property: "
            + premise
        ),
        premises=[
            premise
        ],
        obligation=(
            f"{function} satisfies "
            "the supplied examples"
        ),
        outcome=result.outcome,
        verifier_result=(
            result.to_dict()
        ),
    )


def structural_record(
    index,
    *,
    should_pass,
):
    verifier = StructuralVerifier()

    provenance = Provenance(
        "system_seed",
        reliability=1.0,
    )

    subject = (
        f"entity:subject:{index}"
    )

    object_id = (
        f"entity:object:{index}"
    )

    entities = [
        EntityNode(
            id=subject,
            entity_type="object",
            label=f"subject {index}",
            provenance=provenance,
        )
    ]

    if should_pass:
        entities.append(
            EntityNode(
                id=object_id,
                entity_type="object",
                label=f"object {index}",
                provenance=provenance,
            )
        )

    claim = ClaimNode(
        id=f"claim:struct:{index}",
        subject=subject,
        predicate="related_to",
        object=object_id,
        status="proposed",
        provenance=provenance,
    )

    document = TSIRDocument(
        entities=entities,
        claims=[
            claim
        ],
    )

    obligation = VerifierObligation(
        id=f"curriculum:struct:{index}",
        verifier_type="structural",
        target_claim="__document__",
    )

    result = verifier.verify(
        obligation,
        workspace(document),
    )

    expected_outcome = (
        "pass"
        if should_pass
        else "fail"
    )

    if (
        result.outcome
        != expected_outcome
    ):
        raise RuntimeError(
            (
                "structural verifier mismatch: "
                f"{result.outcome} "
                f"!= {expected_outcome}"
            )
        )

    premise = (
        f"subject={subject}; "
        f"object={object_id}; "
        f"object_declared={should_pass}"
    )

    return finalize_record(
        verifier_type="structural",
        source_text=(
            "Check TSIR structural consistency: "
            + premise
        ),
        premises=[
            premise
        ],
        obligation=(
            "TSIR document is "
            "internally consistent"
        ),
        outcome=result.outcome,
        verifier_result=(
            result.to_dict()
        ),
    )


def abstain_record(
    index,
):
    verifier = CodePropertyVerifier()

    obligation = VerifierObligation(
        id=f"curriculum:unsupported:{index}",
        verifier_type="code_property",
        target_claim=(
            f"unsupported program {index}"
        ),
        expected_property={
            "unsupported_input": True,
        },
    )

    result = verifier.verify(
        obligation,
        workspace(),
    )

    if (
        result.outcome
        != "unsupported"
    ):
        raise RuntimeError(
            "expected unsupported outcome"
        )

    return finalize_record(
        verifier_type="code_property",
        source_text=(
            "Verify an unrestricted program "
            f"outside the bounded verifier: {index}"
        ),
        premises=[],
        obligation=(
            "verify unsupported general "
            f"program property {index}"
        ),
        outcome=result.outcome,
        verifier_result=(
            result.to_dict()
        ),
    )


def unknown_record(
    index,
):
    verifier = ArithmeticVerifier()

    expression = (
        f"unknown_symbol_{index} + 2 = 4"
    )

    obligation = VerifierObligation(
        id=f"curriculum:error:{index}",
        verifier_type="arithmetic",
        target_claim=expression,
        expected_property={
            "expression": expression,
        },
    )

    result = verifier.verify(
        obligation,
        workspace(),
    )

    if (
        result.outcome
        != "error"
    ):
        raise RuntimeError(
            (
                "expected arithmetic "
                "error outcome"
            )
        )

    return finalize_record(
        verifier_type="arithmetic",
        source_text=(
            "Attempt verifier evaluation "
            "with unresolved symbol: "
            + expression
        ),
        premises=[],
        obligation=expression,
        outcome=result.outcome,
        verifier_result=(
            result.to_dict()
        ),
    )


def load_repairs(
    path: Path,
):
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as handle:
        for line in handle:
            row = json.loads(line)

            if (
                row.get(
                    "verifier_label"
                )
                != "REPAIR"
            ):
                continue

            record = {
                "source_text": (
                    row.get(
                        "source_text",
                        "",
                    )
                ),
                "premises": (
                    row.get(
                        "premises",
                        [],
                    )
                ),
                "obligation": (
                    row.get(
                        "obligation",
                        "",
                    )
                ),
                "verifier_type": (
                    "general_claim"
                ),
                "verifier_action": (
                    row.get(
                        "verifier_action",
                        "open_repair",
                    )
                ),
                "verifier_label": (
                    "REPAIR"
                ),
                "verifier_label_id": (
                    VERIFIER_LABEL_TO_ID[
                        "REPAIR"
                    ]
                ),
                "verifier_result": (
                    row.get(
                        "verifier_result",
                        {},
                    )
                ),
                "authority": "NONE",
                "source_record_hash": (
                    row.get(
                        "record_hash",
                        "",
                    )
                ),
            }

            record[
                "record_hash"
            ] = stable_hash(
                record
            )

            records.append(
                record
            )

    return sorted(
        records,
        key=lambda row: (
            row["record_hash"]
        ),
    )


def create_split(
    *,
    split,
    per_class,
    repair_path,
    seed,
):
    records = []

    for index in range(
        per_class
    ):
        selector = (
            index % 3
        )

        if selector == 0:
            accept = (
                arithmetic_record(
                    index,
                    should_pass=True,
                )
            )

            reject = (
                arithmetic_record(
                    index + 100000,
                    should_pass=False,
                )
            )

        elif selector == 1:
            accept = (
                code_record(
                    index,
                    should_pass=True,
                )
            )

            reject = (
                code_record(
                    index + 100000,
                    should_pass=False,
                )
            )

        else:
            accept = (
                structural_record(
                    index,
                    should_pass=True,
                )
            )

            reject = (
                structural_record(
                    index + 100000,
                    should_pass=False,
                )
            )

        records.append(
            accept
        )

        records.append(
            reject
        )

        records.append(
            abstain_record(
                index
            )
        )

        records.append(
            unknown_record(
                index
            )
        )

    repairs = load_repairs(
        repair_path
    )

    if (
        len(repairs)
        < per_class
    ):
        raise RuntimeError(
            (
                f"{split}: need "
                f"{per_class} REPAIR "
                "records but only found "
                f"{len(repairs)}"
            )
        )

    records.extend(
        repairs[
            :per_class
        ]
    )

    rng = random.Random(
        seed
    )

    rng.shuffle(
        records
    )

    counts = Counter(
        row[
            "verifier_label"
        ]
        for row
        in records
    )

    expected = {
        label: per_class
        for label in (
            "ACCEPT",
            "REJECT",
            "REPAIR",
            "ABSTAIN",
            "UNKNOWN",
        )
    }

    if dict(
        sorted(
            counts.items()
        )
    ) != dict(
        sorted(
            expected.items()
        )
    ):
        raise RuntimeError(
            (
                f"unbalanced split: "
                f"{counts}"
            )
        )

    return (
        records,
        counts,
    )


def write_jsonl(
    path,
    records,
):
    parent_hash = ""

    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        for record in records:
            output = dict(
                record
            )

            output[
                "parent_hash"
            ] = parent_hash

            output[
                "experience_hash"
            ] = stable_hash(
                output
            )

            parent_hash = (
                output[
                    "experience_hash"
                ]
            )

            handle.write(
                json.dumps(
                    output,
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

    return parent_hash


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--train-repairs",
        default=(
            "data/native_cortex/"
            "prime_bridge/train/"
            "verifier.jsonl"
        ),
    )

    parser.add_argument(
        "--development-repairs",
        default=(
            "data/native_cortex/"
            "prime_bridge/development/"
            "verifier.jsonl"
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "data/native_cortex/"
            "prime_bridge/curriculum"
        ),
    )

    parser.add_argument(
        "--train-per-class",
        type=int,
        default=500,
    )

    parser.add_argument(
        "--development-per-class",
        type=int,
        default=100,
    )

    args = parser.parse_args()

    output = Path(
        args.output
    )

    output.mkdir(
        parents=True,
        exist_ok=True,
    )

    specifications = (
        (
            "train",
            args.train_per_class,
            Path(
                args.train_repairs
            ),
            26082311,
        ),
        (
            "development",
            args.development_per_class,
            Path(
                args.development_repairs
            ),
            26082312,
        ),
    )

    manifest = {
        "format": (
            "mega-prime-typed-"
            "verifier-curriculum-v1"
        ),
        "mapping": {
            "pass": "ACCEPT",
            "fail": "REJECT",
            "open_repair": "REPAIR",
            "unsupported": "ABSTAIN",
            "error": "UNKNOWN",
        },
        "authority": "NONE",
        "splits": {},
    }

    for (
        split,
        per_class,
        repair_path,
        seed,
    ) in specifications:
        records, counts = (
            create_split(
                split=split,
                per_class=per_class,
                repair_path=repair_path,
                seed=seed,
            )
        )

        path = (
            output
            / f"{split}.jsonl"
        )

        final_hash = write_jsonl(
            path,
            records,
        )

        manifest[
            "splits"
        ][split] = {
            "records": len(
                records
            ),
            "labels": dict(
                sorted(
                    counts.items()
                )
            ),
            "sha256": (
                sha256_file(
                    path
                )
            ),
            "final_experience_hash": (
                final_hash
            ),
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
