# Issue #1: Scale-free graphs retain high final tension under reference relaxation config

## Status

Open.

## Why This Matters

Scale-free graphs are hub-heavy. Real knowledge graphs, citation graphs, social graphs, dependency graphs, and provenance graphs often have hub-like structure. If the reference TS relaxation config handles random and small-world graphs but fails on scale-free graphs, the failure is not cosmetic. It is a direct scaling risk.

## Observed Failure

First 100/1k/10k local sweep:

- `scale-scale_free-100-seed42`: high final tension, F1 `0.000`.
- `scale-scale_free-1000-seed42`: high final tension, F1 `0.000`.
- `scale-scale_free-10000-seed42`: high final tension, F1 `0.000`.

The public report must keep this visible.

## Required Diagnostics

Each failed scale-free run should report:

- tension by degree bucket
- top-k residual edges
- whether high-degree hubs dominate residual tension
- relaxation steps until plateau
- active frontier size over time
- contradiction-localization confusion matrix

## Next Experiment

Compare the current reference config against hub-aware variants:

- degree-normalized edge updates
- capped hub contribution
- context-split hubs
- provenance-weighted hub dampening

Success means lower final tension and nonzero contradiction-localization F1 on the same seeded scale-free graphs without regressing random and small-world runs.
