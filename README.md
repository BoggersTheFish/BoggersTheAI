# Thinking System

> **A verifier-first research architecture for constructing, measuring, localising, and minimally revising structured reasoning systems under explicit residual accounting.**

[![CI](https://github.com/BoggersTheFish/thinking-system/actions/workflows/ci.yml/badge.svg)](https://github.com/BoggersTheFish/thinking-system/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

---

## 1. Current Status

* **Monorepo Stage:** Production Monorepo (`v1.0.0`)
* **Canonical Remote:** `BoggersTheFish/thinking-system`
* **Primary CLI:** `ts`
* **Python Package:** `thinking_system`

---

## 2. What Thinking System Is

Thinking System is a verifier-first architecture operating under the governing pattern:

$$\text{representation} \rightarrow \text{lawful quotient} \rightarrow \text{relative residual} \rightarrow \text{sufficient observer family} \rightarrow \text{localised obstruction} \rightarrow \text{minimal typed revision} \rightarrow \text{sealed adversarial evaluation}$$

* **Verifier-Gated State Authorization:** No proposal enters canonical graph memory without passing explicit verifier obligations.
* **Residual & Tension Accounting:** Measures tension vector components across activation, contradiction, provenance, and verification dimensions.
* **Content-Addressable Receipts:** Every transaction yields an immutable SHA-256 receipt for exact deterministic replay.

---

## 3. What Thinking System Is NOT

> [!IMPORTANT]
> **Authority Boundary Statement:**
> * **Generated language is NOT proof authority.**
> * **Model confidence is NOT proof authority.**
> * **Execution completion is NOT proof authority by itself.**
> * **Canonical accepted state is strictly verifier-gated.**
> * **The current implemented scope is narrower than the research roadmap.**

---

## 4. Architecture Diagram

```text
ts-core (Foundational Types & Memory Specs)
  ↓
ts-ir + ts-artifacts (TSIR Proposals & Receipt Replay)
  ↓
ts-verifiers (Arithmetic & Observation Checkers)
  ↓
ts-kernel (Transaction Authority & Tension Accounting)
  ↓
ts-graph + ts-reasoner (Living Graph & Wave Dynamics)
  ↓
ts-language + ts-runtime (TSLC Dialogue & Runtime Composition)
  ↓
CLI (`ts`) / Lab (`apps/lab`) / Dashboard / Chat
```

---

## 5. Verified & Implemented Capabilities

* **`ts-kernel` Transaction Authority:** 59/59 verified tests covering commit, reject, quarantine, branch, and abstain decisions.
* **BOGVM Verifiers:** Arithmetic program verifier (18 tests) and observation predicate verifiers (15 tests).
* **Wave Runner Dynamics:** Tension-triggered graph wave cycles and local tension dissipation (5 tests).
* **Deterministic Replay:** SHA-256 receipt audit and graph snapshot restoration.

---

## 6. Five-Minute Quick Start

```bash
# 1. Clone the canonical monorepo
git clone https://github.com/BoggersTheFish/thinking-system.git
cd thinking-system

# 2. Install package and dev dependencies
pip install -e ".[dev]"
# Or using make:
make install

# 3. Run unit tests
make unit-test
```

---

## 7. Canonical Runnable Demonstration

Run the deterministic verifier-first transaction demo (**100% offline, no GPU/Ollama required**):

```bash
# Primary CLI command:
ts demo

# Or with raw JSON receipt output:
ts demo --json
```

---

## 8. Repository Map

```text
thinking-system/
├── packages/       # Core domain packages (ts-core, ts-kernel, ts-verifiers, ts-graph, ts-language)
├── engines/        # Compute substrates (bogvm, tension-lm, tension-forge)
├── apps/           # Interfaces (cli, lab, dashboard, chat)
├── research/       # Active research programmes (exodus, genesis, observer-birth)
├── benchmarks/     # Falsification harnesses and seed task fixtures
├── experiments/    # Bounded active, completed, and archived experiments
└── docs/           # Comprehensive specifications, architecture, claims, and lineage
```

---

## 9. Claim-Boundary Statement

Every major public claim is formally tracked in the [Claim Ledger](docs/claims-and-evidence/claim-ledger.md). Public claims are classified under strict status labels: `VERIFIED`, `IMPLEMENTED`, `EXPERIMENTAL`, `HYPOTHESIS`, `ROADMAP`, `SUPERSEDED`, or `ARCHIVED`.

---

## 10. Documentation Links

* [What is Thinking System?](docs/introduction/what-is-thinking-system.md)
* [What Thinking System is NOT](docs/introduction/what-thinking-system-is-not.md)
* [Architecture Overview](docs/architecture/overview.md)
* [Authority Boundary Specification](docs/architecture/authority-boundary.md)
* [Dependency Direction Rules](docs/architecture/dependency-rules.md)
* [Claim Ledger](docs/claims-and-evidence/claim-ledger.md)
* [Repository Inventory & Lineage](docs/lineage/repository-inventory.md)
* [Migration Baseline](docs/migration/baseline.md)

---

## 11. Contributing & Citation

* **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines and coding standards.
* **Citation:** See [CITATION.cff](CITATION.cff) or cite as:
  ```bibtex
  @software{Michalek_Thinking_System_2026,
    author = {Michalek, Ben},
    title = {Thinking System: A Verifier-First Research Architecture for Structured Reasoning Under Residual Accounting},
    year = {2026},
    url = {https://github.com/BoggersTheFish/thinking-system}
  }
  ```

---

## 12. License

This project is licensed under the [MIT License](LICENSE).
