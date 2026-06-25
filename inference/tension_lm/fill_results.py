"""
fill_results.py — patch README.md with actual comparison numbers after training.

Run after both training runs complete:
    python3 fill_results.py
"""
import csv
import os
import re


def best_val_ppl(csv_path: str) -> float | None:
    if not os.path.exists(csv_path):
        return None
    best = float("inf")
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if row.get("val_ppl"):
                v = float(row["val_ppl"])
                if v < best:
                    best = v
    return best if best < float("inf") else None


def final_train_ppl(csv_path: str) -> float | None:
    if not os.path.exists(csv_path):
        return None
    last = None
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if row.get("train_ppl"):
                last = float(row["train_ppl"])
    return last


def main():
    t_val   = best_val_ppl("logs/tension.csv")
    b_val   = best_val_ppl("logs/transformer.csv")
    t_train = final_train_ppl("logs/tension.csv")
    b_train = final_train_ppl("logs/transformer.csv")

    if t_val is None or b_val is None:
        print("Training logs incomplete — run both train.py jobs first.")
        return

    readme = open("README.md").read()

    # Replace placeholder rows in the results table
    readme = re.sub(
        r"\| Best val PPL \| \*\(training\)\* \| \*\(training\)\* \|",
        f"| Best val PPL | **{t_val:.1f}** | **{b_val:.1f}** |",
        readme,
    )
    readme = re.sub(
        r"\| Final train PPL \| \*\(training\)\* \| \*\(training\)\* \|",
        f"| Final train PPL | {t_train:.1f} | {b_train:.1f} |",
        readme,
    )

    winner = "TensionLM" if t_val < b_val else "Transformer"
    delta  = abs(t_val - b_val)
    note   = (
        f"\n> **Result:** {winner} wins by {delta:.1f} PPL points "
        f"(TensionLM {t_val:.1f} vs Transformer {b_val:.1f} on WikiText-2 val).\n"
    )
    readme = readme.replace(
        "Plot: `results/comparison.png` (generated after both runs finish)",
        f"Plot: `results/comparison.png`{note}",
    )

    open("README.md", "w").write(readme)
    print(f"README.md updated with results.")
    print(f"  TensionLM   best val PPL: {t_val:.2f}  |  final train PPL: {t_train:.2f}")
    print(f"  Transformer best val PPL: {b_val:.2f}  |  final train PPL: {b_train:.2f}")
    print(f"  Winner: {winner}  (gap: {delta:.1f})")


if __name__ == "__main__":
    main()
