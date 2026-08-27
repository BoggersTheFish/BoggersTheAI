"""Persistent verified construction library for PRIME M20."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .grammar import (
    dependencies,
)
from .receipts import (
    verify_receipt_chain,
)
from .registry import (
    ConstructionRegistry,
)
from .types import (
    canonical_bytes,
)


LIBRARY_FORMAT = (
    "prime-m20-construction-library-v1"
)


def snapshot_registry(
    registry: ConstructionRegistry,
) -> dict:
    records = []

    for construction_id, record in sorted(
        registry._records.items()
    ):
        records.append(
            {
                "construction": (
                    record.spec.to_dict()
                ),
                "status": (
                    record.status.value
                ),
                "proposed_sequence": (
                    record.proposed_sequence
                ),
                "authorized_sequence": (
                    record.authorized_sequence
                ),
                "retired_sequence": (
                    record.retired_sequence
                ),
                "dependencies": sorted(
                    dependencies(
                        record.spec.expression
                    )
                ),
            }
        )

    payload = {
        "format": LIBRARY_FORMAT,
        "registry_hash": (
            registry.registry_hash()
        ),
        "active_construction_ids": list(
            registry.active_ids()
        ),
        "records": records,
        "receipt_chain": (
            registry.receipts.records
        ),
        "receipt_count": (
            registry.receipts.count
        ),
        "receipt_tip": (
            registry.receipts.tip
        ),
    }

    payload["library_hash"] = (
        hashlib.sha256(
            canonical_bytes(
                payload
            )
        ).hexdigest()
    )

    return payload


def validate_library(
    payload: dict,
) -> bool:
    if (
        payload.get("format")
        != LIBRARY_FORMAT
    ):
        return False

    supplied_hash = (
        payload.get(
            "library_hash"
        )
    )

    if not isinstance(
        supplied_hash,
        str,
    ):
        return False

    unsigned = dict(
        payload
    )

    unsigned.pop(
        "library_hash",
        None,
    )

    actual = hashlib.sha256(
        canonical_bytes(
            unsigned
        )
    ).hexdigest()

    if actual != supplied_hash:
        return False

    if not verify_receipt_chain(
        payload.get(
            "receipt_chain",
            [],
        ),
        expected_count=(
            payload.get(
                "receipt_count"
            )
        ),
        expected_tip=(
            payload.get(
                "receipt_tip"
            )
        ),
    ):
        return False

    active = set(
        payload.get(
            "active_construction_ids",
            [],
        )
    )

    known = {
        row[
            "construction"
        ][
            "construction_id"
        ]
        for row
        in payload.get(
            "records",
            [],
        )
    }

    if not active.issubset(
        known
    ):
        return False

    return True


def save_library(
    registry: ConstructionRegistry,
    path: (
        str
        | Path
    ),
) -> str:
    path = Path(
        path
    )

    payload = (
        snapshot_registry(
            registry
        )
    )

    path.write_bytes(
        canonical_bytes(
            payload
        )
    )

    return payload[
        "library_hash"
    ]


def load_library(
    path: (
        str
        | Path
    ),
) -> dict:
    payload = json.loads(
        Path(
            path
        ).read_text(
            encoding="utf-8"
        )
    )

    if not validate_library(
        payload
    ):
        raise ValueError(
            "invalid construction library"
        )

    return payload
