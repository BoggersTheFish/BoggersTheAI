# Thinking System Migration Baseline

**Date:** 2026-07-21
**Branch:** `refactor/thinking-system-monorepo`
**Target Repository:** `BoggersTheFish/thinking-system` (renamed from `BoggersTheFish/BoggersTheAI`)

---

## 1. Commit Baseline

* **Local HEAD Commit SHA:** `9050c8aee9053e77a56367126ca64713004c5a59`
* **Remote `origin/main` SHA:** `73fd3e8ee9053e77a56367126ca64713004c5a59`
* **Migration Branch:** `refactor/thinking-system-monorepo`

---

## 2. Environment & Dependency Manager

* **Python Version:** `Python 3.12.3` (Runtime compatibility: `>=3.10`, CI matrix: `3.10`, `3.11`, `3.12`)
* **Dependency Manager:** PEP 517 / PEP 621 compliant `pyproject.toml` with `setuptools` build backend (`pip install -e .`) and `uv` package manager support.
* **Core Dependencies:** `pyyaml`, `jsonschema`, `numpy`
* **Dev Dependencies:** `pytest`, `pytest-cov`, `black`, `isort`, `ruff`, `mypy`, `fastapi`, `uvicorn`, `ollama`

---

## 3. Existing Test Commands & Baseline Verification

* **Primary Test Suite:**
  ```bash
  pytest
  ```
* **Smoke / Kernel Verification Command:**
  ```bash
  python -m core.kernel.demo --json
  ```
* **Type Check Command:**
  ```bash
  mypy core/kernel --explicit-package-bases --ignore-missing-imports --follow-imports=skip --no-error-summary
  ```
* **Formatting / Lint Commands:**
  ```bash
  black --check .
  ruff check .
  isort --check .
  ```
* **Baseline Test Results:**
  * Canonical Kernel (`tests/test_canonical_kernel.py`): 59/59 PASSED
  * BOGVM Arithmetic Verifier (`tests/test_bogvm_arithmetic_program_verifier.py`): 18/18 PASSED
  * BOGVM Observation Verifier (`tests/test_bogvm_observation_verifier.py`): 15/15 PASSED
  * BOGVM Wave Payload (`tests/test_bogvm_wave_payload.py`): 10/10 PASSED
  * Wave Runner (`tests/test_wave_runner.py`): 5/5 PASSED
  * Kernel Smoke Demo (`python -m core.kernel.demo --json`): PASSED (Deterministic JSON receipt emitted)

---

## 4. Current CLI Entrypoints

1. `boggers` (`BoggersTheAI.interface.chat:run_chat`)
2. `dashboard-start` (`BoggersTheAI.dashboard.app:main`)
3. `python -m core.kernel.demo` (Deterministic kernel transaction demo)

---

## 5. Current Package Boundaries

* `BoggersTheAI` (Root package namespace)
* `BoggersTheAI.core` (Kernel, graph, reasoning, trace processor, query processor, TS engine)
* `BoggersTheAI.core.kernel` (Canonical TS Kernel authority: transactions, receipts, obligations, representations, IR, tension, arithmetic)
* `BoggersTheAI.core.graph` (Universal living graph, wave runner, BOGVM payload)
* `BoggersTheAI.dashboard` (FastAPI dashboard web app)
* `BoggersTheAI.interface` (Runtime, chat interface, API bindings)
* `BoggersTheAI.adapters` (arXiv, Semantic Scholar, Wikidata crawlers)
* `BoggersTheAI.experiments` (Frontier scripts, seed task benchmarks, self-data generator)

---

## 6. Current CI Workflows

1. `.github/workflows/ci.yml`
   * Trigger: Push / PR to `main` or `master`
   * Matrix: Python `3.10`, `3.11`
   * Steps: Checkout, setup python, pip cache, `pip install -e .`, `pip install pytest`, `pytest -q`, `python -m core.kernel.demo --json`
2. `.github/workflows/test.yml`
   * Trigger: Push / PR
   * Matrix: Python `3.10`, `3.11`, `3.12`
   * Steps: Checkout, ruff lint, black format check, isort check, mypy type check, pytest coverage check (`--cov-fail-under=60`)
