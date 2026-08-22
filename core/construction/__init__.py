"""PRIME M20 adaptive representation construction."""

from .composition import (
    generate_composed_candidates,
)
from .compositional_engine import (
    CandidateFieldSnapshot,
    CompositionalAdaptiveConstructionEngine,
)
from .engine import (
    AdaptiveConstructionEngine,
    ConstructionDecision,
    VerifierGate,
)
from .grammar import (
    binary,
    dependencies,
    description_length,
    evaluate,
    generate_bounded_candidates,
    lag,
    ref,
    required_history,
)
from .graph_projection import (
    project_registry,
)
from .library import (
    load_library,
    save_library,
    snapshot_registry,
    validate_library,
)
from .registry import (
    ConstructionRegistry,
)
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
    "CandidateFieldSnapshot",
    "CompositionalAdaptiveConstructionEngine",
    "ConstructionDecision",
    "ConstructionRegistry",
    "ConstructionSpec",
    "ConstructionStatus",
    "FeatureExpr",
    "FeatureOp",
    "VerifierGate",
    "binary",
    "dependencies",
    "description_length",
    "evaluate",
    "generate_bounded_candidates",
    "generate_composed_candidates",
    "lag",
    "load_library",
    "project_registry",
    "ref",
    "required_history",
    "save_library",
    "snapshot_registry",
    "validate_library",
]
