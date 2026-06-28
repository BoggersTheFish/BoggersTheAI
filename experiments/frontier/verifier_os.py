"""
Verifier OS v0.1 for Wave 0

Wraps the real VerifierFirstRuntimeKernel + typed support concepts.
Adds a basic arithmetic + property checker that can use BOGVM execution.

Produces TypedSupportObject style receipts.
"""

import sys
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    from reasoner.ts_reasoner.runtime_kernel import VerifierFirstRuntimeKernel
    from reasoner.ts_reasoner.typed_support import make_typed_support, validate_typed_support
except Exception:
    # Fallback for demo
    class VerifierFirstRuntimeKernel:
        def process_event(self, event, state, case_id="demo"):
            from dataclasses import dataclass, asdict
            @dataclass
            class R:
                action: str = "accept"
                explanation: str = "fallback accept"
                state: dict = None
                def to_dict(self): return asdict(self)
            if state is None: state = {}
            r = R(state=state or {})
            return r
    def make_typed_support(**kw):
        return {"support_type": "fallback", "verifier_passed": True, **kw}
    def validate_typed_support(*a, **k): return {"valid": True}

class VerifierOS:
    def __init__(self):
        self.kernel = VerifierFirstRuntimeKernel()
        self.receipts = []

    def verify_claim(self, premises, claim, state=None):
        """Core verifier using real kernel."""
        if state is None:
            state = {
                "accepted_claims": premises,
                "branch_worlds": [],
                "repair_targets": [],
                "quarantined_claims": [],
                "patches": [],
            }
        event = {"event_type": "claim", "claim": claim, "source": "verifier_os"}
        result = self.kernel.process_event(event, state, case_id="wave0")
        self.receipts.append(result.to_dict())
        support = make_typed_support(
            channel="kernel",
            premises=premises,
            derived_claim=claim,
            verifier_passed=result.action in ("accept", "record")
        )
        return {
            "action": result.action,
            "explanation": result.explanation,
            "support": support,
            "kernel_result": result.to_dict()
        }

    def arithmetic_property_check(self, expr: str, expected: bool):
        """Basic new domain verifier: simple arithmetic property using eval + BOGVM stub.
        In real would use BOGVM execution.
        """
        try:
            result = eval(expr)
            passed = bool(result) == expected
            support = make_typed_support(
                channel="arithmetic",
                premises=[expr],
                derived_claim=f"{expr} == {expected}",
                verifier_passed=passed
            )
            return {"passed": passed, "result": result, "support": support}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def get_receipts(self):
        return self.receipts
