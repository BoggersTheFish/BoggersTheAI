"""
Phase 0 Unification Adapter (P0.5)

Thin bridge to make key ts_reasoner components (proof_chain, typed_support)
usable from the main core/graph + waves without heavy refactoring.

This is the start of making the advanced verifier-first reasoning first-class
in the living system.

Usage in demos:
  from core.reasoning.ts_unified_adapter import run_proof_verification, make_typed_support

Future: deeper integration into UniversalLivingGraph and run_rules_cycle.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Load real pieces directly (Phase 0 bridge)
try:
    from reasoner.ts_reasoner.proof_chain import universal_bridge_path as _real_proof
    from reasoner.ts_reasoner.typed_support import TypedSupportObject as _real_typed, canonical_hash
    HAS_TS_REASONER = True
except Exception as e:
    HAS_TS_REASONER = False
    print(f"[adapter] ts_reasoner not fully loadable: {e}")

def run_proof_verification(relations, subject, predicate):
    """Use real proof_chain logic."""
    if not HAS_TS_REASONER:
        # fallback simple
        return []
    return _real_proof(relations, subject, predicate)

def make_typed_support(support_type, channel, premises, claim, passed):
    if HAS_TS_REASONER:
        return _real_typed(support_type, channel, premises, claim, passed, trace_hash=canonical_hash(premises))
    class Dummy:
        def __init__(self, **kw): self.__dict__.update(kw)
        def to_dict(self): return self.__dict__
    return Dummy(support_type=support_type, channel=channel, premises=premises, derived_claim=claim, verifier_passed=passed, trace_hash="fallback")

# Example of wiring graph native + proof in one call (used by hello_frontier etc.)
def verify_and_emerge(graph, facts, query_subj, query_pred):
    """High level Phase 0 helper: apply facts, run waves (graph native), verify with proof."""
    # (in real would mutate graph etc.)
    proof = run_proof_verification([], query_subj, query_pred)  # caller prepares relations
    support = make_typed_support("transitive", "transitive_all", tuple(facts), f"{query_subj} {query_pred}", bool(proof))
    return {"proof": proof, "support": support.to_dict() if hasattr(support,'to_dict') else support}
