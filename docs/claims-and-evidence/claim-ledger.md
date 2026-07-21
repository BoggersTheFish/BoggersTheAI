# Thinking System Claim Ledger

**Canonical repository:** `BoggersTheFish/thinking-system` (formerly `BoggersTheFish/BoggersTheAI`).

Public claims, status, evidence pointers, and limitations. Package paths below are **actual** tree locations, not empty `packages/` placeholders.

---

## Status labels

* `VERIFIED`: Supported by reproducible tests on a stated command.
* `IMPLEMENTED`: Code exists within a stated boundary.
* `EXPERIMENTAL`: Code exists; validation incomplete.
* `HYPOTHESIS`: Theoretical proposal.
* `ROADMAP`: Future work.
* `SUPERSEDED` / `ARCHIVED`: Historical only.

Test **counts** must be re-derived with `pytest --collect-only` or a full run for the commit under review. Fixed historical counts in older docs are untrusted.

---

## Claim table

| Claim ID | Claim | Status | Evidence | Reproduction | Limitations | Related path |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CLAIM-001` | Kernel transaction authorization is verifier-gated for the supported domain; required obligations fail closed. | `VERIFIED` | `tests/test_canonical_kernel.py` | `pytest tests/test_canonical_kernel.py` | LLM text is never proof authority. | `core/kernel/` |
| `CLAIM-002` | Receipts are content-addressable via SHA-256 of canonical fields; hash validation and limited graph-delta replay exist. | `VERIFIED` (scoped) | kernel receipt tests + demo | `python -m core.kernel.demo --json` | Not full-system immutable storage or unrestricted time-travel replay. | `core/kernel/receipts.py` |
| `CLAIM-003` | BOGVM arithmetic program execution produces verifiable semantic proof objects for supported ops. | `VERIFIED` | `tests/test_bogvm_arithmetic_program_verifier.py` | `pytest tests/test_bogvm_arithmetic_program_verifier.py` | Integer arithmetic subset. | `core/kernel/`, `core-vm/` |
| `CLAIM-004` | BOGVM observation verifiers enforce invariant checks over state traces. | `VERIFIED` | `tests/test_bogvm_observation_verifier.py` | `pytest tests/test_bogvm_observation_verifier.py` | Requires explicit predicates. | `core/kernel/`, verifiers |
| `CLAIM-005` | Tension-triggered graph wave cycles localise residual tension within configured bounds. | `VERIFIED` | `tests/test_wave_runner.py`, `tests/test_bogvm_wave_payload.py` | `pytest tests/test_wave_runner.py` | Bounded cycles / thresholds. | `core/graph/` |
| `CLAIM-006` | Pattern/heuristic TSLC-style compilation exists in-tree. | `IMPLEMENTED` | `core/language/tslc.py`, kernel representation parser | inspect modules; not a full satellite port proof | Not evidenced as complete `ts-chat-language` import. | `core/language/`, `core/kernel/representation.py` |
| `CLAIM-007` | OpenCL tension-forge training stack exists in-tree. | `EXPERIMENTAL` | `inference/tension_forge/` | project-local scripts under that tree | **Not** under empty `engines/tension-forge/`. Hardware-dependent. | `inference/tension_forge/` |
| `CLAIM-008` | TensionLM-related scripts exist in-tree. | `EXPERIMENTAL` | `inference/tension_lm/` | project-local scripts | **Not** under empty `engines/tension-lm/`. | `inference/tension_lm/` |
| `CLAIM-009` | Representation challenges can induce typed entity branching in kernel demo paths. | `VERIFIED` | demo + kernel tests | `python -m core.kernel.demo` | Depends on provenance / verifier scores. | `core/kernel/` |
| `CLAIM-010` | Fully automated self-improving reasoning loop across arbitrary domains. | `ROADMAP` | architecture docs | N/A | Aspiration only. | runtime / research |

---

## Non-claims

* This repository is **not** a finished production monorepo at v1.0.0.
* Empty `packages/ts-*` directories are **not** evidence of consolidation.
* GitHub rename to `thinking-system` is **planned**, not complete.
