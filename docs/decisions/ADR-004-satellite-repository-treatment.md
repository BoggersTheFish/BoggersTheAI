# ADR-004: Satellite Repository Treatment

* **Status:** ACCEPTED
* **Date:** 2026-07-21
* **Deciders:** Thinking System Maintainers

## Context

Satellite repositories vary between core candidate modules, historical reference implementations, and independent substrates.

## Decision

* Candidate modules (`TS-Core`, `cig-ts-engine`, `TS-Benchmarks`, `ts-chat-language`, `TensionForge`, `Ten-SON-LM`, `tsq`, `TS-LAB`, `TS-OS`, `ts-exodus`, `ts-lm-genesis`) are absorbed into monorepo paths (`packages/`, `engines/`, `apps/`, `research/`, `benchmarks/`).
* Historical prototypes (`TensionLM`, `TS-Reasoner-v0`) remain available for reference with archive notices pointing to `thinking-system`.
* `bogbin` remains an independently maintained verified storage substrate integrated via `engines/bogvm`.
