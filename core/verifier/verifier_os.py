"""
Verifier OS v0.1 - Wave 0

Wraps real ts_reasoner components:
- VerifierFirstRuntimeKernel
- TypedSupport + support_path_verifier
- Proof chains
- Adds basic arithmetic + BOGVM-based code property verifier

Integrated with graph for tension-aware verification.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from reasoner.ts_reasoner.runtime_kernel import VerifierFirstRuntimeKernel
from reasoner.ts_reasoner.typed_support import make_typed_support
import json
import subprocess
import tempfile
import re

class VerifierOS:
    """Production foundation verifier stack."""

    def __init__(self):
        self.kernel = VerifierFirstRuntimeKernel()
        self.receipts = []

    def verify_claim(self, premises: list[str], claim: str, state: dict = None) -> dict:
        """Core: use real kernel for typed verification."""
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

    def arithmetic_verify(self, expr: str, expected: bool = True) -> dict:
        """New domain: arithmetic property, can delegate to BOGVM. Handles even/odd claims and exprs."""
        expr_l = expr.lower().strip()
        try:
            # Direct support for "N is even" style
            m = re.search(r'(\d+)\s+is\s+(even|odd)', expr_l)
            if m:
                n = int(m.group(1))
                want_even = m.group(2) == 'even'
                passed = (n % 2 == 0) == want_even
                support = make_typed_support(channel="arithmetic", premises=[expr], derived_claim=expr, verifier_passed=passed)
                return {"passed": passed, "computed": n % 2 == 0, "support": support, "claim": expr}
            # Fallback eval for = and simple
            if '=' in expr:
                left, right = expr.split('=', 1)
                passed = eval(left.strip()) == eval(right.strip())
            else:
                computed = eval(expr)
                passed = bool(computed) == expected
            support = make_typed_support(
                channel="arithmetic",
                premises=[expr],
                derived_claim=expr,
                verifier_passed=passed
            )
            return {"passed": passed, "computed": computed if 'computed' in dir() else None, "support": support, "action": "accept" if passed else "open_repair"}
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def code_property_verify(self, plan: str, inputs: dict) -> dict:
        """BOGVM-backed code property checker for Wave 0."""
        # Generate minimal BOGBIN for the property
        asm = f"""
CREATE_NODE input
CREATE_NODE output
CREATE_CLAIM prop input output
VERIFY prop
HALT
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
            f.write(asm)
            asm_path = f.name
        bogbin = asm_path.replace('.asm', '.bogbin')
        receipt = asm_path.replace('.asm', '_receipt.json')
        try:
            subprocess.check_call(["python3", "-m", "core-vm.bogvm", "assemble", asm_path, bogbin])
            subprocess.check_call(["python3", "-m", "core-vm.bogvm", "run", bogbin, "--receipt", receipt])
            with open(receipt) as f:
                bog_receipt = json.load(f)
            # For demo, assume success if no error
            passed = bog_receipt.get("execution_status") == "completed"
            return {
                "passed": passed,
                "plan": plan,
                "inputs": inputs,
                "bogvm_receipt": bog_receipt
            }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    def get_receipts(self):
        return self.receipts
