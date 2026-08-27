"""Graph proposal projection for PRIME M20.

This module does NOT mutate the living graph.

It emits a deterministic proposal envelope suitable for a later
TSKernel/TSIR authority adapter.
"""

from __future__ import annotations

import hashlib

from .grammar import (
    dependencies,
)
from .registry import (
    ConstructionRegistry,
)
from .types import (
    canonical_bytes,
)


PROJECTION_VERSION = (
    "prime-m20-construction-projection-v1"
)


def project_registry(
    registry: ConstructionRegistry,
) -> dict:
    nodes = []
    edges = []

    for construction_id, record in sorted(
        registry._records.items()
    ):
        nodes.append(
            {
                "node_id": (
                    construction_id
                ),
                "node_type": (
                    "prime_construction"
                ),
                "status": (
                    record.status.value
                ),
                "expression": (
                    record.spec.expression.to_dict()
                ),
                "proposal_source": (
                    record.spec.proposal_source
                ),
                "authoritative": (
                    record.status.value
                    == "authorized"
                ),
            }
        )

        for dependency in sorted(
            dependencies(
                record.spec.expression
            )
        ):
            edges.append(
                {
                    "src": (
                        construction_id
                    ),
                    "dst": dependency,
                    "relation": (
                        "depends_on"
                    ),
                }
            )

    payload = {
        "projection_version": (
            PROJECTION_VERSION
        ),
        "registry_hash": (
            registry.registry_hash()
        ),
        "receipt_tip": (
            registry.receipts.tip
        ),
        "nodes": nodes,
        "edges": edges,
        "requested_operation": (
            "PROPOSE_GRAPH_DELTA"
        ),
        "state_commit_authorized": (
            False
        ),
    }

    payload[
        "projection_hash"
    ] = hashlib.sha256(
        canonical_bytes(
            payload
        )
    ).hexdigest()

    return payload
