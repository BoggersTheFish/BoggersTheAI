# TS Benchmark Roadmap Implementation

## Phase 0: Truth Audit And Scope Lock

Status: partially implemented.

- Created isolated `TS-Benchmarks` repo scaffold.
- Implemented first Workstream A scaling harness.
- Added receipt schema and report generation.

## Phase 1: TS-Core Scaling Harness

Status: first executable slice implemented.

Next additions:

- Add NetworkX and belief propagation baselines behind optional dependencies.
- Add noise sweeps and context-splitting metrics.
- Add 100k-node performance target and memory report.
- Add CI smoke that runs only 100/1k-node tests.

## Phase 2: Reasoning Benchmark Harness

Status: not implemented.

Planned modules:

- `ts_benchmarks/tasks/reasoning.py`
- `ts_benchmarks/runners/reasoning.py`
- `ts_benchmarks/baselines/llm_baselines.py`
- `ts_benchmarks/metrics/reasoning_metrics.py`

## Phase 3: TensionLM Matched Baseline Campaign

Status: not implemented.

Planned integration:

- Adapter for `bozo/tensionlm`.
- Matched softmax control configs.
- Param/token/compute receipt fields.

## Phase 4: Hardware Microbenchmarks

Status: placeholder package only.

Planned scripts:

- `ts_benchmarks/hardware/microbenchmark_edge_relaxation.py`
- `ts_benchmarks/hardware/benchmark_sparse_vs_dense.py`
- `ts_benchmarks/hardware/benchmark_incremental_update.py`
- `ts_benchmarks/hardware/benchmark_gpu_tension_kernel.py`
- `ts_benchmarks/hardware/benchmark_background_evolution.py`

## Phase 5: Hybrid Contradiction Demo

Status: placeholder package only.

Recommended first domain: AI safety / model evaluation papers, because it is high-value and lower-liability than medical/legal advice domains.
