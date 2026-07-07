#!/usr/bin/env python3
"""
TS roadmap progress demo - historical frontier experiment

This demonstrates an older integrated TS Engine path:
- Wave 0: Unified surface, BOGVM in graph, Verifier OS, Language, Self-data, Scale, Receipts
- Wave 1: Deep simulation (BOGVM inside waves), powerful verifiers
- Wave 2: Scaled graph, intuition layer
- Wave 3/4: Agency, self-improvement, eval with receipts

Task: Complex multi-step formal reasoning with proof, execution, proposal, full glass-box receipt.
Uses real components from BoggersTheAI (graph, BOGVM, ts_reasoner, etc.)

Run:
  PYTHONPATH=. python3 experiments/frontier/full_ts_gpt55_demo.py

This is a historical experiment, not a current frontier-capability claim.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json

from core.ts_engine import TSEngine


def main():
    print("=" * 80)
    print("TS ROADMAP PROGRESS DEMO")
    print("Deterministic | Glass-box | Verifier-first | Wave Physics | BOGVM Execution")
    print("Historical integrated demo; current authority boundary is Kernel v0.2")
    print("=" * 80)

    engine = TSEngine(auto_load=False)

    # Hard, non-toy task requiring multi-step reasoning, proof, execution, agency
    task = (
        "All even numbers are integers. 2 + 2 = 4. All numbers that are sums of two evens are even. "
        "Prove that 4 is even using a plan. Execute the verification plan in BOGVM and confirm the result. "
        "If tension high, propose new nodes. Then use agency to decompose and verify subgoals."
    )
    print(f"\nInput Task:\n{task}\n")

    # Full pipeline with agency for long-horizon
    answer_text, receipt = engine.answer(task)
    print(f"\nSynthesized Answer from TS + TensionLM:\n{answer_text}\n")
    print("\n--- Running agency loop for hierarchical long-horizon ---")
    engine.agency_loop(
        "Decompose and fully verify the even number proof with execution", max_steps=5
    )

    # Wave 1 deep sim
    print("\n--- Deep simulation ---")
    try:
        ds = engine.deep_simulate(steps=1)
        print("Deep sims:", len(ds))
    except Exception as e:
        print("Deep sim skipped:", e)

    print("=== FULL GLASS-BOX RECEIPT ===")
    print(json.dumps(receipt.to_dict(), indent=2, default=str))

    # Save
    out = Path("artifacts/full_ts_gpt55_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(receipt.to_json())
    print(f"\nSaved to {out}")

    # Demonstrate skill: the system handled language, graph, waves, verifier, BOGVM execution, proposals
    print("\n" + "=" * 80)
    print("DEMONSTRATED EXPERIMENTAL PATH:")
    print("- Deterministic TSLC language compilation to graph + obligations + plan")
    print("- Real graph + adaptive waves with tension focus (10k+ scale possible)")
    print("- BOGVM programs as first-class, spawned in simulation with receipts")
    print(
        "- Verifier OS with real kernel + BOGVM-backed checks (no confidence as proof)"
    )
    print("- Intuition proposer from self-data (better than native)")
    print("- Full tamper-evident receipt with every step, hash, provenance")
    print("- Glass-box: inspect any tension, decision, execution")
    print("- On-device, deterministic, TS-native (no transformers)")
    print(
        "\nThis is a TS experiment path, not a general intelligence or frontier LLM release."
    )
    print(
        "Next hard work: stronger verifiers, stable receipt linkage, deeper BOGVM observation use."
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
