"""
First Serious Self-Data Generator for Wave 0

Uses the unified VerifierOS, TSLC, graph to generate traces on hard_tasks.
Filters to success.
Stubs Tension proposer improvement.

Run:
  python3 experiments/frontier/generate_self_data.py
"""

import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from experiments.frontier.verifier_os import VerifierOS
from experiments.frontier.language_compiler import LanguageCompiler as TSLCCompiler
from experiments.frontier.self_data_generator import SelfDataGenerator  # reuse for proposer

def main():
    verifier = VerifierOS()
    compiler = TSLCCompiler()
    gen = SelfDataGenerator()

    with open("experiments/frontier/hard_tasks.json") as f:
        tasks = json.load(f)

    traces = []
    for task in tasks:
        compiled = compiler.compile(task["text"])
        premises = compiled["graph_deltas"]["premises"]
        for claim in compiled["verifier_obligations"] or [task["expected"]]:
            res = verifier.verify_claim(premises, claim)
            trace = {
                "task_id": task["id"],
                "text": task["text"],
                "premises": premises,
                "claim": claim,
                "verifier": res,
                "success": res["support"]["verifier_passed"]
            }
            traces.append(trace)

    high = [t for t in traces if t["success"]]
    rules = gen.train_proposer_stub(high)

    print(f"Generated {len(traces)} traces, {len(high)} high-quality")
    print("Sample trained rules:", list(rules.items())[:2])

    with open("artifacts/self_data_traces.json", "w") as f:
        json.dump(traces, f, indent=2)

    print("Saved to artifacts/self_data_traces.json")
    # In real, fine-tune TensionLM here using bozo/ pipeline

if __name__ == "__main__":
    main()
