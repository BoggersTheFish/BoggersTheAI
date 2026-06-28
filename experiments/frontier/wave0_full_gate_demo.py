#!/usr/bin/env python3
"""
Wave 0 Full Gate Demo: Integrated runnable system

Uses:
- language_compiler for parsing to deltas/obligations/plan
- verifier_os for verification (real kernel + arithmetic)
- bogvm_graph_bridge + real BOGVM CLI for execution
- scale graph sim for waves
- hard_tasks.json for input
- self_data_generator for proposer (stub)

Produces full receipt for a non-toy task.

Run:
  python3 experiments/frontier/wave0_full_gate_demo.py

This is the gate artifact for Wave 0.
"""

import json
import sys
import subprocess
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.frontier.language_compiler import LanguageCompiler
from experiments.frontier.verifier_os import VerifierOS
from experiments.frontier.bogvm_graph_bridge import attach_bogvm_program, run_attached_bogvm
from experiments.frontier.self_data_generator import SelfDataGenerator

class MiniWaveGraph:
    def __init__(self):
        self.nodes = {}
        self.edges = []
        self.bogvm_programs = {}

    def add_node(self, content):
        nid = len(self.nodes)
        self.nodes[nid] = {"id": nid, "content": content, "activation": 0.2}
        return nid

    def add_edge(self, s, t):
        self.edges.append((s, t))

    def run_waves(self, steps=5):
        for _ in range(steps):
            updates = {}
            for s, t in self.edges:
                if s in self.nodes:
                    updates[t] = updates.get(t, 0) + self.nodes[s]["activation"] * 0.12
            for nid, d in updates.items():
                self.nodes[nid]["activation"] = min(1.0, self.nodes[nid]["activation"] + d)

    def detect_tensions(self):
        return {nid: abs(n["activation"] - 0.2) for nid, n in self.nodes.items()}

    def snapshot(self):
        return {"nodes": len(self.nodes)}

def load_tasks():
    with open("experiments/frontier/hard_tasks.json") as f:
        return json.load(f)

def main(task_id="t1"):
    print("=== Wave 0 Full Gate Demo ===")
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), tasks[0])
    print(f"Task: {task['text']}")

    # 1. Language
    compiler = LanguageCompiler()
    compiled = compiler.compile(task["text"])
    print(f"Compiled: {compiled}")

    # 2. Graph + Waves
    g = MiniWaveGraph()
    for p in compiled["graph_deltas"]["premises"]:
        nid = g.add_node(p)
        if "are" in p:
            parts = p.split(" are ")
            g.add_node(parts[1].strip())
    g.run_waves(5)
    print(f"After waves, tensions: {g.detect_tensions()}")

    # 3. Verifier
    verifier = VerifierOS()
    premises = compiled["graph_deltas"]["premises"]
    claims = compiled["verifier_obligations"] or [task["expected"]]
    ver_results = []
    for claim in claims:
        res = verifier.verify_claim(premises, claim)
        ver_results.append(res)
        if res["support"]["verifier_passed"]:
            print(f"Verified: {claim}")
    print(f"Verifier results: {ver_results}")

    # 4. Proposer (self data stub)
    gen = SelfDataGenerator()
    traces = gen.generate_synthetic(20)
    high = gen.filter_high_quality()
    rules = gen.train_proposer_stub(high)
    proposals = []
    for nid, node in g.nodes.items():
        prop = gen.propose(node["content"], rules)
        proposals.append(prop)
    print(f"Proposals: {proposals[:2]}")

    # 5. BOGVM execution via bridge
    execution = {"executed": False}
    try:
        # simple asm
        asm = "CREATE_NODE four\nCREATE_NODE even\nCREATE_CLAIM c1 four even\nVERIFY c1\nHALT\n"
        with open("/tmp/gate.asm", "w") as f: f.write(asm)
        subprocess.check_call(["python3", "-m", "core-vm.bogvm", "assemble", "/tmp/gate.asm", "/tmp/gate.bogbin"])
        attach_bogvm_program(g, 0, "/tmp/gate.bogbin")
        bog_r = run_attached_bogvm(g, 0)
        execution = {"executed": True, "bogvm_receipt": bog_r}
    except Exception as e:
        execution = {"executed": False, "error": str(e)}

    # Receipt
    receipt = {
        "task": task,
        "compiled": compiled,
        "wave_tensions": g.detect_tensions(),
        "verifier_results": ver_results,
        "proposals": proposals,
        "execution": execution,
        "receipt_hash": "wave0_full"
    }
    print("\n=== FULL GATE RECEIPT ===")
    print(json.dumps(receipt, indent=2))
    out = Path("artifacts/wave0_full_gate_receipt.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2))
    print(f"Saved to {out}")

if __name__ == "__main__":
    main()
