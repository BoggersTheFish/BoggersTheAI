# Thinking System Repository Inventory & Provenance Record

Inventory of satellite, external, and historical repositories related to the Thinking System stack.

**Current remote:** `BoggersTheFish/BoggersTheAI`
**Planned remote:** `BoggersTheFish/thinking-system` (rename not performed)
**Migration branch:** `refactor/thinking-system-monorepo`

For file-level status and verified provenance rules, see [docs/migration/import-ledger.md](../migration/import-ledger.md).
**Do not treat short SHAs in older drafts as verified** unless re-checked against a real clone or GitHub API.

---

## Repository inventory

| Repository | Status | Purpose | In-tree related paths | Archive? |
| :--- | :--- | :--- | :--- | :--- |
| `BoggersTheFish/BoggersTheAI` | **CANONICAL (active)** | Primary monorepo under migration | `core/`, `src/thinking_system/`, `interface/`, … | Keep active; rename later |
| `TS-Core` | **INSPECTED / PLANNED** | Historical core / memory work | Kernel lives in monorepo `core/kernel/` (not a satellite file import) | Do **not** archive yet |
| `cig-ts-engine` | **INSPECTED / PLANNED** | Continuous information graph | Related: `core/graph/` | Do **not** archive yet |
| `TS-Benchmarks` | **PLANNED** | Audit-first benchmarks | `benchmarks/` mostly empty | Keep independent |
| `ts-chat-language` | **INSPECTED / PLANNED** | TSLC / DDS | Related: `core/language/tslc.py`; not full port | Do **not** archive yet |
| `TensionForge` | **PLANNED** | OpenCL training | Empty `engines/tension-forge/`; in-tree `inference/tension_forge/` | Keep independent |
| `TensionLM` | **PLANNED / HISTORICAL** | Workspace LM | Empty `engines/tension-lm/`; in-tree `inference/tension_lm/` | Keep as reference |
| `tsq` | **PLANNED** | Quantization runtime | Empty `packages/ts-runtime/` | Keep independent |
| `TS-LAB` | **PLANNED** | Lab UI / records | Empty `apps/lab/` | Keep independent |
| `TS-OS` | **INSPECTED / PARTIALLY** | BOGVM path | Related: `core-vm/`, `core/bogvm_bridge.py` | Do **not** archive yet |
| `ts-spear` | **INDEPENDENT** | Minecraft anti-cheat | Not consolidated | Keep standalone |
| `ts-exodus` | **PLANNED** | Research programme | Empty `research/exodus/` | Keep independent |
| `ts-lm-genesis` | **PLANNED** | Research programme | Empty `research/genesis/` | Keep independent |
| `TS-Reasoner-v0` | **HISTORICAL** | Early reasoner | Related large tree: `reasoner/` (provenance incomplete) | Historical reference |
| `bogbin` | **INDEPENDENT** | Storage substrate | External | Keep active |

---

## Summary

* **Active monorepo:** `BoggersTheAI` (this repo), alpha migration.
* **Real implementation hotspots:** `core/kernel`, `core/graph`, `interface/`, `core-vm/`, `reasoner/`, `inference/`, `src/thinking_system/apps/cli`.
* **Empty destinations are not consolidations:** `packages/ts-*`, top-level `engines/*`, most of `research/*`, empty `apps/{lab,chat,dashboard}`.
* **Independent:** `bogbin`, `ts-spear`.
* **Do not archive satellites** until import-ledger shows CONSOLIDATED with verified SHAs and tests.
