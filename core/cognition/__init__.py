"""PRIME M21 persistent adaptive cognition."""

from .engine import (
    CognitionSnapshot,
    MegaPrimeCognition,
)
from .episodic import (
    EpisodeRecord,
    EpisodicMemory,
)
from .memory import (
    SemanticMemoryEntry,
    VerifiedConstructionMemory,
    expand_references,
)
from .meta import (
    MetaLearningLedger,
    ProposalSourceStats,
)
from .planner import (
    VerifiedPlan,
    VerifiedPlanner,
)
from .proposal_field import (
    DistributedProposalField,
    RankedCandidate,
)
from .schema import (
    SchemaMiner,
    SchemaProposal,
)
from .study import (
    ActiveStudySelector,
    StudyAction,
    StudyProposal,
)
from .transfer import (
    TransferEngine,
    TransferProposal,
)
from .world_model import (
    TransitionAuthorization,
    TransitionCandidate,
    TransitionVerifier,
    VerifiedWorldModel,
)

__all__ = [
    "ActiveStudySelector",
    "CognitionSnapshot",
    "DistributedProposalField",
    "EpisodeRecord",
    "EpisodicMemory",
    "MegaPrimeCognition",
    "MetaLearningLedger",
    "ProposalSourceStats",
    "RankedCandidate",
    "SchemaMiner",
    "SchemaProposal",
    "SemanticMemoryEntry",
    "StudyAction",
    "StudyProposal",
    "TransferEngine",
    "TransferProposal",
    "TransitionAuthorization",
    "TransitionCandidate",
    "TransitionVerifier",
    "VerifiedConstructionMemory",
    "VerifiedPlan",
    "VerifiedPlanner",
    "VerifiedWorldModel",
    "expand_references",
]

from .hypothesis_ecology import (
    HypothesisAllocation,
    WeightedEvidenceEpoch,
    allocate_hypothesis_mass,
)

from .causal_program import (
    CONFIGURATIONS,
    CausalProgram,
    ProgramOp,
    program_lookup,
    program_universe,
)
from .causal_certificate import (
    CausalAuthorization,
    CausalAuthorityLedger,
    compatible_program_ids,
    minimal_certificate,
    universe_hash,
)
from .causal_memory import (
    CausalMemoryEntry,
    CausalProgramMemory,
    CausalSchema,
)
