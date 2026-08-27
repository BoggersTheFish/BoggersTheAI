"""Bounded structured problem analysis under PRIME v19 authority."""

from .authority import (
    ExistingProblemAnalysis,
    PreparedProblemAnalysis,
    ProblemAnalysisWorkflow,
    WorkflowAuthorityKeys,
    WorkflowBuildError,
    build_problem_workflow_kernel,
)
from .canonical import (
    FLOAT_HEX_TAG,
    WorkflowCanonicalizationError,
    canonical_tree_is_valid,
    canonicalize_source,
    contains_native_float,
    workflow_stable_hash,
)
from .model import (
    AdviceProtocol,
    ProblemSpec,
    ProblemSpecError,
    WorkflowOutcome,
    WorkflowState,
)
from .validators import (
    CONSTRAINT_FIELD_OBLIGATION,
    PROBLEM_NODE_KIND,
    PROVENANCE_OBLIGATION,
    REPRESENTATION_ECONOMICS_OBLIGATION,
    WORKFLOW_BOUNDARY_OBLIGATION,
    constraint_field_integrity_v1,
    provenance_binding_v1,
    representation_economics_v1,
    workflow_boundary_v1,
)

__all__ = [
    "AdviceProtocol",
    "CONSTRAINT_FIELD_OBLIGATION",
    "ExistingProblemAnalysis",
    "FLOAT_HEX_TAG",
    "PROBLEM_NODE_KIND",
    "PROVENANCE_OBLIGATION",
    "PreparedProblemAnalysis",
    "ProblemAnalysisWorkflow",
    "ProblemSpec",
    "ProblemSpecError",
    "REPRESENTATION_ECONOMICS_OBLIGATION",
    "WORKFLOW_BOUNDARY_OBLIGATION",
    "WorkflowAuthorityKeys",
    "WorkflowBuildError",
    "WorkflowCanonicalizationError",
    "WorkflowOutcome",
    "WorkflowState",
    "build_problem_workflow_kernel",
    "canonical_tree_is_valid",
    "canonicalize_source",
    "constraint_field_integrity_v1",
    "contains_native_float",
    "provenance_binding_v1",
    "representation_economics_v1",
    "workflow_boundary_v1",
    "workflow_stable_hash",
]
