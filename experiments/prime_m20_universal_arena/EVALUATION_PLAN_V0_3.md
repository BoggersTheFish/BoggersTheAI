# PRIME M20 Universal Adaptive-State Arena v0.3
## Frozen Held-Out Evaluation Plan

Status:

    FROZEN BEFORE HELD-OUT EXECUTION

Held-out stream seeds:

    6000..6031 inclusive

Number of independent stream-seed clusters:

    32

Tasks per seed:

    12

Paired task/seed worlds:

    384

Conditions:

    REACTIVE
    FIXED-H8
    ORACLE-FEATURE
    M20-CONSTRUCTION

Total rows:

    1536

No held-out seed had been executed when this plan was frozen.

---

# Primary comparison

For task t and stream seed s:

    D(s,t) =
        AULC(M20-CONSTRUCTION,s,t)
        -
        AULC(FIXED-H8,s,t)

Overall observed effect:

    mean over all 384 paired task/seed worlds.

---

# Dependence structure

All 12 tasks belonging to the same stream seed reuse the same underlying
binary observation stream.

Therefore task/seed worlds sharing a seed are not treated as independent
bootstrap sampling units.

The bootstrap resamples the 32 stream seeds as clusters.

Whenever seed s is sampled, all 12 paired task differences D(s,t) are included.

This preserves within-stream dependence across task families.

---

# Deterministic cluster bootstrap

Bootstrap replicates:

    16384

Cluster count:

    32

Tasks per cluster:

    12

Sampling:

    32 stream-seed clusters with replacement per replicate

Bootstrap RNG seed:

    0x4D3230563033434C

For replicate r and draw j:

    index =
        splitmix64(
            BOOTSTRAP_SEED
            XOR splitmix64(r)
            XOR splitmix64(j)
        )
        mod 32

For every selected cluster, include all 12 task differences.

Sort the 16384 bootstrap mean differences.

Frozen interval indices:

    lower = 409
    upper = 15974

No alternate confidence interval or inferential test may be selected after
held-out evaluation.

---

# Primary claim

Claim:

    Frozen PRIME M20 v0.3 improves online learning efficiency over FIXED-H8
    on the held-out Universal Adaptive-State Arena.

SUPPORTED iff ALL of the following hold:

1. observed mean M20-H8 AULC delta > 0;

2. deterministic seed-cluster bootstrap lower bound > 0;

3. mean final-window accuracy delta M20-H8 >= 0;

4. mean final-window balanced-accuracy delta M20-H8 >= 0;

5. predictive-partition recovery = 384/384;

6. all 32 CURRENT worlds authorize zero unnecessary constructions;

7. every M20 receipt chain verifies;

8. row/seed/task/condition integrity checks all pass.

Otherwise:

    NOT SUPPORTED

---

# Secondary descriptive results

Report without changing the primary decision rule:

    exact-expression recovery;

    exact versus complement quotient relations;

    task-family AULC;

    authorization latency;

    number of M20-H8 positive/tied/negative task-seed worlds;

    M20-ORACLE AULC gap;

    M20-ORACLE final-window gap;

    target prevalence and balanced accuracy;

    active construction counts.

---

# Oracle interpretation

ORACLE-FEATURE receives the correct predictive representation immediately.

M20-versus-ORACLE therefore measures the cost of online construction and
authorization.

No superiority claim against ORACLE-FEATURE is preregistered.

---

# Claim boundary

A SUPPORTED result would establish controlled held-out evidence that the frozen
M20 v0.3 architecture learns more efficiently than a frozen raw H8 state on
this arena while recovering the required predictive representation class under
a globally alpha-spent verifier.

It would NOT establish:

    AGI;

    universal representation learning;

    superiority on arbitrary POMDPs;

    superiority over learned recurrent state;

    language understanding;

    real-world generality.

A recurrent-memory confrontation and transfer experiments remain separate
future tests.
