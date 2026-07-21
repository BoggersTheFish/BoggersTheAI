# cig-ts-engine consolidation record

## Source

- Repository: `BoggersTheFish/cig-ts-engine`
- Source branch: `master`
- Source commit: `71d91a6a0cdc9e7a5439df972130596f0bae5d2f`
- Licence: MIT

## Imported surface

The deterministic, domain-neutral CIG mechanics were imported into:

`src/thinking_system/graph/cig/`

Imported functionality:

- validated node and edge models
- mutable deterministic CIG graph state
- deterministic activation propagation and relaxation
- edge-local and total tension measurement
- finite-difference derivative-meaning observer
- representational-radius measurement
- overloaded-node localisation
- non-mutating context-split proposals
- tension-reduction versus complexity-cost acceptance rule
- context-split application
- YAML graph loading and saving
- the hand-authored demonstration seed graph
- focused tests for the imported surface

## Adaptation

Imports were changed from `cig` to
`thinking_system.graph.cig`.

The demonstration graph was renamed from:

`examples/ts_core.yaml`

to:

`examples/cig_ts_core.yaml`

The implementation remains an experimental graph family alongside the existing
Thinking System universal graph. It has not replaced that graph implementation.

## Deliberately not imported

- Typer CLI
- matplotlib visualisation
- proof-report generation
- Obsidian export
- generated PNG files
- generated proof-bank documents
- generated Obsidian vault contents
- symbolic or biographical demonstration scripts

Those surfaces are application, presentation, or generated-output layers rather
than required graph mechanics.

## Current status

**PARTIALLY_IMPORTED**

The core experimental graph mechanics are present and tested. The satellite
must remain unarchived until its excluded surfaces are explicitly classified as
obsolete, historical, independently maintained, or worth importing.
