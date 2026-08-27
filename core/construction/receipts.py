"""Deterministic hash-chained receipts for PRIME M20."""

from __future__ import annotations

from copy import deepcopy
import hashlib

from .types import canonical_bytes


GENESIS_HASH = "0" * 64


class ReceiptChain:
    def __init__(self) -> None:
        self._records: list[dict] = []
        self._tip = GENESIS_HASH

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def tip(self) -> str:
        return self._tip

    @property
    def records(self) -> list[dict]:
        return deepcopy(
            self._records
        )

    def append(
        self,
        payload: dict,
    ) -> dict:
        body = deepcopy(payload)

        body["sequence"] = (
            len(self._records)
        )

        body["previous_receipt_hash"] = (
            self._tip
        )

        receipt_hash = hashlib.sha256(
            canonical_bytes(body)
        ).hexdigest()

        record = {
            "payload": body,
            "receipt_hash": receipt_hash,
        }

        self._records.append(
            record
        )

        self._tip = receipt_hash

        return deepcopy(record)


def verify_receipt_chain(
    records: list[dict],
    *,
    expected_count: int | None = None,
    expected_tip: str | None = None,
) -> bool:
    previous = GENESIS_HASH

    for sequence, record in enumerate(
        records
    ):
        payload = record.get(
            "payload"
        )

        receipt_hash = record.get(
            "receipt_hash"
        )

        if not isinstance(
            payload,
            dict,
        ):
            return False

        if payload.get(
            "sequence"
        ) != sequence:
            return False

        if payload.get(
            "previous_receipt_hash"
        ) != previous:
            return False

        actual = hashlib.sha256(
            canonical_bytes(payload)
        ).hexdigest()

        if actual != receipt_hash:
            return False

        previous = actual

    if (
        expected_count is not None
        and len(records)
        != expected_count
    ):
        return False

    if (
        expected_tip is not None
        and previous
        != expected_tip
    ):
        return False

    return True
