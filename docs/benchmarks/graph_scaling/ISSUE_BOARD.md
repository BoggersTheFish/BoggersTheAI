# TS-Benchmarks Issue Board

This is the local issue board seed. Convert these into GitHub issues when the repo is pushed.

## Workstream A: Scaling TS-Core

- [ ] Issue #1: Scale-free graphs retain high final tension under reference relaxation config.
- [x] Create benchmark package skeleton.
- [x] Add deterministic graph generators.
- [x] Add sparse active-frontier reference relaxation.
- [x] Add first baselines.
- [x] Add receipt schema and writer.
- [x] Run 100/1k/10k sweep.
- [ ] Add NetworkX propagation baseline.
- [ ] Add belief propagation and loopy belief propagation baselines.
- [ ] Add noise sweep runner.
- [ ] Add context-splitting score.
- [ ] Add 100k-node performance target.
- [x] Add v0.2 Scale-Free Failure Decomposition task.
- [x] Run v0.2 decomposition receipt from clean commit and attach result to Issue #1.
- [x] Open Issue #2 for v0.3 hub-normalized relaxation ablation.
- [ ] Run v0.3 ablation receipt from clean experimental branch and attach result to Issue #2.
- [x] Open Issue #4 for v0.4 topology-aware policy selection.
- [x] Run v0.4 selector receipt from clean experimental branch and attach result to Issue #4.

## Workstream B: Hard Reasoning Benchmarks

- [ ] Define shared reasoning task JSONL schema.
- [ ] Add TS-Reasoner adapter.
- [ ] Add Llama/Qwen/Mistral baseline adapter.
- [ ] Add no-tension, no-provenance, no-repair ablations.
- [ ] Add Tier 0 synthetic sanity runner.
- [ ] Add Tier 1 ARC-style runner.

## Workstream C: Hardware Viability

- [ ] Add sparse vs dense CPU benchmark.
- [ ] Add torch sparse prototype.
- [ ] Add Triton tension kernel microbenchmark.
- [ ] Add hardware receipt fields for CUDA and VRAM.

## Workstream D: Hybrid Demo

- [ ] Choose first low-liability corpus: AI safety/model evaluation papers.
- [ ] Add document manifest schema.
- [ ] Add claim extraction adapter.
- [ ] Add contradiction report renderer.
- [ ] Add baseline LLM/RAG/TS side-by-side report.

## Public Communication

- [ ] Publish limitations page before benchmark claims.
- [ ] Publish receipts page with checksums.
- [ ] Publish first progress note with the scale-free failure mode included.
