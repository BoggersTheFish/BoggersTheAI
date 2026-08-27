# ADR-003: Verifier Authority Boundary

* **Status:** ACCEPTED
* **Date:** 2026-07-21
* **Deciders:** Thinking System Maintainers

## Context

Language model output and heuristic confidence scores are non-deterministic and can produce correctness flips.

## Decision

Establish that generated language, model confidence, and script execution completion do NOT possess proof authority. All state transactions must be verifier-gated and backed by content-addressable receipts emitted by `TSKernel`. Unsupported verifier domains fail closed to `quarantine`, `branch`, or `abstain`.
