# PRIME Canonical Agent Benchmark v1.3
## Frozen Held-Out Evaluation Result

Status:

    COMPLETE

Evaluation protocol commit:

    dda47f6ec3cdfc611e27bd7f2f9a8ec16c1cf28d

Frozen hypothesis-bearing implementation SHA-256:

    3f8082ad340af46f786a773922ec4a5a49d42fda01f77fe658b911d44afe957e

Evaluation result SHA-256:

    06542efb67ea9fbfefb482c9e7fcfc77d5cc5a884e31266578ed2831dcbffab4

Evaluation worlds:

    128

Condition-world rows:

    1024

Evaluation seeds:

    3000 through 3127 inclusive

All integrity checks passed.

---

# Condition means

    REACTIVE                       611823
    FIXED-H1                       721981
    FIXED-H2                       831280
    FIXED-H4                       918191
    ADAPTIVE-NO-VERIFIER           904833
    FULL-PRIME-V1.2-REFERENCE      918817
    FACTOR-WITNESS-CARRIER-COST    921246
    FULL-PRIME-V1.3                924347

Mean final-window reward:

    FIXED-H4                       948836
    FULL-PRIME-V1.2-REFERENCE      948836
    FACTOR-WITNESS-CARRIER-COST    948836
    FULL-PRIME-V1.3                948836

---

# Primary architectural-upgrade claim

Comparison:

    FULL-PRIME-v1.3
        minus
    FULL-PRIME-v1.2-REFERENCE

Observed paired mean AULC delta:

    +5529 ppm

Frozen deterministic bootstrap 95% interval:

    [+3921, +7200] ppm

Final-window delta:

    0 ppm

Exact final-depth recovery:

    FULL-PRIME-v1.3:
        128/128

    FULL-PRIME-v1.2-REFERENCE:
        128/128

Integrity:

    PASS

Primary architectural-upgrade claim:

    SUPPORTED

Thus the frozen v1.3 mechanism improved held-out online-learning efficiency
relative to the frozen v1.2 reference while preserving exact minimal
representation recovery and final-window performance.

---

# Fixed-H4 comparison

Comparison:

    FULL-PRIME-v1.3
        minus
    FIXED-H4

Observed paired mean AULC delta:

    +6155 ppm

Frozen deterministic bootstrap 95% interval:

    [+3220, +9151] ppm

Final-window delta:

    0 ppm

Integrity:

    PASS

Fixed-memory superiority claim:

    SUPPORTED

Within this frozen MemoryAlias-POMDP benchmark, FULL-PRIME-v1.3 therefore
outperformed the development-selected FIXED-H4 comparator despite beginning
from H0 and having to discover its required representation online.

---

# Factorization-only claim

Comparison:

    FACTOR-WITNESS-CARRIER-COST
        minus
    FULL-PRIME-v1.2-REFERENCE

Observed paired mean AULC delta:

    +2428 ppm

Frozen deterministic bootstrap 95% interval:

    [+1698, +3187] ppm

Final-window delta:

    0 ppm

Exact final-depth recovery:

    128/128 versus 128/128

Factorization-only claim:

    SUPPORTED

Thus replacing complete-candidate carrier evidence with factorized historical
coordinate witnesses improved held-out learning efficiency while retaining the
old v1.2 carrier complexity cost.

---

# Coordinate-repricing diagnostic

Comparison:

    FULL-PRIME-v1.3
        minus
    FACTOR-WITNESS-CARRIER-COST

Observed paired mean AULC delta:

    +3101 ppm

Frozen deterministic bootstrap interval:

    [+2158, +4090] ppm

Status:

    DIAGNOSTIC ONLY

This comparison was not preregistered as a separate inferential claim and
must remain described as diagnostic.

---

# Representation recovery

FULL-PRIME-v1.3 exact final-depth recovery:

    128/128

By hidden dependency depth:

    d=0 -> H0:
        32/32

    d=1 -> H1:
        32/32

    d=2 -> H2:
        32/32

    d=4 -> H4:
        32/32

Accepted FULL-PRIME-v1.3 repairs:

    96

Rejected repairs:

    0

No representation repair occurred in d=0 worlds.

---

# Deep-evidence mechanism

Held-out d=4 mean authorization latency:

    FULL-PRIME-v1.2-REFERENCE:
        59 scored events

    FACTOR-WITNESS-CARRIER-COST:
        34 scored events

    FULL-PRIME-v1.3:
        4 scored events

Held-out d=4 maximum authorization latency:

    FULL-PRIME-v1.2-REFERENCE:
        78

    FACTOR-WITNESS-CARRIER-COST:
        57

    FULL-PRIME-v1.3:
        17

Immediate d=4 FULL-v1.3 authorizations:

    9 / 32

Held-out d=4 mean AULC:

    FULL-PRIME-v1.2-REFERENCE:
        878948

    FACTOR-WITNESS-CARRIER-COST:
        887971

    FULL-PRIME-v1.3:
        900376

Every d=4 world ended at H4 in all three verifier-governed adaptive
conditions.

---

# Scientific interpretation

v1.1 established exact adaptive representation discovery but showed that
fixed prospective verification imposed a severe online-learning cost.

v1.2 replaced fixed prospective evidence with passive anytime-valid
verification. This preserved exact representation recovery and established a
held-out advantage over ungated adaptive growth, but superiority over FIXED-H4
was not established.

v1.3 targeted the remaining deep-representation evidence bottleneck with:

1. factorized lag witnesses rather than full deeper-state carriers; and
2. coordinate-description complexity pricing rather than pricing the complete
   induced tabular carrier.

The frozen held-out evaluation supports the preregistered architectural-upgrade
claim and the factorization-only claim.

It also supports superiority of FULL-PRIME-v1.3 over the development-selected
FIXED-H4 comparator on this benchmark.

The d=4 diagnostics provide a mechanistic explanation: mean authorization
latency fell from 59 scored events in the v1.2 reference to 4 in FULL-v1.3,
while exact representation recovery remained perfect.

---

# Claim boundary

The supported result is:

A verifier-governed adaptive representation-repair agent, starting from H0,
outperformed its frozen v1.2 predecessor and the development-selected
maximal-memory fixed H4 comparator on the frozen held-out MemoryAlias-POMDP
benchmark while preserving exact minimal representation recovery.

This does not establish:

- universal superiority over fixed-memory agents;
- superiority over learned recurrent-memory agents;
- general POMDP superiority;
- AGI;
- broad real-world generality;
- production security.

A separately frozen learned-memory comparison remains required.
