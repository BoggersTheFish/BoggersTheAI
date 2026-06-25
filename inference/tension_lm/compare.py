"""
compare.py — plot TensionLM vs Transformer loss curves
=======================================================
Reads the CSV logs written by train.py --log_csv and produces a side-by-side
comparison chart saved to results/comparison.png.

Usage (after both training runs finish):
    python3 compare.py \\
        --tension   logs/tension.csv \\
        --transformer logs/transformer.csv \\
        --out       results/comparison.png
"""

import argparse
import csv
import os
from pathlib import Path


def read_csv(path: str):
    """Return (train_steps, train_ppls, val_steps, val_ppls)."""
    train_steps, train_ppls = [], []
    val_steps,   val_ppls   = [], []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            step = int(row["step"])
            if row["train_ppl"]:
                train_steps.append(step)
                train_ppls.append(float(row["train_ppl"]))
            if row["val_ppl"]:
                val_steps.append(step)
                val_ppls.append(float(row["val_ppl"]))
    return train_steps, train_ppls, val_steps, val_ppls


def plot(tension_csv: str, transformer_csv: str, out_path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    ts_t, tp_t, vs_t, vp_t = read_csv(tension_csv)
    ts_b, tp_b, vs_b, vp_b = read_csv(transformer_csv)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("TensionLM vs Transformer — WikiText-2", fontsize=14, fontweight="bold")

    # ── Train PPL ──
    ax = axes[0]
    ax.set_title("Train perplexity (lower is better)")
    if ts_t:
        ax.plot(ts_t, tp_t, label="TensionLM",   color="#2196F3", linewidth=1.8)
    if ts_b:
        ax.plot(ts_b, tp_b, label="Transformer", color="#F44336", linewidth=1.8, linestyle="--")
    ax.set_xlabel("Optimiser steps")
    ax.set_ylabel("Perplexity")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
    ax.legend()
    ax.grid(True, alpha=0.3)

    # ── Val PPL ──
    ax = axes[1]
    ax.set_title("Validation perplexity (lower is better)")
    if vs_t:
        ax.plot(vs_t, vp_t, "o-", label="TensionLM",   color="#2196F3", linewidth=1.8)
    if vs_b:
        ax.plot(vs_b, vp_b, "s--", label="Transformer", color="#F44336", linewidth=1.8)
    ax.set_xlabel("Optimiser steps")
    ax.set_ylabel("Perplexity")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Summary annotation
    if vp_t and vp_b:
        best_t = min(vp_t)
        best_b = min(vp_b)
        winner = "TensionLM" if best_t < best_b else "Transformer"
        delta  = abs(best_t - best_b)
        fig.text(
            0.5, 0.01,
            f"Best val PPL — TensionLM: {best_t:.1f}  |  Transformer: {best_b:.1f}  "
            f"|  Gap: {delta:.1f}  ({winner} wins)",
            ha="center", fontsize=10, color="#333333",
        )

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(out_path, dpi=150)
    print(f"Saved → {out_path}")

    # Text summary to stdout
    print("\n── Results summary ─────────────────────────────")
    if vp_t:
        print(f"  TensionLM   best val PPL: {min(vp_t):.2f}")
    if vp_b:
        print(f"  Transformer best val PPL: {min(vp_b):.2f}")
    if vp_t and vp_b:
        winner = "TensionLM" if min(vp_t) < min(vp_b) else "Transformer"
        print(f"  Winner: {winner}")


def main():
    p = argparse.ArgumentParser(description="Plot TensionLM vs Transformer comparison")
    p.add_argument("--tension",     required=True, help="CSV log from TensionLM run")
    p.add_argument("--transformer", required=True, help="CSV log from Transformer run")
    p.add_argument("--out",         default="results/comparison.png")
    args = p.parse_args()

    for path in [args.tension, args.transformer]:
        if not os.path.exists(path):
            raise SystemExit(f"File not found: {path}")

    plot(args.tension, args.transformer, args.out)


if __name__ == "__main__":
    main()
