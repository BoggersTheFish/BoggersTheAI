"""
TSLC v0.2 - Deterministic Language to Verifier Obligations

For Wave 0: compile text to graph deltas + obligations + plan skeleton.

Uses logic from ts_chat / reasoner.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


class TSLCCompiler:
    """Deterministic compiler per Wave 0 plan. Improved claim extraction for real formal tasks."""

    def compile(self, text: str) -> dict:
        """Parse to structured output for graph + verifier + BOGVM."""
        lower = text.lower().strip()
        premises = []
        obligations = []
        plan = []

        # Extract "all X are Y" premises
        for m in re.finditer(r"all (.+?) are (.+?)(?:[.,;]|$)", lower):
            subj = m.group(1).strip()
            pred = m.group(2).strip()
            premises.append(f"all {subj} are {pred}")

        # Extract "X is Y" direct facts
        for m in re.finditer(r"(\w+(?:\s+\w+)*)\s+is\s+(\w+(?:\s+\w+)*)", lower):
            subj = m.group(1).strip()
            pred = m.group(2).strip()
            if len(subj) > 0 and len(pred) > 0 and subj not in ["prove", "all", "that"]:
                premises.append(f"{subj} is {pred}")

        # Arithmetic statements like "2 + 2 = 4"
        for m in re.finditer(
            r"([\d\w\s\+\-\*\/\(\)]+?)\s*=\s*([\d\w\s\+\-\*\/\(\)]+)", lower
        ):
            left = m.group(1).strip()
            right = m.group(2).strip()
            if left and right:
                premises.append(f"{left} = {right}")

        # Extract claim from "prove ..." or "prove that ..."
        claim = None
        if "prove that" in lower:
            claim = lower.split("prove that")[-1].strip().rstrip(".")
        elif "prove" in lower:
            claim = lower.split("prove")[-1].strip().rstrip(".")
        elif "show that" in lower:
            claim = lower.split("show that")[-1].strip().rstrip(".")

        if claim:
            # Clean obvious trailing junk
            claim = re.sub(
                r"\s+(using a plan|execute|confirm|if tension|propose|then use agency|and execute|and confirm).*$",
                "",
                claim,
                flags=re.I,
            ).strip()
            obligations.append(claim)
            plan.append({"step": "verify", "target": claim})

        # Plan steps
        if "execute" in lower or "confirm" in lower or "bogvm" in lower:
            plan.append(
                {"step": "bogvm_execute", "plan": "confirm result via execution"}
            )

        if "decompose" in lower or "agency" in lower:
            plan.append({"step": "decompose", "target": "subgoals"})

        if not premises:
            premises = [text]

        if not obligations and claim is None:
            # Fallback: if no prove, last sentence-ish as potential claim
            parts = re.split(r"[.!?]", text)
            last = parts[-1].strip() if parts else text
            if last and len(last) > 3:
                obligations.append(last.lower())
                plan.append({"step": "verify", "target": last})

        # Question / general query support for more LLM-like behavior
        if not obligations and (
            "?" in text
            or text.lower().startswith(("what", "how", "why", "where", "who", "which"))
        ):
            # Extract a focus claim like "capital of france is ?" or treat query as obligation to "answer/verify"
            focus = text.strip().rstrip("?")
            obligations.append(f"answer: {focus}")
            plan.append({"step": "retrieve_and_synthesize", "target": focus})

        return {
            "graph_deltas": {"premises": premises},
            "verifier_obligations": obligations,
            "plan_skeleton": plan,
        }

    def compile_to_receipt(self, text: str) -> dict:
        compiled = self.compile(text)
        return {"input": text, "output": compiled}
