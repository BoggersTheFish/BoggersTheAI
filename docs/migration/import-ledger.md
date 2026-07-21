# Thinking System Component Provenance Ledger

Evidence-backed ledger of satellite and in-tree components for the monorepo migration
on branch `refactor/thinking-system-monorepo`.

**Canonical remote:** `BoggersTheFish/thinking-system`
**Former remote:** `BoggersTheFish/BoggersTheAI` (renamed after merge `9786e098e0a5c31f8bc3199417e6d47a5cfac2cb`)
**Package version:** `0.5.0-alpha.1`

## Status vocabulary

| Status | Meaning |
|--------|---------|
| **CONSOLIDATED** | Unique maintained functionality is present as tracked monorepo source **and** covered by passing tests. |
| **PARTIALLY_IMPORTED** | Some related code exists in-tree; full satellite surface is not imported. |
| **COMPATIBILITY_FACADE** | Namespace re-export only; implementation still lives under legacy paths. |
| **INSPECTED** | Repository was reviewed; no complete import performed. |
| **PLANNED** | Destination reserved; no unique satellite code imported. |
| **HISTORICAL** | Superseded / reference only. |
| **INDEPENDENT** | Remains a separate maintained project. |
| **ABSENT** | Claimed destination path has no tracked implementation files. |

**Provenance rule:** source commit SHAs are recorded only when verified via git against a local clone or GitHub API. Unverified historical short SHAs from prior docs are **not** repeated as fact.

---

## In-tree implementation (this monorepo)

| Component | Source | Source path(s) | Destination / facade | Adaptation | Tests | Licence | Status |
|-----------|--------|----------------|----------------------|------------|-------|---------|--------|
| TSKernel | `BoggersTheFish/BoggersTheAI` | `core/kernel/` | `core/kernel/` + facade `src/thinking_system/kernel/` | Canonical implementation remains under `core/kernel`; facade re-exports | `tests/test_canonical_kernel.py` | MIT | **PARTIALLY_IMPORTED** (facade) / implementation **CONSOLIDATED** in `core/kernel` |
| TSIR | same | `core/kernel/ir.py` | `core/kernel/ir.py` + `src/thinking_system/ir/` | Facade re-export | `tests/test_canonical_kernel.py` | MIT | **COMPATIBILITY_FACADE** |
| Receipts | same | `core/kernel/receipts.py` | `core/kernel/receipts.py` + `src/thinking_system/artifacts/` | Content-addressable SHA-256 of canonical receipt fields; limited graph-delta replay | `tests/test_canonical_kernel.py` | MIT | **COMPATIBILITY_FACADE** |
| Deterministic parser | same | `core/kernel/representation.py` | facade `src/thinking_system/language/` | Re-export | kernel tests | MIT | **COMPATIBILITY_FACADE** |
| Universal Living Graph | same | `core/graph/` | `core/graph/` + facade `src/thinking_system/graph/` | Re-export | `tests/test_graph*.py`, `tests/test_wave*.py` | MIT | **COMPATIBILITY_FACADE** |
| TSEngine | same | `core/ts_engine.py` | facade `src/thinking_system/reasoner/` | Re-export | reasoner-related tests if present | MIT | **COMPATIBILITY_FACADE** |
| BoggersRuntime | same | `interface/runtime.py` | `interface/runtime.py` + facade `src/thinking_system/runtime/` | Explicit absolute imports for query/router symbols | `tests/test_runtime.py`, `tests/test_integration.py` | MIT | **COMPATIBILITY_FACADE** |
| BOGVM bridge | same | `core/bogvm_bridge.py`, `core-vm/` | facade `src/thinking_system/engines/bogvm/`; real VM under `core-vm/` | Bridge re-export; full VM not relocated | `tests/test_bogvm_*.py` | MIT | **PARTIALLY_IMPORTED** |
| CLI (`ts`) | same | `src/thinking_system/apps/cli/main.py` | same; legacy `apps/cli/` re-exports | Canonical entry for console scripts | `tests/test_clean_package_imports.py`, CI demo step | MIT | **CONSOLIDATED** (CLI entry) |
| Dashboard | same | `dashboard/app.py` | still `dashboard/`; empty `apps/dashboard/` | Not moved | `tests/test_dashboard*.py` | MIT | **PARTIALLY_IMPORTED** |
| Chat | same | `interface/chat.py` | still `interface/chat.py`; empty `apps/chat/` | Not moved | chat used via CLI legacy path | MIT | **PARTIALLY_IMPORTED** |
| TensionForge (in-tree) | same | `inference/tension_forge/` | **not** `engines/tension-forge/` (empty) | Historical in-tree OpenCL stack | limited | MIT | **PARTIALLY_IMPORTED** (path differs from docs that claimed `engines/`) |
| TensionLM (in-tree) | same | `inference/tension_lm/` | **not** `engines/tension-lm/` (empty) | Historical in-tree scripts | limited | MIT | **PARTIALLY_IMPORTED** |
| Reasoner tree | same | `reasoner/` | still `reasoner/` | Large local tree; not fully namespaced under `thinking_system` | various | MIT | **PARTIALLY_IMPORTED** |

