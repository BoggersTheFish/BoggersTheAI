# PRIME Canonical Agent Benchmark v1 — Retirement Record

Status: RETIRED BEFORE ADAPTIVE IMPLEMENTATION AND BEFORE FROZEN EVALUATION

The v1 experiment is retired because its frozen repair-transition rule is
incompatible with the information structure of its frozen environment.

No evaluation seeds in the frozen range 1000 through 1127 were run before this
retirement decision.

## Defect

The environment uses binary observations with target action

    Y_t = X_(t-d)

for hidden depth

    d in {0, 1, 2, 4}.

The frozen contract required FULL PRIME to:

1. begin at history depth 0;
2. propose only the next permitted history depth;
3. require predictive/decision evidence plus representation complexity cost
   before authorizing repair.

For d = 2, the intermediate depth-1 representation is

    H1_t = (X_(t-1), X_t)

while the target is

    Y_t = X_(t-2).

Under the frozen iid-style binary observation generator, H1_t contains no
systematic predictive information about Y_t beyond chance.

Therefore an honest predictive verifier should not be expected to authorize
the H0 -> H1 transition after complexity cost.

But without accepting H1, the frozen next-depth-only rule prevents PRIME from
ever proposing H2.

For d = 4, the same structural problem prevents justified traversal through
intermediate H1 and H2 representations before reaching H4.

## Consequence

Continuing v1 would force one of two scientifically unacceptable choices:

- make the verifier accept representation growth without supporting
  predictive/decision evidence; or
- leave FULL PRIME structurally unable to reach representations that the
  benchmark was intended to test.

Neither is acceptable.

## Preserved evidence

The following remain valid historical artifacts:

- the original frozen v1 experiment contract;
- the dependency-free environment;
- the common tabular learner;
- the fixed baseline apparatus;
- the development-only baseline selection;
- the selection of FIXED-H4 under the frozen development rule.

These are not deleted or rewritten.

## Resolution

A successor experiment will retain the frozen environment, learner, fixed
baselines, metrics, development/evaluation split, and evaluation seeds.

The repair rule will be changed explicitly so that obstruction may produce a
bounded set of strictly deeper candidate representations.

Independent verifier authority will score those candidates and may authorize
the smallest candidate that supplies sufficient penalized predictive/decision
improvement.

This retirement occurred before adaptive implementation and before frozen
evaluation inspection.
