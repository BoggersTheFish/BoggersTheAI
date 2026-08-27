# Adversarial Topology Generalization

This is the v0.5 experimental task for TS-Benchmarks.

## Framing

v0.4 passed on known graph families. v0.5 tries to falsify that result by testing mixed, near-boundary, and contradiction-placement-stressed graphs. The goal is not to prove universal scaling; the goal is to measure where topology-aware policy selection generalizes and where it fails.

## Graph Families

- `mixed_core_periphery`: scale-free hub core, small-world/random periphery, sparse bridge edges.
- `hub_threshold_sweep`: gradually varied hub concentration near selector boundary.
- `topology_noise_sweep`: known topology perturbed by edge rewiring/noise.

## Contradiction Placements

- `hub_hub`
- `hub_leaf`
- `leaf_leaf`
- `random`

## Oracle Comparison

- `selector_policy`: chosen from pre-run topology diagnostics only.
- `oracle_best_policy`: chosen after seeing policy outcomes.

The receipt reports both, but the selector must never use oracle information.

## Minimum Metrics

- `selector_policy`
- `selector_reason`
- `oracle_best_policy`
- `selector_matches_oracle`
- `selector_regret_final_tension`
- `selector_regret_f1`
- `catastrophic_regression`
- `boundary_case`
- `contradiction_placement`
- `topology_family`

## Command

```bash
python -m thinking_system.benchmarks.graph_scaling.runners.adversarial_topology_generalization \
  --sizes 100,1000 \
  --families mixed_core_periphery,hub_threshold_sweep,topology_noise_sweep \
  --placements hub_hub,hub_leaf,leaf_leaf,random \
  --hub-strengths 0.25,0.35,0.45,0.60,0.75 \
  --seed 42 \
  --out-dir artifacts/adversarial-topology
```

## Strict Success Criteria

- selector beats or matches always-reference on aggregate
- selector beats or matches always-degree-normalized on aggregate
- no catastrophic family-level regression
- receipts include oracle-best-policy comparison
- selector uses topology diagnostics only, not oracle labels or final outcome metrics
- boundary cases are documented honestly

## Claim Boundary

> v0.5 is an adversarial synthetic selector stress test. It does not prove TS-Core scales to real knowledge/provenance graphs.
