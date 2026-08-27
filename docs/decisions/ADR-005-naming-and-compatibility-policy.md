# ADR-005: Naming and Backward Compatibility Policy

* **Status:** ACCEPTED
* **Date:** 2026-07-21
* **Deciders:** Thinking System Maintainers

## Context

Renaming `BoggersTheAI` to `thinking-system` requires standardizing package names while preserving backward compatibility for existing imports and CLI commands.

## Decision

* Project Name: `Thinking System`
* Repository Slug: `thinking-system`
* Primary Python Package: `thinking_system`
* Primary CLI Command: `ts`
* Legacy Compatibility: `BoggersTheAI` imports and `boggers`/`dashboard-start` CLI commands are preserved via backward-compatibility wrappers.