Empty placeholder directories (no tracked source): `packages/ts-*`, top-level `engines/*`, `research/*`, `benchmarks/suites`, `apps/lab`, `apps/chat`, `apps/dashboard` → classify **ABSENT** / **PLANNED**.

---

## Satellite repositories (15)

| Repository | Verified source SHA in this clone? | Destination claimed historically | Status | Notes |
|------------|-------------------------------------|----------------------------------|--------|-------|
| TS-Core | `3ef48ad00efef8659ad0981d71de509a9827f584` | `src/thinking_system/core/typed_tension/` | **PARTIALLY_IMPORTED** | Domain-neutral typed tension kernel imported with its focused test and example; legacy Python application layers, Rust acceleration, CLI, Z3, Grok, UI, and Kernel Wave 12 surfaces remain unimported |
| cig-ts-engine | `71d91a6a0cdc9e7a5439df972130596f0bae5d2f` | `src/thinking_system/graph/cig/` | **PARTIALLY_IMPORTED** | Core graph models, deterministic propagation, edge tension, derivative observer, representational radius, context-split proposal, YAML IO, seed graph and focused tests imported; CLI, plotting, reports, Obsidian export and generated artifacts remain outside |
| TS-Benchmarks | `7c0611f7ef4dc2d150b12dc4197a8d48a462207f` | `src/thinking_system/benchmarks/graph_scaling/` | **CONSOLIDATED** | Complete implemented Workstream A imported with graph generators, relaxation policies, baselines, receipts, schemas, runners, reports, failure decomposition, topology selection, focused tests, technical documentation and retained evidence; only repository scaffolding and a public-post draft were excluded |
| ts-chat-language | Not verified here | `packages/ts-language` | **INSPECTED** / **PLANNED** | TSLC-like code in `core/language/tslc.py` is in-tree monorepo code; full satellite port not evidenced |
| TensionForge | Not verified here | `engines/tension-forge` | **PLANNED** (satellite); in-tree `inference/tension_forge/` is separate | Empty `engines/tension-forge/` |
| Ten-SON-LM | Not verified here | `engines/tension-lm` | **PLANNED** | Empty destination |
| tsq | Not verified here | `packages/ts-runtime` | **PLANNED** | Empty destination |
| TS-LAB | Not verified here | `apps/lab` | **PLANNED** | `apps/lab` empty |
| TS-OS | Not verified here | bogvm paths | **INSPECTED** / **PARTIALLY_IMPORTED** | Related substrate in `core-vm/` |
| ts-spear | Not verified here | verifiers | **INDEPENDENT** | Keep standalone; do not archive |
| ts-exodus | Not verified here | `research/exodus` | **PLANNED** | `research/exodus` empty |
| ts-lm-genesis | Not verified here | `research/genesis` | **PLANNED** | empty |
| TensionLM | Not verified here | `engines/tension-lm` | **PLANNED** / **HISTORICAL** | empty engines path; see `inference/tension_lm/` |
| TS-Reasoner-v0 | Not verified here | `reasoner/` | **HISTORICAL** / **PARTIALLY_IMPORTED** | Large `reasoner/` tree exists; full satellite provenance not ledgered with SHA |
| bogbin | Not verified here | external | **INDEPENDENT** | Keep active |

---

## Packaging notes

- Installable packages: `thinking_system` (from `src/`), plus legacy top-level modules `core`, `interface`, `adapters`, `apps`, `dashboard`, `entities`, `tools`, `shared`, `mind`, `multimodal`, `experiments`, and compatibility package `BoggersTheAI`.
- Top-level empty `packages/` and `engines/` directories are **not** declared in setuptools package discovery.

## How to re-verify a satellite SHA

```bash
# Example — only record when this succeeds against a real clone:
git -C /path/to/satellite rev-parse HEAD
gh api repos/BoggersTheFish/<repo>/commits/<sha> --jq .sha
```

Do not invent or splice SHAs.
