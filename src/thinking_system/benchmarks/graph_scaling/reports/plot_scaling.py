"""Generate scaling CSV, markdown, and optional PNG plots from run JSON."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_runs(in_dir: Path) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for path in sorted(in_dir.glob("*.json")):
        if path.name.endswith(".receipt.json"):
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if "graph" in payload and "metrics" in payload:
            payload["_path"] = str(path)
            runs.append(payload)
    return runs


def write_csv(runs: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "run_id",
        "graph_type",
        "nodes",
        "edges",
        "runtime_s",
        "peak_rss_mb",
        "iterations",
        "initial_global_tension",
        "final_global_tension",
        "contradiction_localization_f1",
        "degree_baseline_f1",
        "pagerank_like_baseline_f1",
        "random_residual_baseline_f1",
        "plateau_step",
        "hub_residual_tension_share",
        "edges_relaxed_per_s",
    ]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for run in runs:
            row = {
                "run_id": run["run_id"],
                "graph_type": run["graph"]["type"],
                "nodes": run["graph"]["nodes"],
                "edges": run["graph"]["edges"],
                "degree_baseline_f1": run["baselines"]["degree"]["f1"],
                "pagerank_like_baseline_f1": run["baselines"]["pagerank_like"]["f1"],
                "random_residual_baseline_f1": run["baselines"]["random_residual"][
                    "f1"
                ],
            }
            row.update(
                {
                    field: run["metrics"].get(field)
                    for field in fields
                    if field not in row
                }
            )
            writer.writerow(row)


def write_markdown(runs: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    failed_scale_free = [
        run
        for run in runs
        if run["graph"]["type"] == "scale_free"
        and (
            float(run["metrics"]["final_global_tension"]) > 0.05
            or float(run["metrics"]["contradiction_localization_f1"]) == 0.0
        )
    ]
    lines = [
        "# TS-Core Scaling Report",
        "",
        "TS-Benchmarks is not a victory-lap repo. It is a falsification harness. The first result shows clean relaxation on some graph families and failure on scale-free graphs, which is now the next target.",
        "",
        "This report is generated from local benchmark receipts. It is not a capability claim and not a transformer comparison.",
        "",
        "## What Worked",
        "",
        *worked_lines(runs),
        "",
        "## What Failed",
        "",
        *failed_lines(runs),
        "",
        "## What This Means",
        "",
        "- The reference relaxation path can reduce injected tension on some sparse synthetic graph families.",
        "- The same reference config is not yet robust to scale-free hub structure.",
        "- Scale-free failure is a useful target because real knowledge graphs often have hub-heavy structure.",
        "- These results justify diagnostics and kernel work; they do not justify broad capability claims.",
        "",
        "## Next Experiment",
        "",
        "- Add hub-aware relaxation controls: degree-normalized updates, hub clipping, and per-context hub splitting.",
        "- Re-run the same 100/1k/10k scale-free sweep before changing the claim boundary.",
        "- Add NetworkX, belief-propagation, and Bayesian provenance baselines.",
        "",
        "## Summary Metrics",
        "",
        "| Run | Graph | Nodes | Edges | Runtime s | Peak MB | Final tension | F1 |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for run in runs:
        metrics = run["metrics"]
        lines.append(
            "| {run_id} | {graph} | {nodes} | {edges} | {runtime:.4f} | {mem:.2f} | {tension:.6f} | {f1:.3f} |".format(
                run_id=run["run_id"],
                graph=run["graph"]["type"],
                nodes=run["graph"]["nodes"],
                edges=run["graph"]["edges"],
                runtime=float(metrics["runtime_s"]),
                mem=float(metrics["peak_rss_mb"]),
                tension=float(metrics["final_global_tension"]),
                f1=float(metrics["contradiction_localization_f1"]),
            )
        )
    lines.extend(
        [
            "",
            "## Baseline Comparison",
            "",
            "| Run | TS F1 | Degree F1 | PageRank-like F1 | Random residual F1 | TS vs best baseline |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for run in runs:
        ts_f1 = float(run["metrics"]["contradiction_localization_f1"])
        baseline_f1s = {
            "degree": float(run["baselines"]["degree"]["f1"]),
            "pagerank_like": float(run["baselines"]["pagerank_like"]["f1"]),
            "random_residual": float(run["baselines"]["random_residual"]["f1"]),
        }
        best_name, best_f1 = max(baseline_f1s.items(), key=lambda item: item[1])
        if abs(ts_f1 - best_f1) < 1e-9:
            verdict = f"equivalent to {best_name}"
        elif ts_f1 > best_f1:
            verdict = f"wins by {ts_f1 - best_f1:.3f}"
        else:
            verdict = f"loses to {best_name} by {best_f1 - ts_f1:.3f}"
        lines.append(
            "| {run_id} | {ts:.3f} | {degree:.3f} | {pagerank:.3f} | {random_f1:.3f} | {verdict} |".format(
                run_id=run["run_id"],
                ts=ts_f1,
                degree=baseline_f1s["degree"],
                pagerank=baseline_f1s["pagerank_like"],
                random_f1=baseline_f1s["random_residual"],
                verdict=verdict,
            )
        )
    if failed_scale_free:
        lines.extend(["", "## Scale-Free Failure Diagnostics", ""])
        for run in failed_scale_free:
            diagnostics = run["diagnostics"]
            hub = diagnostics["hub_dominance"]
            confusion = diagnostics["contradiction_localization_confusion_matrix"]
            lines.extend(
                [
                    f"### {run['run_id']}",
                    "",
                    f"- Plateau step: {diagnostics['plateau_step']}",
                    f"- Hub residual tension share: {float(hub['hub_residual_tension_share']):.3f} at degree threshold {hub['hub_degree_threshold']}",
                    f"- Confusion matrix: TP={confusion['tp']} FP={confusion['fp']} FN={confusion['fn']} TN={confusion['tn']}",
                    f"- Active frontier first/last: {diagnostics['active_frontier_history'][:5]} -> {diagnostics['active_frontier_history'][-5:]}",
                    "",
                    "| Degree bucket | Nodes | Total tension | Avg tension | Max tension |",
                    "| --- | ---: | ---: | ---: | ---: |",
                ]
            )
            for bucket in diagnostics["tension_by_degree_bucket"]:
                lines.append(
                    "| {bucket} | {nodes} | {total:.6f} | {avg:.6f} | {max_tension:.6f} |".format(
                        bucket=bucket["bucket"],
                        nodes=bucket["nodes"],
                        total=float(bucket["total_tension"]),
                        avg=float(bucket["avg_tension"]),
                        max_tension=float(bucket["max_tension"]),
                    )
                )
            lines.extend(
                [
                    "",
                    "| Edge | Relation | Tension | Src degree | Dst degree | Provenance |",
                    "| ---: | --- | ---: | ---: | ---: | --- |",
                ]
            )
            for edge in diagnostics["top_residual_edges"][:10]:
                lines.append(
                    "| {idx} | {relation} | {tension:.6f} | {src_degree} | {dst_degree} | {provenance} |".format(
                        idx=edge["edge_index"],
                        relation=edge["relation"],
                        tension=float(edge["tension"]),
                        src_degree=edge["src_degree"],
                        dst_degree=edge["dst_degree"],
                        provenance=edge["provenance"],
                    )
                )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def worked_lines(runs: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for graph_type in sorted({run["graph"]["type"] for run in runs}):
        graph_runs = [run for run in runs if run["graph"]["type"] == graph_type]
        clean = [
            run
            for run in graph_runs
            if float(run["metrics"]["final_global_tension"]) < 0.01
            and float(run["metrics"]["contradiction_localization_f1"]) > 0.0
        ]
        if clean:
            max_nodes = max(run["graph"]["nodes"] for run in clean)
            lines.append(
                f"- `{graph_type}`: relaxed cleanly with nonzero localization up to {max_nodes} nodes."
            )
    return lines or ["- No graph family met the first-pass clean-relaxation threshold."]


def failed_lines(runs: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for run in runs:
        final_tension = float(run["metrics"]["final_global_tension"])
        f1 = float(run["metrics"]["contradiction_localization_f1"])
        if final_tension > 0.05 or f1 == 0.0:
            lines.append(
                f"- `{run['run_id']}`: final tension {final_tension:.6f}, contradiction-localization F1 {f1:.3f}."
            )
    return lines or ["- No run crossed the first-pass failure threshold."]


def write_optional_plots(runs: list[dict[str, Any]], out_dir: Path) -> list[Path]:
    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError:
        return []

    out_paths: list[Path] = []
    by_graph: dict[str, list[dict[str, Any]]] = {}
    for run in runs:
        by_graph.setdefault(run["graph"]["type"], []).append(run)

    for metric, filename, ylabel in [
        ("runtime_s", "runtime_vs_nodes.png", "Runtime (s)"),
        ("peak_rss_mb", "memory_vs_nodes.png", "Peak traced memory (MB)"),
        (
            "contradiction_localization_f1",
            "localization_f1_vs_nodes.png",
            "Localization F1",
        ),
    ]:
        plt.figure()
        for graph_type, graph_runs in sorted(by_graph.items()):
            graph_runs = sorted(graph_runs, key=lambda run: run["graph"]["nodes"])
            plt.plot(
                [run["graph"]["nodes"] for run in graph_runs],
                [run["metrics"][metric] for run in graph_runs],
                marker="o",
                label=graph_type,
            )
        plt.xscale("log")
        plt.xlabel("Nodes")
        plt.ylabel(ylabel)
        plt.legend()
        plt.tight_layout()
        out_path = out_dir / filename
        plt.savefig(out_path)
        plt.close()
        out_paths.append(out_path)
    return out_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    in_dir = Path(args.in_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = load_runs(in_dir)
    write_csv(runs, out_dir / "scaling_summary.csv")
    write_markdown(runs, out_dir / "SCALING_REPORT.md")
    plot_paths = write_optional_plots(runs, out_dir)
    print(f"wrote {len(runs)} runs to {out_dir}; plots={len(plot_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
