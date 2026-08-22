"""PRIME M20 adaptive representation construction."""

from .engine import (
    AdaptiveConstructionEngine,
    ConstructionDecision,
    VerifierGate,
)
from .grammar import (
    binary,
    description_length,
    evaluate,
    generate_bounded_candidates,
    lag,
    required_history,
)
from .registry import ConstructionRegistry
from .types import (
    AuthorityAction,
    ConstructionSpec,
    ConstructionStatus,
    FeatureExpr,
    FeatureOp,
)

__all__ = [
    "AdaptiveConstructionEngine",
    "AuthorityAction",
    "ConstructionDecision",
    "ConstructionRegistry",
    "ConstructionSpec",
    "ConstructionStatus",
    "FeatureExpr",
    "FeatureOp",
    "VerifierGate",
    "binary",
    "description_length",
    "evaluate",
    "generate_bounded_candidates",
    "lag",
    "required_history",
]
