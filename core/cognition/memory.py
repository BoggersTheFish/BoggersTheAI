"""Persistent verifier-backed semantic construction memory."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path

from core.construction.grammar import (
    binary,
    description_length,
    lag,
)
from core.construction.quotient import (
    predictive_partition_signature,
)
from core.construction.receipts import (
    verify_receipt_chain,
)
from core.construction.registry import (
    ConstructionRegistry,
)
from core.construction.types import (
    ConstructionSpec,
    FeatureExpr,
    FeatureOp,
    expr_from_dict,
)


def expand_references(
    expr: FeatureExpr,
    lookup: dict[str, FeatureExpr],
    stack: tuple[str, ...] = (),
) -> FeatureExpr:
    """Convert a registry-dependent expression into a portable expression."""

    if expr.op == FeatureOp.LAG:
        assert expr.lag is not None
        return lag(expr.lag)

    if expr.op == FeatureOp.REF:
        assert expr.ref_id is not None

        if expr.ref_id in stack:
            raise ValueError(
                "cyclic construction dependency"
            )

        target = lookup.get(
            expr.ref_id
        )

        if target is None:
            raise KeyError(
                "unresolved construction reference: "
                + expr.ref_id
            )

        return expand_references(
            target,
            lookup,
            stack + (expr.ref_id,),
        )

    assert expr.left is not None
    assert expr.right is not None

    return binary(
        expr.op,
        expand_references(
            expr.left,
            lookup,
            stack,
        ),
        expand_references(
            expr.right,
            lookup,
            stack,
        ),
    )


@dataclass
class SemanticMemoryEntry:
    memory_id: str
    spec: ConstructionSpec
    quotient_signature: int
    contexts: set[str] = field(
        default_factory=set
    )
    observations: int = 0
    successful_transfers: int = 0
    failed_transfers: int = 0
    cumulative_gain_ppm: int = 0

    @property
    def complexity(self) -> int:
        return description_length(
            self.spec.expression
        )


class VerifiedConstructionMemory:
    """Persistent memory grouped by predictive quotient."""

    FORMAT = "prime-m21-semantic-memory-v1"

    def __init__(self) -> None:
        self.entries: dict[
            str,
            SemanticMemoryEntry,
        ] = {}

    @staticmethod
    def _memory_id(
        quotient_signature: int,
    ) -> str:
        return (
            "pq:"
            + format(
                quotient_signature,
                "x",
            )
        )

    def ingest_registry(
        self,
        registry: ConstructionRegistry,
        *,
        context_id: str,
    ) -> tuple[str, ...]:
        receipts = (
            registry.receipts.records
        )

        if not verify_receipt_chain(
            receipts,
            expected_count=len(
                receipts
            ),
        ):
            raise ValueError(
                "registry receipt chain invalid"
            )

        lookup = {
            construction_id: (
                record.spec.expression
            )
            for construction_id, record
            in registry._records.items()
        }

        touched = []

        for record in (
            registry.active_records()
        ):
            portable = (
                expand_references(
                    record.spec.expression,
                    lookup,
                )
            )

            signature = (
                predictive_partition_signature(
                    portable,
                    max_lag=8,
                )
            )

            memory_id = (
                self._memory_id(
                    signature
                )
            )

            portable_spec = (
                ConstructionSpec(
                    expression=portable,
                    proposal_source=(
                        "verified-semantic-memory"
                    ),
                )
            )

            current = (
                self.entries.get(
                    memory_id
                )
            )

            if current is None:
                current = (
                    SemanticMemoryEntry(
                        memory_id=memory_id,
                        spec=portable_spec,
                        quotient_signature=(
                            signature
                        ),
                    )
                )

                self.entries[
                    memory_id
                ] = current

            elif (
                description_length(
                    portable_spec.expression
                )
                <
                description_length(
                    current.spec.expression
                )
            ):
                # Prefer the simpler representative of the same
                # predictive quotient class.
                current.spec = (
                    portable_spec
                )

            current.contexts.add(
                context_id
            )

            current.observations += 1

            touched.append(
                memory_id
            )

        return tuple(
            sorted(
                set(touched)
            )
        )

    def record_transfer_outcome(
        self,
        memory_id: str,
        *,
        accepted: bool,
        gain_ppm: int,
    ) -> None:
        entry = self.entries[
            memory_id
        ]

        if accepted:
            entry.successful_transfers += 1
        else:
            entry.failed_transfers += 1

        entry.cumulative_gain_ppm += (
            gain_ppm
        )

    def to_dict(self) -> dict:
        return {
            "format": self.FORMAT,
            "entries": [
                {
                    "memory_id": (
                        entry.memory_id
                    ),
                    "expression": (
                        entry.spec.expression.to_dict()
                    ),
                    "quotient_signature": (
                        str(
                            entry.quotient_signature
                        )
                    ),
                    "contexts": sorted(
                        entry.contexts
                    ),
                    "observations": (
                        entry.observations
                    ),
                    "successful_transfers": (
                        entry.successful_transfers
                    ),
                    "failed_transfers": (
                        entry.failed_transfers
                    ),
                    "cumulative_gain_ppm": (
                        entry.cumulative_gain_ppm
                    ),
                }
                for entry
                in sorted(
                    self.entries.values(),
                    key=lambda row: (
                        row.memory_id
                    ),
                )
            ],
        }

    def save(
        self,
        path: str | Path,
    ) -> None:
        Path(path).write_text(
            json.dumps(
                self.to_dict(),
                sort_keys=True,
                indent=2,
            )
            + "\n"
        )

    @classmethod
    def load(
        cls,
        path: str | Path,
    ) -> "VerifiedConstructionMemory":
        payload = json.loads(
            Path(path).read_text()
        )

        if (
            payload.get("format")
            != cls.FORMAT
        ):
            raise ValueError(
                "unsupported semantic memory format"
            )

        memory = cls()

        for row in payload[
            "entries"
        ]:
            expression = (
                expr_from_dict(
                    row[
                        "expression"
                    ]
                )
            )

            spec = ConstructionSpec(
                expression=expression,
                proposal_source=(
                    "verified-semantic-memory"
                ),
            )

            entry = SemanticMemoryEntry(
                memory_id=row[
                    "memory_id"
                ],
                spec=spec,
                quotient_signature=int(
                    row[
                        "quotient_signature"
                    ]
                ),
                contexts=set(
                    row[
                        "contexts"
                    ]
                ),
                observations=int(
                    row[
                        "observations"
                    ]
                ),
                successful_transfers=int(
                    row[
                        "successful_transfers"
                    ]
                ),
                failed_transfers=int(
                    row[
                        "failed_transfers"
                    ]
                ),
                cumulative_gain_ppm=int(
                    row[
                        "cumulative_gain_ppm"
                    ]
                ),
            )

            expected_id = (
                cls._memory_id(
                    entry.quotient_signature
                )
            )

            if (
                expected_id
                != entry.memory_id
            ):
                raise ValueError(
                    "semantic memory identity mismatch"
                )

            memory.entries[
                entry.memory_id
            ] = entry

        return memory
