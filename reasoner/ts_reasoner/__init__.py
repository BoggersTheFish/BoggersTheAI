"""TS-Reasoner-v0: toy constraint-graph reasoning telemetry."""

from .benchmark import BenchmarkRunner, BenchmarkTask, load_benchmark
from .candidates import CandidateClaim, CandidateVerification
from .coupling_learner import train_residual_coupling_matrix
from .operation_router import OperationRouter
from .pipeline import TSReasoner, run_reasoner
from .tension_agents import TensionCoordinator
from .tensionproof_smoke import evaluate_tensionproof_smoke
from .types import ReasonerOutput, TensionAgentSignal


def run_tensionlm_candidate_bridge(*args, **kwargs):
    """Load the optional TS-Core-backed candidate bridge only when invoked."""
    from .candidate_bridge import (
        run_tensionlm_candidate_bridge as _run_tensionlm_candidate_bridge,
    )

    return _run_tensionlm_candidate_bridge(*args, **kwargs)


def load_tensionlm_export_jsonl(*args, **kwargs):
    """Load the optional TensionLM adapter only when invoked."""
    from .tensionlm_adapter import (
        load_tensionlm_export_jsonl as _load_tensionlm_export_jsonl,
    )

    return _load_tensionlm_export_jsonl(*args, **kwargs)


def run_tensionlm_export_jsonl(*args, **kwargs):
    """Load the optional TensionLM adapter only when invoked."""
    from .tensionlm_adapter import (
        run_tensionlm_export_jsonl as _run_tensionlm_export_jsonl,
    )

    return _run_tensionlm_export_jsonl(*args, **kwargs)


__all__ = [
    "BenchmarkRunner",
    "BenchmarkTask",
    "CandidateClaim",
    "CandidateVerification",
    "OperationRouter",
    "ReasonerOutput",
    "TSReasoner",
    "TensionAgentSignal",
    "TensionCoordinator",
    "evaluate_tensionproof_smoke",
    "load_benchmark",
    "load_tensionlm_export_jsonl",
    "run_reasoner",
    "run_tensionlm_candidate_bridge",
    "run_tensionlm_export_jsonl",
    "train_residual_coupling_matrix",
]
