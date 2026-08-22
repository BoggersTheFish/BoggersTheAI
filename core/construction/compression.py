"""Predictive-quotient compression proposals for PRIME M20."""

from __future__ import annotations

from dataclasses import dataclass

from .quotient import (
    expanded_description_length,
    predictive_partition_signature,
    registry_expression_lookup,
)
from .registry import (
    ConstructionRegistry,
)


@dataclass(frozen=True)
class CompressionProposal:
    retained_construction_id: str
    redundant_construction_ids: (
        tuple[str, ...]
    )
    quotient_signature: str
    state_commit_authorized: bool = False


def propose_partition_compression(
    registry: ConstructionRegistry,
    *,
    max_lag: int = 8,
) -> tuple[
    CompressionProposal,
    ...,
]:
    """Detect redundant authorized representations.

    Proposal only. Does not mutate registry state.
    """

    lookup = (
        registry_expression_lookup(
            registry
        )
    )

    groups: dict[
        int,
        list,
    ] = {}

    for record in (
        registry.active_records()
    ):
        signature = (
            predictive_partition_signature(
                record.spec.expression,
                max_lag=max_lag,
                lookup=lookup,
            )
        )

        groups.setdefault(
            signature,
            [],
        ).append(
            record
        )

    proposals = []

    for signature, records in (
        groups.items()
    ):
        if len(records) < 2:
            continue

        ordered = sorted(
            records,
            key=lambda record: (
                expanded_description_length(
                    record.spec.expression,
                    lookup=lookup,
                ),
                record.authorized_sequence,
                record.spec.construction_id,
            ),
        )

        retained = ordered[0]

        redundant = tuple(
            row.spec.construction_id
            for row in ordered[
                1:
            ]
        )

        proposals.append(
            CompressionProposal(
                retained_construction_id=(
                    retained.spec.construction_id
                ),
                redundant_construction_ids=(
                    redundant
                ),
                quotient_signature=(
                    hex(
                        signature
                    )
                ),
                state_commit_authorized=False,
            )
        )

    proposals.sort(
        key=lambda row: (
            row.retained_construction_id
        )
    )

    return tuple(
        proposals
    )
