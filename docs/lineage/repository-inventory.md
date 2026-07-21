# Thinking System Repository Inventory

This inventory documents all satellite and historical repositories inspected during the consolidation of the Thinking System research stack into the canonical `BoggersTheFish/thinking-system` monorepo.

---

## Repository Inventory Table

| Repository | Status | Purpose | Canonical Destination | Unique Contribution | Superseded By | Import Strategy | Provenance Notes | Archive Recommendation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `TS-Core` | Active Prototype | Rust/Python core kernel & vector memory | `packages/ts-core`, `packages/ts-kernel` | Rust-accelerated graph operations, Modelfile specs | Monorepo `packages/ts-core` | Selective port of core algorithms and memory specs | Derived from `BoggersTheFish/TS-Core` (`377284b`) | Archive after monorepo verification |
| `cig-ts-engine` | Active Prototype | Continuous information graph engine | `packages/ts-graph`, `packages/ts-runtime` | Obsidian export workflow, CIG graph schemas | Monorepo `packages/ts-graph` | Selective port of graph schemas and export tools | Derived from `BoggersTheFish/cig-ts-engine` (`71d91a6`) | Archive after monorepo verification |
| `TS-Benchmarks` | Active Harness | Audit-first falsification benchmark suite | `benchmarks/` | Topology-aware relaxation policies, audit schemas | Monorepo `benchmarks/` | Port benchmark suites, schemas, and failure datasets | Derived from `BoggersTheFish/TS-Benchmarks` (`7c0611f`) | Archive after monorepo verification |
| `ts-chat-language` | Active Compiler | Language compiler (TSLC) & DDS substrate | `packages/ts-language`, `apps/chat` | Pattern-backed language compiler, state transition tables | Monorepo `packages/ts-language` | Import TSLC compiler logic and dialogue packs | Derived from `BoggersTheFish/ts-chat-language` (`a67c788`) | Archive after monorepo verification |
| `TensionForge` | Active Substrate | OpenCL GPU training runtime for legacy hardware | `engines/tension-forge` | Mesa Rusticl OpenCL matmul/linear kernels, RX480 receipts | Monorepo `engines/tension-forge` | Port OpenCL kernels and verification scripts | Derived from `BoggersTheFish/TensionForge` (`d1ef0c5`) | Archive after monorepo verification |
| `Ten-SON-LM` | Active Research | Recurrent workspace language model (Milestone 1) | `engines/tension-lm`, `research/substrate-experiments` | Fixed-size semantic workspace recurrent model | Monorepo `engines/tension-lm` | Import model architecture and training scripts | Derived from `BoggersTheFish/Ten-SON-LM` (`b4976f6`) | Archive after monorepo verification |
| `tsq` | Active Runtime | Tension-Structured Quantization runtime | `packages/ts-runtime` | Verifier-gated tension-driven precision allocation | Monorepo `packages/ts-runtime` | Port TSQ quantization algorithms and adapters | Derived from `BoggersTheFish/tsq` (`68f510f`) | Archive after monorepo verification |
| `TS-LAB` | Active Spec | Research record spec & schema validation | `apps/lab`, `docs/specifications` | Constitutional boundary, JSON schemas, validation state machine | Monorepo `apps/lab` | Port schemas and validation machine | Derived from `BoggersTheFish/TS-LAB` (`7744f43`) | Archive after monorepo verification |
| `TS-OS` | Active Substrate | Bedrock BOGVM runtime path & process driver | `packages/ts-kernel`, `engines/bogvm` | Bedrock process driver, `.bogpkg` loader | Monorepo `engines/bogvm` | Port execution driver and bootloader logic | Derived from `BoggersTheFish/TS-OS` (`aa0b9d3`) | Archive after monorepo verification |
| `ts-spear` | Active Application | Paper Minecraft anti-cheat intelligence engine | `packages/ts-verifiers` / Standalone | State-driven confidence graphs, Paper plugin integration | Verifiers in `packages/ts-verifiers` | Import core verifiers; retain app standalone | Derived from `BoggersTheFish/ts-spear` (`fc2d482`) | Keep standalone; add TS monorepo dependency |
| `ts-exodus` | Active Research | Representation-dependent computation research | `research/exodus` | Phase 3 ORBIT and activation gate scripts | Monorepo `research/exodus` | Import research manifests and orbit scripts | Derived from `BoggersTheFish/ts-exodus` (`8c8770d`) | Archive satellite after monorepo integration |
| `ts-lm-genesis` | Active Research | Verifier-grounded semantic-orbit training | `research/genesis` | Hardware-aware semantic-orbit evaluation harness | Monorepo `research/genesis` | Import genesis experiment scripts and receipts | Derived from `BoggersTheFish/ts-lm-genesis` (`23109af`) | Archive satellite after monorepo integration |
| `TensionLM` | Historical | Early sigmoid-tension language model experiments | `docs/lineage/`, `docs/migration/archive-notices/` | LaTeX paper source, early Path A 117M/350M scripts | Monorepo `engines/tension-lm` | Preserve paper sources & archive notices | Derived from `BoggersTheFish/TensionLM` (`502937e`) | Maintain as archived historical reference |
| `TS-Reasoner-v0` | Historical | Early TS-Reasoner v30.0.0 local agent OS | `docs/lineage/`, `docs/migration/archive-notices/` | Metacompute trace schema, AGL implementation | Monorepo `packages/ts-reasoner` | Preserve trace schemas & archive notices | Derived from `BoggersTheFish/TS-Reasoner-v0` (`31b7d31`) | Maintain as archived historical reference |
| `bogbin` | Independent Substrate | Verified storage & portable compute substrate | External Substrate / `engines/bogvm` integration | BOGK capability engine, journal proof verifier, `.bog` format | N/A (Independent Project) | Integration via BOGVM driver (`engines/bogvm`) | Derived from `BoggersTheFish/bogbin` (`0189c47`) | Keep active and independently maintained |

---

## Consolidated Count & Verification Summary

* **Total Satellite Repositories Inspected:** 15
* **Canonical Monorepo Candidates Consolidated:** 12 (`TS-Core`, `cig-ts-engine`, `TS-Benchmarks`, `ts-chat-language`, `TensionForge`, `Ten-SON-LM`, `tsq`, `TS-LAB`, `TS-OS`, `ts-spear`, `ts-exodus`, `ts-lm-genesis`)
* **Historical Repositories Preserved:** 2 (`TensionLM`, `TS-Reasoner-v0`)
* **Independent Substrates Maintained:** 1 (`bogbin`)
