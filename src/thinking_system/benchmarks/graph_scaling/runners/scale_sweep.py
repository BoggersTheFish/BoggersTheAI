"""Run a deterministic sweep over graph sizes and graph families."""

from __future__ import annotations

import argparse
from pathlib import Path

from thinking_system.benchmarks.graph_scaling.runners.scale_graph import (
    build_parser as build_scale_parser,
)
from thinking_system.benchmarks.graph_scaling.runners.scale_graph import (
    run_one,
)


def _split_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _split_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        required=True,
        help="Comma-separated node counts, e.g. 100,1000,10000",
    )
    parser.add_argument("--graphs", required=True, help="Comma-separated graph types")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--avg-degree", type=int, default=6)
    parser.add_argument("--contradiction-rate", type=float, default=0.01)
    parser.add_argument("--steps", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.12)
    parser.add_argument("--damping", type=float, default=0.85)
    parser.add_argument("--tolerance", type=float, default=1e-4)
    parser.add_argument("--no-frontier", action="store_true")
    parser.add_argument("--no-provenance-weighting", action="store_true")
    parser.add_argument(
        "--update-policy",
        default="reference",
        choices=[
            "reference",
            "degree_normalized",
            "hub_damping",
            "residual_redistribution",
        ],
    )
    parser.add_argument("--hub-percentile", type=float, default=0.95)
    parser.add_argument("--hub-damping-factor", type=float, default=0.35)
    parser.add_argument("--nonhub-frontier-fraction", type=float, default=0.30)
    parser.add_argument("--out-dir", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    scale_parser = build_scale_parser()
    completed = []
    for graph in _split_strings(args.graphs):
        for nodes in _split_ints(args.sizes):
            out_path = out_dir / f"{graph}_{nodes}_seed{args.seed}.json"
            scale_args = scale_parser.parse_args(
                [
                    "--nodes",
                    str(nodes),
                    "--graph",
                    graph,
                    "--seed",
                    str(args.seed),
                    "--avg-degree",
                    str(args.avg_degree),
                    "--contradiction-rate",
                    str(args.contradiction_rate),
                    "--steps",
                    str(args.steps),
                    "--learning-rate",
                    str(args.learning_rate),
                    "--damping",
                    str(args.damping),
                    "--tolerance",
                    str(args.tolerance),
                    "--out",
                    str(out_path),
                    "--update-policy",
                    args.update_policy,
                    "--hub-percentile",
                    str(args.hub_percentile),
                    "--hub-damping-factor",
                    str(args.hub_damping_factor),
                    "--nonhub-frontier-fraction",
                    str(args.nonhub_frontier_fraction),
                ]
                + (["--no-frontier"] if args.no_frontier else [])
                + (
                    ["--no-provenance-weighting"]
                    if args.no_provenance_weighting
                    else []
                )
            )
            payload = run_one(scale_args, out_path)
            completed.append(payload["run_id"])
            print(f"completed {payload['run_id']} -> {out_path}")

    print(f"completed {len(completed)} scaling runs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
