# Thinking System Monorepo Migration Status Report

**Date:** 2026-07-21 (updated during interrupted-migration recovery)
**Branch:** `refactor/thinking-system-monorepo`
**Current remote:** `BoggersTheFish/BoggersTheAI`
**Planned remote:** `BoggersTheFish/thinking-system` (rename **not** performed)
**Package version:** `0.5.0-alpha.1` (alpha; **not** 1.0.0)

> **Honest status:** Alpha — canonical monorepo migration **in progress**.
> The verifier-gated kernel is implemented for a narrow supported domain under `core/kernel/`.
> A `src/thinking_system` namespace provides installable facades and a real CLI.
> Several historical and research components remain partially consolidated or planned.
> Empty `packages/`, top-level `engines/`, and `research/` directories are **placeholders**, not completed consolidations.

---

## 1. What actually landed

### Implemented

| Area | Location |
|------|----------|
| Verifier-gated kernel | `core/kernel/` |
| Living graph / waves | `core/graph/` |
| Runtime composition | `interface/runtime.py` |
| Canonical CLI | `src/thinking_system/apps/cli/main.py` (`ts` entry point) |
| Kernel/receipt facades | `src/thinking_system/kernel/`, `artifacts/`, etc. |
| BOGVM bridge + VM tree | `core/bogvm_bridge.py`, `core-vm/` |
| In-tree tension stacks | `inference/tension_forge/`, `inference/tension_lm/` |
| Dashboard | `dashboard/app.py` (not under `apps/dashboard/`) |
| Tests | `tests/` (unit suite gated by `not slow and not network`) |

### Compatibility facades (not physical package moves)

`src/thinking_system/{core,ir,artifacts,verifiers,graph,reasoner,language,runtime,engines/bogvm}` re-export legacy modules. Labelled **COMPATIBILITY_FACADE** in source.

### Absent / planned destinations

Empty or non-implementation directories: `packages/ts-*`, top-level `engines/*`, `research/*`, `benchmarks/suites`, `apps/lab`, `apps/chat`, `apps/dashboard`.

---

## 2. Satellite repositories

Prior reports claiming all 15 satellites were **ported and ready to archive** were **incorrect**.

See [import-ledger.md](import-ledger.md) for the evidence-backed classification. Summary:

- **INDEPENDENT:** bogbin, ts-spear (do not archive)
- **PLANNED / INSPECTED:** most other satellites
- **PARTIALLY_IMPORTED:** related in-tree code exists under legacy paths for some themes (graph, reasoner, tension, bogvm)
- **No satellite may be called CONSOLIDATED** without tracked import paths + verified SHA + tests

**Do not archive satellite repositories** as part of this PR.

---

## 3. Backward compatibility

1. Primary namespace: `thinking_system` (src layout).
2. Legacy top-level modules packaged: `core`, `interface`, …
3. Compatibility package: `BoggersTheAI` (aliases historical imports).
4. CLI: `ts` primary; `boggers` and `dashboard-start` retained.

---

## 4. Remaining migration work

1. Physical moves of `core/*` into `src/thinking_system/*` (optional; not required for alpha CLI/kernel).
2. Populate or delete empty `packages/` / `engines/` placeholders after real imports.
3. Import-ledger rows with verified external SHAs when satellites are actually pulled.
4. GitHub rename to `thinking-system` (manual, post-review).
5. Stronger architecture checker (full layer DAG) if package boundaries solidify.

---

## 5. Remaining risks

- Dual import models (`BoggersTheAI.*` vs bare `core.*`) still require packaging care.
- Documentation elsewhere may still overclaim; prefer this report + import-ledger + claim-ledger.
- Architecture checker enforces authority denylist only, not full dependency direction.
- Empty directories can mislead reviewers if docs are not read.

---

## 6. Verification commands (local)

```bash
python -m black --check .
python -m isort --check .
python -m ruff check .
python tools/check_architecture.py
python tools/check_docs.py
pytest -m "not slow and not network"
python -m thinking_system.apps.cli.main demo --json
```

Do not describe local results as GitHub-hosted CI results.
