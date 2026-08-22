# PRIME Canonical Agent Benchmark v1.2
## Frozen Held-Out Evaluation Analysis Plan

Status: FROZEN BEFORE ANY v1.2 EVALUATION SEED IS RUN

Evaluation seeds:

    2000 through 2127 inclusive

Paired worlds:

    128

Development-selected fixed comparator:

    FIXED-H4

The development result is not part of the held-out success criterion.

---

# 1. Conditions

Every held-out world is evaluated under:

    REACTIVE
    FIXED-H1
    FIXED-H2
    FIXED-H4
    ADAPTIVE-NO-VERIFIER
    VERIFIER-NO-REPAIR
    FULL-PRIME-V1.2

All 128 worlds are retained.

---

# 2. Primary comparison

For each world i:

    D_i =
        AULC(FULL-PRIME-V1.2, i)
        -
        AULC(FIXED-H4, i)

Primary paired mean advantage:

    sum(D_i) / 128

The primary mean must be strictly positive.

---

# 3. Deterministic paired bootstrap

This protocol reuses the v1.1 bootstrap design without modification.

Bootstrap replicates:

    16384

Paired sample size:

    128

Sampling:

    with replacement

Generator seed:

    0x5052494D45563131

For replicate r and draw j:

    index =
        splitmix64(
            BOOTSTRAP_SEED
            XOR splitmix64(r)
            XOR splitmix64(j)
        )
        mod 128

Each replicate stores the SUM of 128 sampled paired deltas.

Sorted zero-based interval indices:

    lower = 409
    upper = 15974

The primary confidence criterion is:

    bootstrap_sums[409] > 0

No normal approximation or post-evaluation interval choice is allowed.

---

# 4. Final-performance criterion

For each paired world:

    F_i =
        final_window(FULL-PRIME-V1.2, i)
        -
        final_window(FIXED-H4, i)

The conservative zero-margin interpretation remains frozen:

    sum(F_i) >= 0

No degradation allowance is introduced.

---

# 5. Primary claim

The preregistered primary claim is SUPPORTED only when all are true:

1. paired mean AULC delta FULL-PRIME-V1.2 minus FIXED-H4 > 0;
2. deterministic paired-bootstrap lower bound > 0;
3. mean final-window delta >= 0;
4. all frozen-input, receipt, deterministic and source-integrity checks pass.

Otherwise:

    NOT SUPPORTED

---

# 6. Verifier-specific comparison

For every world:

    V_i =
        AULC(FULL-PRIME-V1.2, i)
        -
        AULC(ADAPTIVE-NO-VERIFIER, i)

Use the identical 16384-replicate paired bootstrap.

Verifier-specific performance is SUPPORTED only when:

    sum(V_i) > 0

and:

    bootstrap lower bound > 0

and integrity checks pass.

Otherwise:

    NOT SUPPORTED

---

# 7. Structural diagnostics

Report for FULL-PRIME-V1.2:

- final representation depth;
- exact required-depth recovery;
- accepted repair count;
- rejected repair count;
- proposal count;
- verifier-supported repair count;
- canonical receipt count;
- receipt-chain validity.

The hidden dependency depth may be used only after execution for diagnostic
grouping.

It is never available to policy, proposal or verifier logic.

Exact-depth recovery is not substituted for the primary AULC criterion.

---

# 8. Authorization-latency diagnostics

For resolved FULL-PRIME-V1.2 repairs report:

- authorization latency in scored events;
- maximum authorization latency;
- immediate-authorization count;
- discordant evidence already accumulated at obstruction;
- additional discordant evidence required after obstruction;
- breakdown by hidden dependency depth.

Historical v1.1 reference:

    fixed prospective evidence duration:
        4 complete episodes

    equivalent prospective scored evidence events:
        256

This historical quantity is descriptive only because v1.1 and v1.2 use
different held-out worlds.

No inferential cross-version latency claim is preregistered.

---

# 9. Integrity

Before evaluation:

- Git worktree must be clean;
- frozen v1.2 hashes must verify;
- frozen v1.1 parent result hash must verify;
- selected comparator must remain FIXED-H4;
- core v1.2 implementation SHA-256 must equal:

    bed64cbe558c928d3793c915e34260638c9c0ed3f7061c350695e769b5c3efc9

During evaluation:

- every adaptive result must report source_dirty=false;
- every adaptive result must report the frozen implementation hash;
- every receipt chain must verify against its count and tip anchors;
- every condition must produce exactly 128 worlds.

Evaluation output must be written outside the Git worktree.

---

# 10. Claim boundary

Even a positive result is controlled mechanistic benchmark evidence.

It is not evidence of:

- AGI;
- universal POMDP superiority;
- universal superiority over recurrent learned memory;
- production security;
- broad real-world generality.

The frozen learned-memory-baseline boundary remains in force.
