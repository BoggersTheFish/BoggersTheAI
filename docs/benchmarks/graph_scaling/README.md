> **Canonical location:** This benchmark workstream was imported from
> `BoggersTheFish/TS-Benchmarks` into the Thinking System monorepo.
> Commands below use the canonical package namespace.

# TS-Benchmarks

`TS-Benchmarks` is the audit-first benchmark harness for the Thinking System ecosystem.

This is not a victory-lap repo. It is a falsification harness. The first result shows clean relaxation on some graph families and failure on scale-free graphs, which is now the next target.

The first implemented slice is Workstream A: scalable graph/tension tests for TS-Core-style relaxation. It creates deterministic synthetic graphs, injects contradictions, runs a sparse active-frontier relaxation loop, compares against simple baselines, and writes auditable receipts.

## Current Status

Implemented:

- deterministic graph generators: random, scale-free, small-world, knowledge-like, provenance, temporal, multi-context
- TS-style tension relaxation reference implementation
- degree and PageRank-like localization baselines
- scaling CLIs with JSON receipts
- receipt JSON schema
- markdown/CSV report generation
- smoke tests

Not implemented yet:

- hard reasoning benchmark runners
- TensionLM matched softmax campaign
- GPU/Triton hardware microbenchmarks
- hybrid Graph+LLM contradiction demo

## Quickstart

```bash
python3 -m unittest discover -s tests -p 'test*.py'
python -m thinking_system.benchmarks.graph_scaling.runners.scale_graph --nodes 1000 --graph scale_free --seed 42 --out artifacts/scaling/scale_free_1000.json
python -m thinking_system.benchmarks.graph_scaling.runners.scale_sweep --sizes 100,1000,10000 --graphs random,scale_free,small_world --seed 42 --out-dir artifacts/scaling
python -m thinking_system.benchmarks.graph_scaling.reports.plot_scaling --in-dir artifacts/scaling --out-dir artifacts/scaling/report
```

v0.2 failure decomposition:

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.scale_free_decomposition \
  --sizes 100,1000,10000 \
  --seed 42 \
  --out-dir artifacts/decomposition
```

v0.3 experimental hub-normalization ablation:

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.hub_normalization_ablation \
  --sizes 100,1000,10000 \
  --graphs scale_free,random,small_world \
  --seed 42 \
  --out-dir artifacts/hub-normalization
```

v0.4 experimental topology-aware selector:

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.topology_policy_selection \
  --sizes 100,1000,10000 \
  --graphs scale_free,random,small_world \
  --seed 42 \
  --out-dir artifacts/topology-policy
```

Optional plot generation uses dev dependencies only:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m thinking_system.benchmarks.graph_scaling.reports.plot_scaling --in-dir artifacts/scaling --out-dir artifacts/scaling/report
```

## Issue #1

Scale-free graphs retain high final tension under the reference relaxation config. See `docs/issues/001-scale-free-residual-tension.md`.

## v0.2 Task

`Scale-Free Failure Decomposition` asks whether the scale-free failure is caused by hub dominance, bad damping/plateau behavior, poor contradiction scoring, or active-frontier policy. It intentionally diagnoses the failure before changing the relaxation algorithm.

## v0.3 Experimental Branch

`Hub-Normalized Relaxation Ablation` tests three remedies against the reference config:

- degree-normalized update
- hub damping
- residual redistribution

The branch is experimental. A positive result means the remedy helped seeded synthetic graphs, not that TS-Core scales cleanly.

## v0.4 Experimental Branch

`Topology-Aware Relaxation Policy Selection` tests whether pre-run topology diagnostics can select a safer policy:

- hub-heavy graphs select degree normalization
- non-hub-heavy graphs keep the reference active-frontier policy

The selector uses graph diagnostics only, not outcome metrics.

This is not yet evidence of universal scaling; it is evidence that topology diagnostics can prevent a known policy tradeoff in the current synthetic sweep.

## Claim Boundary

This repo does not prove TS is a transformer replacement. It measures specific graph/tension behavior under specified configs and emits receipts that can be audited.
