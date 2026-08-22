"""Canonical hash-chained receipts with truncation anchors."""

from copy import deepcopy
import hashlib
import json


GENESIS_HASH = "0" * 64


def canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(
        canonical_bytes(payload)
    ).hexdigest()


class ReceiptChain:
    def __init__(self) -> None:
        self._records: list[dict] = []

    @property
    def records(self) -> list[dict]:
        return deepcopy(self._records)

    @property
    def count(self) -> int:
        return len(self._records)

    @property
    def tip(self) -> str:
        if not self._records:
            return GENESIS_HASH
        return self._records[-1]["receipt_hash"]

    def append(self, payload: dict) -> dict:
        material = deepcopy(payload)
        material["sequence"] = self.count + 1
        material["previous_receipt_hash"] = self.tip

        record = {
            "payload": material,
            "receipt_hash": payload_hash(material),
        }

        self._records.append(record)
        return deepcopy(record)


def verify_receipt_chain(
    records: list[dict],
    *,
    expected_count: int | None = None,
    expected_tip: str | None = None,
) -> bool:
    if (
        expected_count is not None
        and len(records) != expected_count
    ):
        return False

    previous = GENESIS_HASH

    for expected_sequence, record in enumerate(
        records,
        start=1,
    ):
        if set(record) != {
            "payload",
            "receipt_hash",
        }:
            return False

        payload = record["payload"]
        claimed_hash = record["receipt_hash"]

        if not isinstance(payload, dict):
            return False

        if payload.get("sequence") != expected_sequence:
            return False

        if (
            payload.get("previous_receipt_hash")
            != previous
        ):
            return False

        if payload_hash(payload) != claimed_hash:
            return False

        previous = claimed_hash

    actual_tip = (
        records[-1]["receipt_hash"]
        if records
        else GENESIS_HASH
    )

    if (
        expected_tip is not None
        and actual_tip != expected_tip
    ):
        return False

    return True
