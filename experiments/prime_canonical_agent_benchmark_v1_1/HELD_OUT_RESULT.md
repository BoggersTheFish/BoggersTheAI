# PRIME Canonical Agent Benchmark v1.1
## Frozen Held-Out Evaluation Result

Status: COMPLETE

Source commit:

    8d2f03495bead25bedb31c6008e46d1ebb22b8ee

Frozen hypothesis-bearing core SHA-256:

    b98a84c501979eb05d221bdfb603dfb68895ee541696d7a7c80045feb7a8bb6f

Evaluation worlds:

    128

Frozen evaluation seeds:

    1000 through 1127 inclusive

Evaluation result SHA-256:

    b58a51857864e61837168dbb5e36ef69d26a600b5775aa2dcc3cb17651962388

All integrity checks passed.

---

# Preregistered primary result

    NOT SUPPORTED

FULL-PRIME did not outperform the development-selected FIXED-H4 comparator
on frozen held-out online-learning AULC.

Mean primary AULC:

    REACTIVE               613189
    FIXED-H1               723884
    FIXED-H2               832090
    FIXED-H4               918420
    ADAPTIVE-NO-VERIFIER   905346
    VERIFIER-NO-REPAIR     613189
    FULL-PRIME             852920

FULL-PRIME minus FIXED-H4:

    mean paired delta:
        -65501 ppm

    frozen deterministic bootstrap 95% interval:
        [-74816, -55695] ppm

The confidence interval lies entirely below zero.

Therefore the preregistered primary performance claim is not supported.

---

# Final performance

Mean final-window reward:

    FIXED-H4               949096
    ADAPTIVE-NO-VERIFIER   949096
    FULL-PRIME             949096

FULL-PRIME therefore showed no final-window degradation relative to FIXED-H4.

The performance deficit is an online adaptation-efficiency deficit rather than
a final-policy-quality deficit.

---

# Verifier-specific result

FULL-PRIME minus ADAPTIVE-NO-VERIFIER:

    mean paired AULC delta:
        -52427 ppm

    frozen deterministic bootstrap 95% interval:
        [-59091, -45713] ppm

Verifier-specific performance claim:

    NOT SUPPORTED

The frozen prospective verification process imposed more online-learning cost
than the ungated adaptive repair mechanism.

---

# Representation-repair result

Despite the negative primary performance result, FULL-PRIME recovered the
exact environment-required final representation depth in every held-out world:

    hidden d=0 -> final H0: 32/32
    hidden d=1 -> final H1: 32/32
    hidden d=2 -> final H2: 32/32
    hidden d=4 -> final H4: 32/32

Total:

    128/128 exact final-depth recovery

FULL-PRIME accepted:

    96 repairs

This equals exactly the number of held-out worlds requiring nonzero memory.

No d=0 world underwent an accepted representation repair.

ADAPTIVE-NO-VERIFIER accepted:

    192 repairs

This is consistent with incremental ladder traversal:

    d=1: H0 -> H1
    d=2: H0 -> H1 -> H2
    d=4: H0 -> H1 -> H2 -> H4

Thus verifier governance substantially improved repair targeting, but not
online-learning efficiency under the frozen four-episode prospective probe.

---

# Mean cumulative regret

    FIXED-H4               234
    ADAPTIVE-NO-VERIFIER   251
    FULL-PRIME             322

Relative to FIXED-H4, FULL-PRIME incurred approximately 88 additional
incorrect decisions per held-out world.

Relative to ungated adaptive repair, FULL-PRIME incurred approximately 71
additional incorrect decisions per world.

---

# Interpretation

The held-out evidence supports the mechanistic observation that the frozen
verifier can identify and authorize the minimal sufficient representation with
very high reliability in this controlled benchmark.

It does not support the stronger claim that the resulting verifier-governed
adaptive system improves online learning efficiency over the frozen maximum
history representation or over ungated adaptive growth.

The principal observed bottleneck is verification latency.

A successor experiment should therefore investigate whether verifier
sovereignty can be retained while reducing evidence-acquisition and
authorization latency.

The v1.1 rules, thresholds, implementation, analysis plan, and negative primary
result must remain immutable.

Any successor is a new explicitly linked experiment.

---

# Claim boundary

This is controlled benchmark evidence.

It is not evidence of AGI, general POMDP superiority, universal adaptive
representation superiority, production security, or broad real-world
generality.

The original frozen requirement for a learned-memory baseline remains necessary
before making a stronger public comparative performance claim.
