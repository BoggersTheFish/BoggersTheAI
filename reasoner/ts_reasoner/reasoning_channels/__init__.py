"""Reasoning-specific typed tension channels."""

from __future__ import annotations

import sys
from pathlib import Path

sibling = Path(__file__).resolve().parents[2].parent / "TS-Core"
if sibling.exists() and str(sibling) not in sys.path:
    sys.path.insert(0, str(sibling))

from .confidence_abstention import ConfidenceAbstentionChannel
from .contradiction import ContradictionChannel
from .directionality import DirectionalityChannel
from .identity_preservation import IdentityPreservationChannel
from .logic_transitivity import LogicTransitivityChannel
from .quantifier_scope import QuantifierScopeChannel
from .surface_structure import SurfaceStructureChannel


def default_reasoning_channels():
    return [
        LogicTransitivityChannel(),
        IdentityPreservationChannel(),
        DirectionalityChannel(),
        SurfaceStructureChannel(),
        ConfidenceAbstentionChannel(),
        ContradictionChannel(),
        QuantifierScopeChannel(),
    ]


__all__ = [
    "ConfidenceAbstentionChannel",
    "ContradictionChannel",
    "DirectionalityChannel",
    "IdentityPreservationChannel",
    "LogicTransitivityChannel",
    "QuantifierScopeChannel",
    "SurfaceStructureChannel",
    "default_reasoning_channels",
]
