"""Cross-world verified-construction transfer."""

from __future__ import annotations

from dataclasses import dataclass

from core.construction.grammar import (
    description_length,
)
from core.construction.registry import (
    ConstructionRegistry,
)
from core.construction.types import (
    ConstructionSpec,
)

from .memory import (
    VerifiedConstructionMemory,
)
from .proposal_field import (
    DistributedProposalField,
)


@dataclass(frozen=True)
class TransferProposal:
    memory_id: str
    spec: ConstructionSpec
    score: int
    reasons: tuple[str, ...]
    state_commit_authorized: bool = False


class TransferEngine:
    def __init__(
        self,
        memory: (
            VerifiedConstructionMemory
        ),
        field: (
            DistributedProposalField
        ),
    ) -> None:
        self.memory = memory
        self.field = field

    def recall(
        self,
        *,
        context_tokens: tuple[
            str,
            ...,
        ],
        max_candidates: int = 32,
    ) -> tuple[
        TransferProposal,
        ...,
    ]:
        proposals = []

        for entry in (
            self.memory.entries.values()
        ):
            spec = ConstructionSpec(
                expression=(
                    entry.spec.expression
                ),
                proposal_source=(
                    "cross-world-transfer"
                ),
            )

            learned_score = (
                self.field.score(
                    spec,
                    context_tokens,
                )
            )

            prior = (
                100
                * entry.successful_transfers
                - 120
                * entry.failed_transfers
                + (
                    entry.cumulative_gain_ppm
                    // 10_000
                )
                + 4
                * len(
                    entry.contexts
                )
                - description_length(
                    spec.expression
                )
            )

            proposals.append(
                TransferProposal(
                    memory_id=(
                        entry.memory_id
                    ),
                    spec=spec,
                    score=(
                        learned_score
                        + prior
                    ),
                    reasons=(
                        "verified-memory",
                        "predictive-quotient",
                        "learned-routing",
                    ),
                )
            )

        proposals.sort(
            key=lambda row: (
                -row.score,
                row.memory_id,
                row.spec.construction_id,
            )
        )

        return tuple(
            proposals[
                :max_candidates
            ]
        )

    def stage(
        self,
        registry: ConstructionRegistry,
        proposals: tuple[
            TransferProposal,
            ...,
        ],
    ) -> tuple[str, ...]:
        staged = []

        for proposal in proposals:
            # Registry proposal is deliberately not authority.
            registry.propose(
                proposal.spec
            )

            staged.append(
                proposal.spec.construction_id
            )

        return tuple(staged)
