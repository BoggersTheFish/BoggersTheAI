# ADR-002: Package Boundary Rules

* **Status:** ACCEPTED
* **Date:** 2026-07-21
* **Deciders:** Thinking System Maintainers

## Context

Clear domain boundaries are necessary to prevent circular dependencies and protect core verifier authority.

## Decision

Enforce strict package boundaries and unidirectional dependency flow:
`ts-core` -> `ts-ir` / `ts-artifacts` -> `ts-verifiers` -> `ts-kernel` -> `ts-graph` / `ts-reasoner` -> `ts-language` / `ts-runtime` -> `apps/`

Foundational packages must not import applications. Dependency directions are checked automatically via `make check-architecture`.
