# Thinking System Claim Ledger

This ledger records all public research and engineering claims, their verified status, empirical evidence, reproduction commands, and explicit operational limitations.

---

## Status Classification Definitions

* `VERIFIED`: Supported by a reproducible passing test or sealed evaluation.
* `IMPLEMENTED`: Code exists and operates within a clearly stated boundary.
* `EXPERIMENTAL`: Implemented but not yet sufficiently validated or bounded.
* `HYPOTHESIS`: A proposed interpretation or theoretical mechanism.
* `ROADMAP`: Intended future development.
* `SUPERSEDED`: Replaced by a newer implementation or formulation.
* `ARCHIVED`: Retained only for historical lineage or reference.

---

## Claim Table

| Claim ID | Claim | Status | Evidence | Reproduction Command | Limitations | Related Package | Last Verified Commit |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `CLAIM-001` | Canonical TS Kernel transaction authorization is verifier-gated; unverified proposals fail closed to quarantine or abstain. | `VERIFIED` | 59 deterministic unit tests in `tests/test_canonical_kernel.py` | `pytest tests/test_canonical_kernel.py` | Authority covers bounded TSIR and BOGVM obligations; open-ended LLM text output is never proof. | `packages/ts-kernel` | `9050c8a` |
| `CLAIM-002` | Execution receipts are deterministic, content-addressable, and verifiable via SHA-256 replay. | `VERIFIED` | Replay tests in `tests/test_canonical_kernel.py` & `python -m core.kernel.demo --json` | `python -m core.kernel.demo --json` | Replay requires deterministic state snapshots. | `packages/ts-artifacts` | `9050c8a` |
| `CLAIM-003` | BOGVM arithmetic program execution produces verifiable semantic proof objects. | `VERIFIED` | 18 unit tests in `tests/test_bogvm_arithmetic_program_verifier.py` | `pytest tests/test_bogvm_arithmetic_program_verifier.py` | Covers integer arithmetic operations (ADD, SUB, MUL, DIV, MOD). | `engines/bogvm` | `9050c8a` |
| `CLAIM-004` | BOGVM observation verifiers enforce invariant boundary checks over state traces. | `VERIFIED` | 15 unit tests in `tests/test_bogvm_observation_verifier.py` | `pytest tests/test_bogvm_observation_verifier.py` | Requires explicit observation predicate definitions. | `packages/ts-verifiers` | `9050c8a` |
| `CLAIM-005` | Tension-triggered graph wave cycles dynamically localise residual tension across living graph nodes. | `VERIFIED` | Wave runner tests in `tests/test_wave_runner.py` & `tests/test_bogvm_wave_payload.py` | `pytest tests/test_wave_runner.py` | Wave propagation is bounded by max cycle count and tension thresholds. | `packages/ts-graph` | `9050c8a` |
| `CLAIM-006` | TSLC pattern-backed compiler translates natural language inputs into inspectable TSIR proposals. | `IMPLEMENTED` | TSLC compiler implementation in `packages/ts-language` (ported from `ts-chat-language`) | `pytest tests/test_protocols.py` | Natural language translation is bounded by pattern rules; output must pass verifier obligations. | `packages/ts-language` | `9050c8a` |
| `CLAIM-007` | OpenCL GPU matmul and linear training runtimes execute on legacy commodity hardware (RX480). | `EXPERIMENTAL` | Benchmark receipts in `engines/tension-forge` (`matmul_receipt.json`) | `python engines/tension-forge/rx480_smoke.py` | Requires Mesa Rusticl OpenCL environment on Linux. | `engines/tension-forge` | `9050c8a` |
| `CLAIM-008` | Recurrent fixed-size semantic workspace language model reduces parameter footprint for structured tasks. | `EXPERIMENTAL` | Milestone 1 scripts in `engines/tension-lm` | `python engines/tension-lm/baseline.py` | Active research prototype under evaluation. | `engines/tension-lm` | `9050c8a` |
| `CLAIM-009` | Representation challenges induce typed entity branching rather than arbitrary confidence inflation. | `VERIFIED` | Test case in `core/kernel/demo.py` & `tests/test_canonical_kernel.py` | `python -m core.kernel.demo` | Branching depends on user or verifier provenance score. | `packages/ts-kernel` | `9050c8a` |
| `CLAIM-010` | Full automated self-improving reasoning loop operates without human intervention across arbitrary domains. | `ROADMAP` | Conceptual specification in `docs/architecture/` | N/A | Roadmap aspiration; current implementation is verifier-bounded to supported task schemas. | `packages/ts-runtime` | N/A |
