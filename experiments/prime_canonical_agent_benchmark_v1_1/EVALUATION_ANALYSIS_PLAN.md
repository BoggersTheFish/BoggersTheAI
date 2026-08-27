# PRIME Canonical Agent Benchmark v1.1
## Frozen Evaluation Analysis Plan

Status: FROZEN BEFORE ANY EVALUATION SEED IS RUN

Evaluation seeds:

    1000 through 1127 inclusive

Number of paired worlds:

    128

No evaluation result has been inspected before this plan is frozen.

---

# 1. Conditions

Every evaluation seed is run under all seven frozen conditions:

    REACTIVE
    FIXED-H1
    FIXED-H2
    FIXED-H4
    ADAPTIVE-NO-VERIFIER
    VERIFIER-NO-REPAIR
    FULL-PRIME

The development-selected fixed comparator remains:

    FIXED-H4

This selection may not change after evaluation.

---

# 2. Primary comparison

For every evaluation seed i define:

    D_i =
        primary_AULC(FULL-PRIME, i)
        -
        primary_AULC(FIXED-H4, i)

The primary paired mean advantage is:

    mean(D_i)

Because all runs contain the same number of seeds, inference may operate on
the integer sum of paired deltas without floating-point arithmetic.

---

# 3. Deterministic paired bootstrap

Number of bootstrap replicates:

    16384

Sample size per replicate:

    128 paired worlds

Sampling:

    with replacement

Bootstrap generator seed:

    0x5052494D45563131

The generator is SplitMix64 using the already frozen benchmark SplitMix64
implementation.

For bootstrap replicate r and draw j, the sampled source index is:

    splitmix64(
        BOOTSTRAP_SEED
        XOR splitmix64(r)
        XOR splitmix64(j)
    ) mod 128

Each bootstrap replicate stores the SUM of its 128 sampled paired deltas.

The bootstrap sums are sorted in ascending order.

The frozen 95% percentile interval uses zero-based order-statistic indices:

    lower index = 409
    upper index = 15974

The primary confidence requirement is:

    bootstrap_sums[409] > 0

No normal approximation, floating-point bootstrap probability, or
post-evaluation choice of interval is permitted.

---

# 4. Primary support rule

The controlled-benchmark primary claim is supported only if ALL are true:

1. mean paired primary AULC advantage of FULL-PRIME over FIXED-H4 is positive;
2. the frozen paired-bootstrap 95% lower bound is strictly positive;
3. FULL-PRIME mean final-window reward is not below FIXED-H4 mean
   final-window reward;
4. all frozen-input, receipt-chain, source-cleanliness, and deterministic
   integrity checks pass.

For criterion 3, "not materially degraded" is conservatively interpreted as:

    mean_final(FULL-PRIME)
        -
    mean_final(FIXED-H4)
        >= 0

No favourable degradation margin is introduced.

A failure is retained and reported.

---

# 5. Verifier-specific comparison

Separately define:

    V_i =
        primary_AULC(FULL-PRIME, i)
        -
        primary_AULC(ADAPTIVE-NO-VERIFIER, i)

The same deterministic paired bootstrap algorithm is applied to V_i.

A verifier-specific performance contribution is supported only if:

    mean(V_i) > 0
    and
    bootstrap lower bound > 0

If ADAPTIVE-NO-VERIFIER performs equally or better, that is reported
explicitly.

This verifier-specific result does not rewrite the primary comparison.

---

# 6. Structural diagnostics

The following are reported but are not substituted for the primary metric:

- final representation depth;
- accepted repair count;
- rejected repair count;
- verifier-supported repair count;
- representation-change episodes;
- adaptation latency;
- canonical receipt count;
- receipt-chain validity;
- final-window reward;
- cumulative regret.

For diagnostic reporting only, worlds may be grouped by their known
environment-generation depth after the run.

The agent never receives that hidden depth.

---

# 7. Integrity requirements

Before evaluation begins:

- Git worktree must be clean.
- Frozen contract hashes must verify.
- Frozen adaptive-rule hash must verify.
- Frozen development diagnostic hash must verify.
- Core implementation hash must equal the development-frozen identity:

    b98a84c501979eb05d221bdfb603dfb68895ee541696d7a7c80045feb7a8bb6f

Evaluation output is written outside the Git worktree during execution.

Every adaptive receipt chain must verify.

Every adaptive result must report:

    source_dirty = false

The evaluation harness must fail closed if these conditions do not hold.

---

# 8. Evaluation-output policy

All 128 evaluation worlds are retained.

No seed may be removed because it is surprising, unfavourable, or anomalous.

A failed integrity run remains documented.

The evaluation report must state whether the preregistered primary claim is:

    SUPPORTED

or:

    NOT SUPPORTED

No threshold or metric may be changed after inspecting the evaluation.

---

# 9. Claim boundary

Even a positive result supports only controlled benchmark evidence for
verifier-governed adaptive representation repair.

It does not establish AGI, universal superiority, optimal POMDP solving,
production security, or broad real-world generality.

A stronger public performance claim additionally requires a learned-memory
baseline as specified in the frozen experiment contract.
