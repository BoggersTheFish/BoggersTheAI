# PRIME Canonical Agent Benchmark v1.3
## Frozen Held-Out Evaluation Analysis Plan

Status:

    FROZEN BEFORE ANY v1.3 EVALUATION WORLD IS RUN

Evaluation seeds:

    3000 through 3127 inclusive

World count:

    128

Development-selected fixed comparator:

    FIXED-H4

Frozen hypothesis-bearing core SHA-256:

    3f8082ad340af46f786a773922ec4a5a49d42fda01f77fe658b911d44afe957e

---

# 1. Held-out conditions

Every evaluation world is run under:

    REACTIVE
    FIXED-H1
    FIXED-H2
    FIXED-H4
    ADAPTIVE-NO-VERIFIER
    FULL-PRIME-V1.2-REFERENCE
    FACTOR-WITNESS-CARRIER-COST
    FULL-PRIME-V1.3

All 128 worlds are retained.

Total condition-world rows:

    1024

---

# 2. Primary v1.3 upgrade comparison

For each held-out world i:

    D_i =
        AULC(FULL-PRIME-V1.3, i)
        -
        AULC(FULL-PRIME-V1.2-REFERENCE, i)

The primary v1.3 upgrade claim is SUPPORTED only if:

1. paired mean D_i > 0;
2. frozen paired-bootstrap lower bound > 0;
3. mean final-window delta >= 0;
4. exact final-depth recovery of FULL-PRIME-V1.3 is not below that of
   FULL-PRIME-V1.2-REFERENCE;
5. all integrity checks pass.

Otherwise:

    NOT SUPPORTED

---

# 3. Fixed-H4 comparison

For every world:

    H_i =
        AULC(FULL-PRIME-V1.3, i)
        -
        AULC(FIXED-H4, i)

The fixed-memory superiority claim is SUPPORTED only if:

1. paired mean H_i > 0;
2. frozen paired-bootstrap lower bound > 0;
3. mean final-window delta >= 0;
4. all integrity checks pass.

Otherwise:

    NOT SUPPORTED

This claim is separate from the primary architectural-upgrade claim.

---

# 4. Factorization-only comparison

For every world:

    F_i =
        AULC(FACTOR-WITNESS-CARRIER-COST, i)
        -
        AULC(FULL-PRIME-V1.2-REFERENCE, i)

The factorization-only claim is SUPPORTED only if:

1. paired mean F_i > 0;
2. frozen paired-bootstrap lower bound > 0;
3. mean final-window delta >= 0;
4. exact final-depth recovery is not degraded relative to the v1.2 reference;
5. all integrity checks pass.

Otherwise:

    NOT SUPPORTED

This isolates factorized evidence while retaining the old carrier cost.

---

# 5. Repricing diagnostic

Also report:

    R_i =
        AULC(FULL-PRIME-V1.3, i)
        -
        AULC(FACTOR-WITNESS-CARRIER-COST, i)

A paired bootstrap interval is reported.

This comparison is diagnostic only.

No separately preregistered inferential claim is attached to it.

---

# 6. Deterministic paired bootstrap

Reuse the frozen v1.1/v1.2 procedure without modification.

Replicates:

    16384

Paired sample size:

    128

Sampling:

    with replacement

Seed:

    0x5052494D45563131

For replicate r and draw j:

    index =
        splitmix64(
            BOOTSTRAP_SEED
            XOR splitmix64(r)
            XOR splitmix64(j)
        )
        mod 128

Store the SUM of 128 sampled paired deltas.

Sort replicate sums.

Frozen zero-based interval indices:

    lower = 409
    upper = 15974

A lower confidence bound is positive iff:

    sorted_bootstrap_sums[409] > 0

No post-evaluation interval selection or alternative test is permitted.

---

# 7. Structural diagnostics

For:

    FULL-PRIME-V1.2-REFERENCE
    FACTOR-WITNESS-CARRIER-COST
    FULL-PRIME-V1.3

report:

- exact final-depth recovery;
- final-depth distribution by hidden depth;
- proposal count;
- accepted repair count;
- rejected repair count;
- verifier-supported repair count;
- unnecessary repairs in d=0 worlds;
- receipt-chain integrity.

For FULL-PRIME-V1.3, 128/128 remains the strongest structural gate.

---

# 8. Deep-evidence diagnostics

For the three verifier-governed adaptive conditions report, overall and by
hidden depth:

- mean authorization latency in scored events;
- maximum authorization latency;
- immediate authorization count;
- selected witness-lag distribution where applicable.

The central d=4 mechanistic comparison is:

    FULL-PRIME-V1.2-REFERENCE
        versus
    FACTOR-WITNESS-CARRIER-COST
        versus
    FULL-PRIME-V1.3

Development values are not part of the held-out success criterion.

---

# 9. Integrity requirements

Before evaluation:

- Git worktree clean;
- frozen contract valid;
- frozen lineage valid;
- frozen adaptive rules valid;
- frozen fixed comparator valid;
- frozen development diagnostic valid;
- parent v1.2 result valid;
- comparator remains FIXED-H4;
- core implementation SHA-256 exactly:

    3f8082ad340af46f786a773922ec4a5a49d42fda01f77fe658b911d44afe957e

During evaluation:

- adaptive source_dirty=false;
- adaptive source commit equals frozen evaluation source commit;
- adaptive core hash equals frozen core hash;
- all receipt chains verify against count and tip;
- every condition yields exactly 128 worlds.

Output must be outside the Git repository.

---

# 10. Claim boundary

A positive v1.3 result is controlled mechanistic benchmark evidence.

It does not establish:

- AGI;
- universal POMDP superiority;
- superiority over learned recurrent memory;
- universal superiority over fixed memory;
- production security;
- broad real-world generality.

A separately frozen learned-memory benchmark remains required.
