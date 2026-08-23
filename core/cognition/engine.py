"""Integrated PRIME M21 persistent adaptive cognition engine."""

from __future__ import annotations

from dataclasses import dataclass

from core.construction.registry import (
    ConstructionRegistry,
)

from .episodic import (
    EpisodicMemory,
)
from .memory import (
    VerifiedConstructionMemory,
)
from .meta import (
    MetaLearningLedger,
)
from .planner import (
    VerifiedPlanner,
)
from .proposal_field import (
    DistributedProposalField,
)
from .schema import (
    SchemaMiner,
)
from .study import (
    ActiveStudySelector,
    StudyAction,
)
from .transfer import (
    TransferEngine,
    TransferProposal,
)
from .world_model import (
    TransitionVerifier,
    VerifiedWorldModel,
)


@dataclass(frozen=True)
class CognitionSnapshot:
    semantic_memory_classes: int
    episodes: int
    verified_transition_rules: int
    meta_sources: int


class MegaPrimeCognition:
    """Persistent cognitive layer above frozen M20 construction."""

    def __init__(self) -> None:
        self.semantic_memory = (
            VerifiedConstructionMemory()
        )

        self.episodic_memory = (
            EpisodicMemory()
        )

        self.proposal_field = (
            DistributedProposalField()
        )

        self.meta_memory = (
            MetaLearningLedger()
        )

        self.transfer_engine = (
            TransferEngine(
                self.semantic_memory,
                self.proposal_field,
            )
        )

        self.study_selector = (
            ActiveStudySelector()
        )

        self.world_model = (
            VerifiedWorldModel()
        )

        self.transition_verifier = (
            TransitionVerifier()
        )

        self.planner = (
            VerifiedPlanner(
                self.world_model
            )
        )

        self.schema_miner = (
            SchemaMiner()
        )

    def close_world(
        self,
        registry: ConstructionRegistry,
        *,
        context_id: str,
        context_tokens: tuple[
            str,
            ...,
        ],
        reward_ppm: int,
        tensions: tuple[
            str,
            ...,
        ] = (),
        studies: tuple[
            str,
            ...,
        ] = (),
    ) -> tuple[str, ...]:
        touched = (
            self.semantic_memory.ingest_registry(
                registry,
                context_id=context_id,
            )
        )

        self.episodic_memory.append(
            context_id=context_id,
            context_tokens=(
                context_tokens
            ),
            verified_construction_ids=tuple(
                sorted(
                    registry.active_ids()
                )
            ),
            reward_ppm=(
                reward_ppm
            ),
            tensions=tensions,
            studies=studies,
        )

        return touched

    def open_world(
        self,
        registry: ConstructionRegistry,
        *,
        context_tokens: tuple[
            str,
            ...,
        ],
        max_transfer: int = 32,
    ) -> tuple[
        TransferProposal,
        ...,
    ]:
        proposals = (
            self.transfer_engine.recall(
                context_tokens=(
                    context_tokens
                ),
                max_candidates=(
                    max_transfer
                ),
            )
        )

        self.transfer_engine.stage(
            registry,
            proposals,
        )

        return proposals

    def record_transfer_result(
        self,
        proposal: TransferProposal,
        *,
        context_tokens: tuple[
            str,
            ...,
        ],
        accepted: bool,
        gain_ppm: int,
    ) -> None:
        self.semantic_memory.record_transfer_outcome(
            proposal.memory_id,
            accepted=accepted,
            gain_ppm=gain_ppm,
        )

        self.proposal_field.update(
            proposal.spec,
            context_tokens,
            accepted=accepted,
            gain_ppm=gain_ppm,
        )

        self.meta_memory.record(
            "cross-world-transfer",
            accepted=accepted,
            gain_ppm=gain_ppm,
        )

    def choose_study(
        self,
        actions: tuple[
            StudyAction,
            ...,
        ],
    ):
        ranked = (
            self.study_selector.rank(
                actions
            )
        )

        if not ranked:
            return None

        return ranked[0]

    def observe_transition(
        self,
        state: tuple[int, ...],
        action: str,
        next_state: tuple[int, ...],
    ) -> None:
        self.world_model.observe(
            state,
            action,
            next_state,
        )

    def verify_transition(
        self,
        state: tuple[int, ...],
        action: str,
    ):
        candidate = (
            self.world_model.propose_rule(
                state,
                action,
            )
        )

        if candidate is None:
            return None

        authorization = (
            self.transition_verifier.authorize(
                candidate
            )
        )

        if authorization.verdict:
            self.world_model.apply(
                authorization
            )

        return (
            candidate,
            authorization,
        )

    def plan(
        self,
        start_state: tuple[int, ...],
        goal_state: tuple[int, ...],
        *,
        max_depth: int = 16,
    ):
        return self.planner.plan(
            start_state,
            goal_state,
            max_depth=max_depth,
        )

    def mine_schemas(self):
        return (
            self.schema_miner.mine(
                self.semantic_memory
            )
        )

    def snapshot(
        self,
    ) -> CognitionSnapshot:
        return CognitionSnapshot(
            semantic_memory_classes=len(
                self.semantic_memory.entries
            ),
            episodes=len(
                self.episodic_memory.records
            ),
            verified_transition_rules=len(
                self.world_model.verified
            ),
            meta_sources=len(
                self.meta_memory.sources
            ),
        )
