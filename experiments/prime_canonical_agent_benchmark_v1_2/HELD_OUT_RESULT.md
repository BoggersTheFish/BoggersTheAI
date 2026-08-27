# PRIME Canonical Agent Benchmark v1.2
## Frozen Held-Out Evaluation Result

Status:

    COMPLETE

Evaluation protocol commit:

    96c719622951e64fd2c6e3aea911e49927385ccb

Frozen hypothesis-bearing implementation SHA-256:

    bed64cbe558c928d3793c915e34260638c9c0ed3f7061c350695e769b5c3efc9

Evaluation result SHA-256:

    6ce64dc7aa0bcc44ce1453788162a007ea79429d0283e69d6ba4e8c9e91028f

Evaluation worlds:

    128

Evaluation seeds:

    2000 through 2127 inclusive

All integrity checks passed.

---

# Preregistered primary result

    NOT SUPPORTED

Mean primary AULC:

    REACTIVE                 611477
    FIXED-H1                 722486
    FIXED-H2                 831241
    FIXED-H4                 918084
    ADAPTIVE-NO-VERIFIER     905651
    VERIFIER-NO-REPAIR       611477
    FULL-PRIME-V1.2          918754

Paired FULL-PRIME-v1.2 minus FIXED-H4:

    observed mean delta:
        +669 ppm

    frozen deterministic bootstrap 95% interval:
        [-3644, +4983] ppm

The paired mean was positive, but the frozen lower confidence bound was not
strictly greater than zero.

Therefore the preregistered primary superiority claim is:

    NOT SUPPORTED

---

# Final-window performance

Mean final-window reward:

    FIXED-H4                 949233
    ADAPTIVE-NO-VERIFIER     949233
    FULL-PRIME-V1.2          949233

FULL-PRIME-v1.2 therefore showed no final-window degradation.

Mean cumulative regret:

    FIXED-H4                 234
    ADAPTIVE-NO-VERIFIER     250
    FULL-PRIME-V1.2          234

---

# Verifier-specific held-out result

FULL-PRIME-v1.2 minus ADAPTIVE-NO-VERIFIER:

    observed mean paired AULC delta:
        +13102 ppm

    frozen deterministic bootstrap 95% interval:
        [+10414, +15817] ppm

The complete frozen interval lies above zero.

Verifier-specific claim:

    SUPPORTED

Within this controlled benchmark, verifier-governed representation selection
therefore improved online-learning AULC relative to the frozen ungated
adaptive representation-growth condition.

---

# Representation discovery

FULL-PRIME-v1.2 recovered the exact required final representation in every
held-out world:

    hidden d=0 -> H0: 32/32
    hidden d=1 -> H1: 32/32
    hidden d=2 -> H2: 32/32
    hidden d=4 -> H4: 32/32

Total:

    128/128 exact final-depth recovery

FULL-PRIME-v1.2:

    proposals:
        96

    accepted repairs:
        96

    rejected repairs:
        0

ADAPTIVE-NO-VERIFIER:

    proposals:
        192

    accepted repairs:
        192

    rejected repairs:
        0

Thus FULL-PRIME-v1.2 used exactly one authorized representation repair in each
of the 96 worlds requiring nonzero memory, while ungated adaptation traversed
the incremental representation ladder.

---

# Authorization latency

Across the 96 accepted FULL-PRIME-v1.2 repairs:

    mean authorization latency:
        25 scored events

    maximum authorization latency:
        100 scored events

    immediate authorizations:
        24

    mean discordant evidence already available at obstruction:
        13

    mean additional discordant evidence required after obstruction:
        11

Historical v1.1 fixed prospective evidence duration:

    256 scored events

The v1.2 architecture therefore substantially reduced the evidence-acquisition
delay associated with verifier authorization.

This historical comparison is descriptive rather than a paired cross-version
inferential test.

---

# Latency by required representation

For d=1:

    mean latency:
        2 scored events

    maximum:
        13

For d=2:

    mean latency:
        8 scored events

    maximum:
        22

For d=4:

    mean latency:
        64 scored events

    maximum:
        100

The deepest H4 repair remains the dominant authorization-latency regime.

---

# Scientific interpretation

v1.1 established that verifier-governed representation selection could recover
the exact required representation but incurred a large online-learning cost
from fixed prospective evidence collection.

v1.2 attacked that measured failure mode through passive prequential evidence
and anytime-valid sequential authorization.

The held-out v1.2 result shows:

1. exact representation recovery remained 128/128;

2. authorization latency fell substantially relative to the historical v1.1
   prospective evidence regime;

3. verifier-governed adaptation significantly outperformed ungated adaptive
   growth under the frozen verifier-specific comparison;

4. the large v1.1 deficit relative to FIXED-H4 was eliminated at the point
   estimate;

5. superiority over FIXED-H4 itself was not statistically established under the
   preregistered paired bootstrap criterion.

The primary claim must therefore remain negative.

The verifier-specific claim is supported.

---

# Claim boundary

This constitutes controlled mechanistic benchmark evidence that verifier
governance can improve adaptive representation-growth performance relative to
the frozen ungated alternative while preserving exact minimal representation
selection.

It does not establish:

- universal superiority over fixed representations;
- superiority over learned recurrent-memory agents;
- general POMDP superiority;
- AGI;
- production security;
- broad real-world generality.

The requirement for a separately frozen learned-memory comparator remains.
