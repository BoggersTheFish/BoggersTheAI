# Hub-Normalized Relaxation Ablation

This is the v0.3 experimental task for TS-Benchmarks.

## Hypothesis

Scale-free failure is caused by hub nodes absorbing or emitting disproportionate residual tension.

## Variants

- `reference`: v0.1/v0.2 reference behavior.
- `degree_normalized`: scales node updates by `1 / sqrt(degree + 1)`.
- `hub_damping`: applies a lower update multiplier to nodes at or above the configured hub percentile.
- `residual_redistribution`: reserves active-frontier edge budget for non-hub edges so hub edges cannot monopolize relaxation work.

## Command

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.hub_normalization_ablation \
  --sizes 100,1000,10000 \
  --graphs scale_free,random,small_world \
  --seed 42 \
  --out-dir artifacts/hub-normalization
```

## Strict Success Criteria

- Reduce `hub_residual_share` from the v0.2 level without hiding total final tension.
- Improve contradiction-localization F1 on scale-free graphs.
- Avoid regression on random and small-world graph families.
- Preserve sparse active-frontier runtime behavior.
- Emit clean-commit receipts for every comparison.

## Claim Boundary

> v0.3 is an experimental ablation. A positive result can support hub-aware relaxation on these seeded synthetic graphs only.
