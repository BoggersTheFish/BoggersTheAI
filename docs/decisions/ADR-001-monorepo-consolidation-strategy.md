# ADR-001: Monorepo Consolidation Strategy

* **Status:** ACCEPTED
* **Date:** 2026-07-21
* **Deciders:** Thinking System Maintainers

## Context

The Thinking System project was scattered across 15+ satellite repositories (`TS-Core`, `cig-ts-engine`, `TS-Benchmarks`, `ts-chat-language`, `TensionForge`, `Ten-SON-LM`, `tsq`, `TS-LAB`, `TS-OS`, `ts-spear`, `ts-exodus`, `ts-lm-genesis`, `TensionLM`, `TS-Reasoner-v0`, `bogbin`). This fragmentation created duplicate implementations, ambiguous authority boundaries, and unclear claim status.

## Decision

Consolidate all active TS research and engineering components into one canonical monorepo: `BoggersTheFish/thinking-system` (transformed directly from `BoggersTheFish/BoggersTheAI`).

## Consequences

* Provides a single, verifier-first source of truth.
* Establishes clean package layers (`packages/`, `engines/`, `apps/`, `research/`, `benchmarks/`).
* Eliminates competing implementations.
