# Topology-Aware Relaxation Policy Selection

This is the v0.4 experimental task for TS-Benchmarks.

## Hypothesis

Different graph topologies require different relaxation policies. Scale-free graphs benefit from degree normalization, while random and small-world graphs may prefer the reference policy.

## Selector Inputs

The selector uses pre-run graph diagnostics only:

- `max_degree / mean_degree`
- `degree_gini`
- `degree_variance`
- `hub_edge_touch_share`
- `hub_node_share`
- approximate clustering coefficient

It must not inspect final tension, localization scores, planted contradiction labels, or any post-run outcome metric.

## Command

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.topology_policy_selection \
  --sizes 100,1000,10000 \
  --graphs scale_free,random,small_world \
  --seed 42 \
  --out-dir artifacts/topology-policy
```

## Strict Success Criteria

- Preserve or improve scale-free performance versus reference.
- Avoid random/small-world regressions seen in v0.3.
- Report selected policy and selection reason in receipts.
- Use the same 100 / 1k / 10k sweep.
- Keep v0.3 marked experimental; do not merge raw degree normalization as the default policy.

## Claim Boundary

> v0.4 tests topology-aware policy selection on seeded synthetic graph families. It does not prove TS-Core scales cleanly to real knowledge graphs.
