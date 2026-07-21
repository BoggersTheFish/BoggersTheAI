# Thinking System Monorepo Roadmap

This document outlines active development goals and planned research milestones. Roadmap items represent planned work and are explicitly separated from verified capabilities.

---

## Phase 1: Canonical Monorepo Stabilization (Current)

* [ ] Finish physical monorepo layout (`packages/` / full `src/` moves); currently facades + legacy trees.
* [x] Establish `TSKernel` transaction authority (`core/kernel`) and `ts` CLI (`thinking_system.apps.cli`).
* [x] Baseline documentation, inventory, ADRs, and evidence-backed import ledger (claims must stay honest).
* [x] Architecture authority checks in CI (denylist for kernel layers; not a full package DAG yet).

---

## Phase 2: Verifier & Substrate Expansion

* [ ] Expand BOGVM instruction set and observation predicate verifiers.
* [ ] Integrate OpenCL GPU compute kernels (`engines/tension-forge`) into wave runner.
* [ ] Formalize TSLC dialogue compiler state machine (`packages/ts-language`).

---

## Phase 3: Research & Sealed Evaluation

* [ ] Execute sealed adversarial benchmark evaluations across `benchmarks/adversarial/`.
* [ ] Complete semantic-orbit correctness flip study (`research/genesis/`).
* [ ] Formalize observer family birth and residual localization calculus (`research/observer-birth/`).
