# Thinking System

> **A verifier-first research architecture for constructing, measuring, localising, and minimally revising structured reasoning systems under explicit residual accounting.**

[![CI](https://github.com/BoggersTheFish/BoggersTheAI/actions/workflows/ci.yml/badge.svg)](https://github.com/BoggersTheFish/BoggersTheAI/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

---

## 1. Current Status

> **Alpha — canonical monorepo migration in progress.** The verifier-gated kernel is implemented for a narrow supported domain. Several historical and research components remain partially consolidated or planned.

| Field | Value |
|-------|--------|
| **Version** | `0.5.0-alpha.1` |
| **Current remote** | [`BoggersTheFish/BoggersTheAI`](https://github.com/BoggersTheFish/BoggersTheAI) |
| **Planned remote** | `BoggersTheFish/thinking-system` (rename not done) |
| **Branch** | `refactor/thinking-system-monorepo` |
| **Primary CLI** | `ts` |
| **Python package** | `thinking_system` (+ `BoggersTheAI` compatibility package) |

---

## 2. What Thinking System Is

Governing pattern:

$$\text{representation} \rightarrow \text{lawful quotient} \rightarrow \text{relative residual} \rightarrow \text{sufficient observer family} \rightarrow \text{localised obstruction} \rightarrow \text{minimal typed revision} \rightarrow \text{sealed adversarial evaluation}$$

* **Verifier-gated state authorization** for the supported kernel domain.
* **Residual / tension accounting** across activation, contradiction, provenance, and verification dimensions where implemented.
* **Content-addressable receipts:** canonical receipt fields are hashed (SHA-256). Replay support is **limited graph-delta re-application** when base state matches — not full system time-travel.

---

## 3. What Thinking System Is NOT

> **Authority boundary**
> * Generated language is **not** proof authority.
> * Model confidence is **not** proof authority.
> * Execution completion alone is **not** proof authority.
> * Canonical accepted state is verifier-gated where the kernel path is used.
> * Implemented scope is **narrower** than the research roadmap.

---

## 4. Architecture (as implemented today)

```text
Legacy implementation (source of truth for most logic)
  core/kernel, core/graph, core/*, interface/*, reasoner/*, core-vm/, inference/*

Canonical installable namespace (src layout)
  src/thinking_system/
    kernel/     → re-exports core.kernel          (COMPATIBILITY_FACADE)
    apps/cli/   → real CLI (`ts`)                 (IMPLEMENTED)
    artifacts/, ir/, verifiers/, graph/, …        (COMPATIBILITY_FACADE)
    engines/tension_*                             (PLANNED stubs)

Empty placeholders (not consolidations)
  packages/ts-*, engines/* (top-level), research/*, apps/{lab,chat,dashboard}
```

Intended long-term package layers are described in [docs/architecture/](docs/architecture/) and ADRs; treat those as **target** design unless import-ledger says otherwise.

---

## 5. Implemented capabilities (scoped)

* **TSKernel** transaction authority under `core/kernel/` (also `from thinking_system.kernel import TSKernel`).
* **BOGVM** arithmetic / observation verifiers and bridge tests under `tests/test_bogvm_*.py`.
* **Wave runner** dynamics under `core/graph/`.
* **Receipt hash validation** and limited replay helpers.
* **Offline demo:** `ts demo --json` (no GPU/Ollama required for the kernel demo path).

Exact test counts change; derive them from `pytest` output for a given commit — do not trust fixed historical numbers in older docs.

---

## 6. Quick start

```bash
# Current repository (until rename)
git clone https://github.com/BoggersTheFish/BoggersTheAI.git
cd BoggersTheAI
git checkout refactor/thinking-system-monorepo   # migration branch

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# or: make install

make unit-test
make demo
```

---

## 7. Canonical demonstration

```bash
ts demo --json
# equivalent:
python -m thinking_system.apps.cli.main demo --json
```

---

## 8. Supported imports

```python
import thinking_system
from thinking_system.kernel import TSKernel
from thinking_system.apps.cli.main import main

# Legacy / compatibility
from core.kernel import TSKernel as CoreKernel
from BoggersTheAI.core.kernel import TSKernel as LegacyKernel
```

---

## 9. Claim boundary & lineage

* [Claim ledger](docs/claims-and-evidence/claim-ledger.md)
* [Import ledger](docs/migration/import-ledger.md)
* [Repository inventory](docs/lineage/repository-inventory.md)
* [Migration status report](docs/migration/final-report.md)

---

## 10. Documentation

* [What is Thinking System?](docs/introduction/what-is-thinking-system.md)
* [Architecture overview](docs/architecture/overview.md)
* [Authority boundary](docs/architecture/authority-boundary.md)
* [Dependency rules](docs/architecture/dependency-rules.md)

---

## 11. Citation

See [CITATION.cff](CITATION.cff). Until rename, cite the **current** repository URL:

```bibtex
@software{Michalek_Thinking_System_2026,
  author = {Michalek, Ben},
  title  = {Thinking System},
  year   = {2026},
  version = {0.5.0-alpha.1},
  url    = {https://github.com/BoggersTheFish/BoggersTheAI}
}
```

---

## 12. License

[MIT License](LICENSE).
