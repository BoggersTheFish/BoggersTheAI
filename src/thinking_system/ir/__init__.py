"""
Typed Intermediate Representation (`thinking_system.ir`).
"""

# COMPATIBILITY_FACADE: re-exports implementation from legacy top-level packages.


from core.kernel.ir import (
    ClaimNode,
    EntityNode,
    EvidenceNode,
    Provenance,
    RelationEdge,
    TSIRDocument,
    TSOperation,
    VerifierObligation,
)

__all__ = [
    "TSIRDocument",
    "TSOperation",
    "EntityNode",
    "ClaimNode",
    "RelationEdge",
    "EvidenceNode",
    "VerifierObligation",
    "Provenance",
]
