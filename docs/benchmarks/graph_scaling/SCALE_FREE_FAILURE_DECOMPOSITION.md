# Scale-Free Failure Decomposition

This is the v0.2 task for TS-Benchmarks.

## Purpose

Do not fix scale-free graphs yet. First make the failure sharper.

Central question:

> Is scale-free failure caused by hub dominance, bad relaxation damping, poor contradiction scoring, or the active-frontier policy starving low-degree regions?

## Metrics

- `hub_residual_share`: share of residual edge tension touching high-degree hubs.
- `nonhub_residual_share`: remaining residual tension share.
- `hub_to_nonhub_residual_ratio`: hub residual share divided by nonhub residual share.
- `mean_residual_by_degree_decile`: final node residual tension grouped by degree decile.
- `max_residual_edge_degree_product`: highest tension-weighted edge degree product.
- `frontier_churn_rate`: mean normalized change in active frontier size between steps.
- `plateau_residual_slope`: slope over the tail of the global tension curve.
- `contradiction_rank_of_planted_edge`: rank of planted contradiction edges among residual edges.

## Failure Labels

- `hub_dominance_problem`: high-degree nodes account for most residual tension.
- `damping_or_plateau_problem`: residual tension remains high while tail slope is flat.
- `localization_problem`: planted contradiction edges are not ranked near the top.
- `frontier_policy_problem`: the active frontier is effectively static.

## Command

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.scale_free_decomposition \
  --sizes 100,1000,10000 \
  --seed 42 \
  --out-dir artifacts/decomposition
```

## Claim Boundary

> v0.2 diagnoses failure modes. It does not claim TS-Core scales cleanly and does not introduce a fix.
