# Thinking System Monorepo Roadmap

This document outlines active development goals and planned research milestones. Roadmap items represent planned work and are explicitly separated from verified capabilities.

---

## Phase 1: Canonical Monorepo Stabilization (Current)

* [x] Reconstruct `BoggersTheAI` into canonical `thinking-system` monorepo.
* [x] Establish unified `TSKernel` transaction authority and `ts` CLI.
* [x] Consolidate baseline documentation, inventory, and ADR decision records.
* [x] Enforce automated architecture dependency checks in CI.

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
