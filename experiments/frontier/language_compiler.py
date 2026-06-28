"""
Deterministic Language Compiler (TSLC v0.2) for Wave 0

Takes natural language, outputs:
- Graph deltas (premises as nodes/edges)
- Verifier obligations (claims to prove)
- Skeleton plan (steps that can map to BOGVM)

Uses logic from ts_chat.
"""

import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

class LanguageCompiler:
    def __init__(self):
        self.premises = []
        self.obligations = []
        self.plan = []

    def compile(self, text: str):
        """Parse text into structured output."""
        lower = text.lower().strip()
        premises = []
        obligations = []
        plan_steps = []

        # Extract "all X are Y" style
        for match in re.finditer(r'all (.+?) are (.+?)(?:[.,]|$)', lower):
            subj = match.group(1).strip()
            pred = match.group(2).strip()
            premises.append(f"all {subj} are {pred}")

        # Simple goal extraction
        if "prove that" in lower:
            claim = lower.split("prove that")[-1].strip().rstrip(".")
            obligations.append(claim)
            plan_steps.append({"step": "prove", "claim": claim})

        if "execute" in lower or "confirm" in lower:
            plan_steps.append({"step": "execute", "action": "run verification plan"})

        if not premises and not obligations:
            premises = [text]

        self.premises = premises
        self.obligations = obligations
        self.plan = plan_steps

        return {
            "graph_deltas": {"premises": premises},
            "verifier_obligations": obligations,
            "plan_skeleton": plan_steps
        }

    def to_receipt(self):
        return {
            "premises": self.premises,
            "obligations": self.obligations,
            "plan": self.plan
        }
