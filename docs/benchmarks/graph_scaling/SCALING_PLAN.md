# TS-Core Scaling Plan

## Purpose

This document pins the first benchmark slice for escaping the toy graph phase. The immediate goal is not to prove intelligence. The goal is to measure graph/tension stability, runtime, memory, and contradiction localization as graph size and structure change.

## Implemented Graph Families

- `random`: broad sparse baseline.
- `scale_free`: hub-heavy graph resembling knowledge concentration.
- `small_world`: local clusters plus rewired long links.
- `knowledge`: triple-like relation labels on sparse graph structure.
- `provenance`: source reliability weights.
- `temporal`: timestamped support edges.
- `multi_context`: context-tagged edges for future context splitting.

## Current CLI

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.scale_graph \
  --nodes 1000 \
  --graph scale_free \
  --seed 42 \
  --out artifacts/scaling/scale_free_1000.json

python -m thinking_system.benchmarks.graph_scaling.runners.scale_sweep \
  --sizes 100,1000,10000 \
  --graphs random,scale_free,small_world \
  --seed 42 \
  --out-dir artifacts/scaling

python -m thinking_system.benchmarks.graph_scaling.reports.plot_scaling \
  --in-dir artifacts/scaling \
  --out-dir artifacts/scaling/report
```

## Current Metrics

- `runtime_s`
- `peak_rss_mb`
- `iterations`
- `initial_global_tension`
- `final_global_tension`
- `tension_reduction`
- `converged`
- `oscillation_detected`
- `contradiction_localization_precision`
- `contradiction_localization_recall`
- `contradiction_localization_f1`
- `edges_relaxed`
- `edges_relaxed_per_s`

## Current Baselines

- `degree`: ranks nodes by weighted graph degree.
- `pagerank_like`: dependency-free diffusion baseline with contradiction boost.

These are not enough for publication. Next baselines should include NetworkX propagation, belief propagation, loopy belief propagation, a simple GNN, vector retrieval, and Bayesian provenance scoring.

## Acceptance Thresholds For First Public Receipt

- 100, 1k, and 10k-node runs complete for `random`, `scale_free`, and `small_world`.
- Every run emits a JSON result and a receipt with commit, command, seed, config, metrics, and artifact checksum.
- Report generation produces `SCALING_REPORT.md` and `scaling_summary.csv`.
- Any failed or oscillating run is reported as a failure, not hidden.

## Claim Boundary

Allowed after this slice:

> TS-Core-style reference relaxation has been tested on deterministic synthetic graphs up to N nodes with auditable runtime, memory, tension, and localization receipts.

Forbidden after this slice:

> TS scales to real knowledge graphs.
> TS beats transformers.
> TS solves hallucination.

## Public Framing

TS-Benchmarks is not a victory-lap repo. It is a falsification harness. The first result shows clean relaxation on some graph families and failure on scale-free graphs, which is now the next target.
