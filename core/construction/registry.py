"""Canonical construction registry for PRIME M20."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .receipts import ReceiptChain
from .types import (
    AuthorityAction,
    ConstructionSpec,
    ConstructionStatus,
    VerifierAuthorization,
    canonical_bytes,
)


@dataclass
class ConstructionRecord:
    spec: ConstructionSpec
    status: ConstructionStatus
    proposed_sequence: int
    authorized_sequence: int | None = None
    retired_sequence: int | None = None


class ConstructionRegistry:
    """Proposal/state separation for constructed representation."""

    def __init__(self) -> None:
        self._records: dict[
            str,
            ConstructionRecord,
        ] = {}

        self._proposal_sequence = 0
        self._authorization_sequence = 0

        self.receipts = ReceiptChain()

    def propose(
        self,
        spec: ConstructionSpec,
    ) -> ConstructionRecord:
        construction_id = (
            spec.construction_id
        )

        existing = self._records.get(
            construction_id
        )

        if existing is not None:
            return existing

        record = ConstructionRecord(
            spec=spec,
            status=ConstructionStatus.PROPOSED,
            proposed_sequence=(
                self._proposal_sequence
            ),
        )

        self._proposal_sequence += 1

        self._records[
            construction_id
        ] = record

        return record

    def get(
        self,
        construction_id: str,
    ) -> ConstructionRecord | None:
        return self._records.get(
            construction_id
        )

    def active_records(
        self,
    ) -> tuple[
        ConstructionRecord,
        ...,
    ]:
        rows = [
            record
            for record
            in self._records.values()
            if record.status
            == ConstructionStatus.AUTHORIZED
        ]

        rows.sort(
            key=lambda record: (
                record.authorized_sequence,
                record.spec.construction_id,
            )
        )

        return tuple(rows)

    def active_ids(self) -> tuple[str, ...]:
        return tuple(
            row.spec.construction_id
            for row in self.active_records()
        )

    def registry_hash(self) -> str:
        payload = [
            {
                "construction_id": (
                    record.spec.construction_id
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
            }
            for record
            in sorted(
                self._records.values(),
                key=lambda row: (
                    row.spec.construction_id
                ),
            )
        ]

        return hashlib.sha256(
            canonical_bytes(payload)
        ).hexdigest()

    def apply(
        self,
        authorization: VerifierAuthorization,
    ) -> dict:
        if not authorization.verdict:
            raise PermissionError(
                "failed verifier verdict cannot mutate registry"
            )

        record = self._records.get(
            authorization.construction_id
        )

        if record is None:
            raise KeyError(
                "construction must be proposed before authorization"
            )

        before = self.registry_hash()

        action = authorization.action

        if action == AuthorityAction.AUTHORIZE:
            if (
                record.status
                != ConstructionStatus.PROPOSED
            ):
                raise ValueError(
                    "only proposed construction may be authorized"
                )

            record.status = (
                ConstructionStatus.AUTHORIZED
            )

            record.authorized_sequence = (
                self._authorization_sequence
            )

            self._authorization_sequence += 1

        elif action == AuthorityAction.RETIRE:
            if (
                record.status
                != ConstructionStatus.AUTHORIZED
            ):
                raise ValueError(
                    "only authorized construction may be retired"
                )

            record.status = (
                ConstructionStatus.RETIRED
            )

            record.retired_sequence = (
                self._authorization_sequence
            )

            self._authorization_sequence += 1

        elif action == AuthorityAction.RESTORE:
            if (
                record.status
                != ConstructionStatus.RETIRED
            ):
                raise ValueError(
                    "only retired construction may be restored"
                )

            record.status = (
                ConstructionStatus.AUTHORIZED
            )

            record.authorized_sequence = (
                self._authorization_sequence
            )

            self._authorization_sequence += 1

        else:
            raise ValueError(
                "unsupported authority action"
            )

        after = self.registry_hash()

        return self.receipts.append(
            {
                "event": (
                    "CONSTRUCTION_AUTHORITY_TRANSITION"
                ),
                "action": (
                    action.value
                ),
                "construction": (
                    record.spec.to_dict()
                ),
                "evidence_hash": (
                    authorization.evidence_hash
                ),
                "reason": (
                    authorization.reason
                ),
                "registry_hash_before": (
                    before
                ),
                "registry_hash_after": (
                    after
                ),
                "active_construction_ids": list(
                    self.active_ids()
                ),
            }
        )
