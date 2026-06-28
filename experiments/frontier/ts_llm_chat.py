#!/usr/bin/env python3
"""
TS LLM Chat - The full TS-based LLM interface.

This is the 'LLM' : use the TS engine for reasoning/verification, TensionLM for generation.

It's deterministic in the reasoning part, glass-box with receipts, on-device.

Run:
  PYTHONPATH=. python3 experiments/frontier/ts_llm_chat.py

Type queries, get synthesized answer + receipt.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from core.ts_engine import TSEngine


def main():
    print("TS LLM Chat (Wave 0-4 complete)")
    print("Reason with TS (graph/waves/verifiers/BOGVM), generate with real TensionLM.")
    print("Every answer comes with full receipt. Type 'quit' to exit.\n")

    engine = TSEngine(auto_load=False)

    while True:
        try:
            query = input("You: ").strip()
        except EOFError:
            break
        if query.lower() in ("quit", "exit", "q"):
            break
        if not query:
            continue
        answer, receipt = engine.answer(query)
        print(f"TS: {answer}")
        print(
            f"[Receipt: {receipt.receipt_hash} - {len(receipt.wave_trace)} waves, verifier passed: {any(v.get('support',{}).get('verifier_passed', False) for v in receipt.verifier_results)} ]"
        )
        print()


if __name__ == "__main__":
    main()
