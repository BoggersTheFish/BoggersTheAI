#!/usr/bin/env python3
"""
Wave 0 Gate Demo — First non-toy verifiable capability demo

This is the runnable artifact for the Wave 0 of the GPT-5.5+ TS roadmap.

Implements the full pipeline using the Wave 0 implementations:
- Language: TSLCCompiler
- Graph + Waves + BOGVM: real UniversalLivingGraph with attach/spawn
- Verifier: VerifierOS (real kernel + BOGVM property)
- Full receipt

Run:
  cd /home/boggersthefish/workspace/BoggersTheAI
  PYTHONPATH=. python3 experiments/frontier/wave0_gate_demo.py
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, ".")

from core.graph.universal_living_graph import UniversalLivingGraph
from core.language.tslc import TSLCCompiler
from core.verifier.verifier_os import VerifierOS


def stable_hash(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]


def main():
    print("=" * 72)
    print("WAVE 0 GATE DEMO — Implementing the GPT-5.5+ plan")
    print("=" * 72)

    problem = "All even numbers are integers. 2 + 2 = 4. Prove that 4 is even. Execute a plan to confirm."
    print(f"\nProblem: {problem}")

    # Language
    lang = TSLCCompiler()
    compiled = lang.compile(problem)
    premises = compiled["graph_deltas"]["premises"]
    obligations = compiled["verifier_obligations"]
    goal = obligations[0] if obligations else "4 is even"
    print(f"Parsed premises: {premises}")
    print(f"Goal: {goal}")

    # Real Graph + Waves + BOGVM support
    g = UniversalLivingGraph(auto_load=False)
    for p in premises:
        nid = "p_" + str(hash(p))[:8]
        g.add_node(node_id=nid, content=p)

    print("\nRunning waves...")
    for _ in range(4):
        g.run_wave_cycle()
    tens = g.detect_tensions()
    print(f"Tensions: {list(tens.items())[:2]}")

    # Verifier OS (real kernel)
    print("\nVerifier...")
    ver = VerifierOS()
    ver_res = ver.verify_claim(premises, goal)
    print(f"Action: {ver_res['action']}")
    print(f"Explanation: {ver_res['explanation']}")
    print(f"Passed: {ver_res['support']['verifier_passed']}")

    # BOGVM execution using real graph method
    print("\nBOGVM execution...")
    asm = """CREATE_NODE four
CREATE_NODE even
CREATE_CLAIM c1 four even
VERIFY c1
HALT
"""
    asm_p = "/tmp/gate.asm"
    bin_p = "/tmp/gate.bogbin"
    with open(asm_p, "w") as f:
        f.write(asm)
    subprocess.check_call(["python3", "-m", "core-vm.bogvm", "assemble", asm_p, bin_p])
    nid = list(g.nodes.keys())[0]
    g.attach_bogvm_program(nid, bin_p)
    bog_res = g.spawn_bogvm_simulation(nid)
    print(f"BOGVM status: {bog_res.get('status')}")

    # Receipt
    receipt = {
        "problem": problem,
        "premises": premises,
        "goal": goal,
        "wave_tensions": tens,
        "verifier": ver_res,
        "bogvm": bog_res,
        "receipt_hash": stable_hash({"goal": goal, "status": bog_res.get("status")}),
    }

    print("\n=== FULL GLASS-BOX RECEIPT ===")
    print(json.dumps(receipt, indent=2))

    out = Path("artifacts/wave0_gate_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2))
    print(f"\nSaved to {out}")

    print(
        "\nWave 0 implemented: Real components unified, BOGVM in graph, verifier stack, language, execution, receipts."
    )
    print("This is the foundation for the GPT-5.5+ TS system.")


if __name__ == "__main__":
    main()
