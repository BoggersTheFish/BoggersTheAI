# PRIME M20 Universal Adaptive-State Arena v0.2
## Frozen Held-Out Evaluation Plan

Status:

    FROZEN BEFORE HELD-OUT EXECUTION

Held-out seeds:

    6000..6031 inclusive

Task families:

    12

Paired task/seed worlds:

    384

Conditions:

    REACTIVE
    FIXED-H8
    ORACLE-FEATURE
    M20-CONSTRUCTION

Total condition-world rows:

    1536

---

# Primary held-out comparison

For every task/seed world i:

    D_i =
        AULC(M20-CONSTRUCTION, i)
        -
        AULC(FIXED-H8, i)

Primary claim:

    M20-CONSTRUCTION improves online learning efficiency over FIXED-H8.

SUPPORTED iff all are true:

1. observed paired mean D_i > 0;
2. frozen deterministic paired-bootstrap lower bound > 0;
3. mean final-window accuracy delta >= 0;
4. mean final-window balanced-accuracy delta >= 0;
5. predictive-partition recovery = 384/384;
6. CURRENT unnecessary-construction count = 0/32;
7. all M20 receipt chains verify;
8. all integrity checks pass.

Otherwise:

    NOT SUPPORTED

---

# Predictive representation recovery

Exact-expression recovery is reported.

Predictive-partition recovery is also reported.

For binary constructed features, exact complement:

    q(h) = 1 - f(h)

counts as the same predictive partition because both induce the same two-cell
partition of the history space.

This equivalence rule was frozen before v0.2 development.

---

# Oracle comparison

M20-CONSTRUCTION versus ORACLE-FEATURE is diagnostic.

Report:

- paired AULC delta;
- final-window accuracy delta;
- final-window balanced-accuracy delta.

No superiority claim against the oracle is preregistered.

The oracle comparison primarily measures remaining construction/authorization
latency.

---

# Deterministic paired bootstrap

Replicates:

    16384

Paired sample size:

    384

Sampling:

    with replacement

Seed:

    0x4D32305630324556

For bootstrap replicate r and draw j:

    index =
        splitmix64(
            seed
            XOR splitmix64(r)
            XOR splitmix64(j)
        )
        mod 384

Store sampled SUMS.

Sort the 16384 sums.

Frozen interval indices:

    lower = 409
    upper = 15974

The lower confidence bound is positive iff:

    sorted_sums[409] > 0

No alternative interval or test may be selected after evaluation.

---

# Claim boundary

A supported result would establish controlled held-out evidence that the frozen
M20 construction architecture achieves better online learning efficiency than
the frozen raw H8 representation on this arena while recovering the required
predictive representation class.

It would not establish:

- AGI;
- universal representation learning;
- superiority over recurrent learned state;
- universal POMDP superiority;
- broad real-world generality.

A separately frozen recurrent-memory confrontation remains required.
