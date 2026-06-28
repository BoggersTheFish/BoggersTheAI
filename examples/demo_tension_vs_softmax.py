#!/usr/bin/env python3
"""
BoggersTheAI / TS-OS
Mathematical Demonstration: The Softmax Illusion vs. Sigmoid Tension

Run this script to observe why standard LLM attention (Softmax) inherently
fails at multi-constraint logic, and why TS-OS uses Causal Tension Fields.
"""

import math


def softmax(logits):
    """Standard attention: Zero-sum statistical interpolation."""
    # Subtract max for numerical stability (standard practice)
    m = max(logits)
    exp_vals = [math.exp(val - m) for val in logits]
    sum_exp = sum(exp_vals)
    return [e / sum_exp for e in exp_vals]


def sigmoid_tension(logits):
    """TS-OS reasoning: Independent constraint resolution."""
    # T(x) = 1 / (1 + e^-x)
    return [1 / (1 + math.exp(-val)) for val in logits]


def print_receipt(title, inputs, soft_out, tens_out):
    print(f"\n{'='*60}")
    print(f" EXPERIMENT: {title}")
    print(f"{'='*60}")
    print("INPUT ENERGY (Graph Nodes):")
    print(" " + str([round(x, 2) for x in inputs]))
    print("\n[Softmax Attention] - Token Prediction Paradigm:")
    print(" " + str([round(x, 3) for x in soft_out]))
    print(
        f" -> Sum: {round(sum(soft_out), 2)} | Status: {'Diluted' if len(inputs) > 2 else 'Stable'}"
    )

    print("\n[Sigmoid Tension] - Cognitive Physics Paradigm:")
    print(" " + str([round(x, 3) for x in tens_out]))
    print(f" -> System Energy Maintained: {round(sum(tens_out), 2)} / {len(inputs)}")
    print("-" * 60)


def run_demo():
    print("\n>>> INITIALIZING BOGVM-0 LOGIC SANDBOX <<<")

    # Phase 1: Two valid constraints
    # Imagine two logical constraints are heavily supported by context (Energy = 4.0)
    claims_2 = [4.0, 4.0]
    print_receipt(
        "SCENARIO A: Two Competing Truths",
        claims_2,
        softmax(claims_2),
        sigmoid_tension(claims_2),
    )

    # Phase 2: The Softmax Collapse
    # Now imagine the context reveals 8 more equally valid, necessary constraints.
    # The absolute energy of the original claims hasn't changed, but look what happens.
    claims_10 = [4.0] * 10
    print_receipt(
        "SCENARIO B: Ten Competing Truths (The Dilution Effect)",
        claims_10,
        softmax(claims_10),
        sigmoid_tension(claims_10),
    )

    print("\n>>> CONCLUSION <<<")
    print("Notice SCENARIO B:")
    print("1. Softmax diluted perfectly valid truths down to 0.100 (10%).")
    print(
        "   It treats 10 undeniable facts as 'uncertainty' because it forces a zero-sum choice."
    )
    print("   It cannot hold a complex state in mind; it must predict one next token.")
    print("2. Sigmoid Tension holds all constraints at 0.982.")
    print("   The Truth Graph remains stable. Wave propagation resolves constraints.")
    print("\nThought is not token prediction.")
    print("See docs/anti-token-prediction.md for the full architectural proof.\n")


if __name__ == "__main__":
    run_demo()
