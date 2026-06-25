"""Tiny learned candidate model for TS-Reasoner.

The model proposes and ranks candidate claims. TS-Reasoner typed channels remain
the verifier and proof authority.
"""

from .dataset import build_cases, label_case
from .features import extract_candidate_features
from .model import TinyCandidateModel

__all__ = ["TinyCandidateModel", "build_cases", "extract_candidate_features", "label_case"]
