# TS-Benchmarks consolidation record

## Source

- Repository: `BoggersTheFish/TS-Benchmarks`
- Source branch: `main`
- Source commit: `7c0611f7ef4dc2d150b12dc4197a8d48a462207f`
- Licence: MIT
- Source package version: `0.1.0`

## Canonical destination

`src/thinking_system/benchmarks/graph_scaling/`

## Consolidated implementation

The complete implemented Workstream A benchmark surface was imported:

- deterministic synthetic graph generators
- random, scale-free, small-world, knowledge-like, provenance, temporal,
  and multi-context graph families
- contradiction injection
- sparse active-frontier relaxation
- reference, degree-normalized, hub-damping, and residual-redistribution
  update policies
- degree, PageRank-like, and random-residual baselines
- contradiction localisation metrics
- scale-free failure decomposition
- hub-normalization ablation
- topology diagnostics and policy selection
- benchmark receipts with source, machine, dependency, dataset, metric,
  caveat, dirty-tree, and artifact information
- Markdown and CSV report generation
- optional plotting support
- receipt JSON schema
- all focused source tests
- technical design, roadmap, issue, and experiment documentation
- retained scaling report evidence

## Namespace adaptation

Imports changed from:

`ts_benchmarks`

to:

`thinking_system.benchmarks.graph_scaling`

Module commands now use:

`python -m thinking_system.benchmarks.graph_scaling...`

Runner repository-root resolution was adjusted for the deeper canonical package
location so benchmark receipts point at the Thinking System repository.

## Deliberately not imported

- repository-specific GitHub Actions configuration
- the public progress-post draft
- standalone packaging metadata and dependency files

These are repository scaffolding or communication material, not benchmark
runtime, verification, evidence, or technical documentation.

## Empty future workstreams

The source repository contained placeholder packages for future datasets,
hardware benchmarks, hybrid demonstrations, metrics, and scripts. Their package
markers were preserved, but no unimplemented capability is claimed.

## Current status

**CONSOLIDATED**

All implemented source, tests, schemas, technical documentation, and retained
evidence from source commit `7c0611f7ef4dc2d150b12dc4197a8d48a462207f` are present in the canonical
monorepo.

Archiving the satellite remains a separate maintainer action after this import
is merged and verified by CI.
