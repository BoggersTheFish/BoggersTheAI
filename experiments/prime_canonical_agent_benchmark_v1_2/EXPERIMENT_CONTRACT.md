# PRIME Canonical Agent Benchmark v1.2
## Frozen Experimental Contract

Status: FROZEN BEFORE v1.2 IMPLEMENTATION OR v1.2 RESULT INSPECTION

v1.2 is a successor experiment to the completed v1.1 benchmark.

v1.1 remains immutable.

---

# 1. Parent result

PRIME Canonical Agent Benchmark v1.1 produced:

    preregistered primary claim:
        NOT SUPPORTED

    exact final representation recovery:
        128 / 128

    FULL-PRIME mean AULC:
        852920 ppm

    FIXED-H4 mean AULC:
        918420 ppm

    ADAPTIVE-NO-VERIFIER mean AULC:
        905346 ppm

    FULL-PRIME minus FIXED-H4:
        -65501 ppm

    frozen 95% bootstrap interval:
        [-74816, -55695] ppm

    FULL-PRIME minus ADAPTIVE-NO-VERIFIER:
        -52427 ppm

The v1.1 evidence therefore indicates that representation selection succeeded
while verifier latency reduced online learning efficiency.

---

# 2. v1.2 research question

Can verifier sovereignty and precise representation repair be retained while
reducing evidence-acquisition and authorization latency enough to improve
online learning efficiency?

The intended architectural change is not a weaker verifier.

The intended change is to eliminate unnecessary waiting by allowing the
independent verifier to reuse bounded evidence that naturally arises during
ordinary agent interaction.

---

# 3. Reused frozen substrate

v1.2 reuses the v1.1 task family and common learning apparatus:

    MemoryAlias-POMDP
    binary observation/action interface
    permitted representation depths {0, 1, 2, 4}
    deterministic SplitMix64 generators
    common BinaryTabularLearner
    64 episodes
    64 scored decisions per episode
    4 warmup observations per episode
    deterministic exploration period 10
    integer-only canonical metrics

The environment semantics are not modified to make v1.2 easier.

---

# 4. Fresh development and evaluation worlds

v1.1 evaluation seeds are permanently burned and may not be reused as
held-out v1.2 evidence.

v1.2 development seeds:

    100 through 131 inclusive

Count:

    32

v1.2 frozen evaluation seeds:

    2000 through 2127 inclusive

Count:

    128

All four hidden dependency depths are balanced in both sets.

The evaluation seeds may not be inspected until the v1.2 implementation,
adaptive rules, statistical analysis plan, and evaluation harness are frozen.

---

# 5. Conditions

v1.2 must evaluate at least:

    REACTIVE
    FIXED-H1
    FIXED-H2
    FIXED-H4
    ADAPTIVE-NO-VERIFIER
    VERIFIER-NO-REPAIR
    FULL-PRIME-V1.2

The common learner must remain the same wherever technically applicable.

Representation management remains the experimental independent variable.

---

# 6. Representation authority

FULL-PRIME-V1.2 begins with policy representation:

    H0

The policy may act only through the currently authorized canonical
representation.

A deeper candidate representation may never control policy before
authorization.

Proposal is not authority.

Verifier support is not canonical mutation.

Only an explicit authorization event may change the policy representation.

---

# 7. v1.2 evidence principle

The verifier may maintain bounded, passive candidate-side evidence derived
from observations and action/reward feedback that the system legitimately
receives during ordinary interaction.

Such passive evidence:

- may not influence policy action selection;
- may not expose hidden environment depth;
- may not mutate canonical policy representation;
- may not receive future observations;
- may not access evaluation labels;
- must remain deterministic and provenance-bound.

This is intended to distinguish:

    policy representation capacity

from:

    verifier evidence collection

The adaptive rules governing this evidence are frozen separately before
implementation.

---

# 8. Sequential authorization principle

v1.2 may replace the fixed four-complete-episode prospective verification delay
used in v1.1 with a deterministic sequential evidence rule.

The verifier must authorize only when the frozen evidence criterion is
satisfied.

It may stop collecting evidence as soon as support is sufficient.

Failure to obtain sufficient support must leave canonical representation
unchanged.

No threshold may be tuned after adaptive development results are observed.

---

# 9. Development comparator selection

FIXED-H1, FIXED-H2 and FIXED-H4 are run on every v1.2 development seed.

The fixed comparator is the condition with greatest mean primary AULC.

Ties select the smaller representation.

This selection is frozen before v1.2 evaluation.

---

# 10. Primary metric

Primary metric:

    area under the online learning curve

represented canonically in integer ppm.

The exact calculation remains the same as v1.1.

Every evaluation world is retained.

---

# 11. Primary v1.2 performance claim

The primary claim is supported only if FULL-PRIME-V1.2 has:

1. positive paired mean primary-AULC advantage over the development-selected
   fixed representation;

2. a preregistered paired-bootstrap 95% lower bound strictly greater than zero;

3. no degradation in mean final-window reward under the frozen conservative
   zero-margin interpretation;

4. all integrity and deterministic replay checks passing.

A negative result is retained.

---

# 12. Verifier-specific claim

FULL-PRIME-V1.2 is separately compared with ADAPTIVE-NO-VERIFIER.

Verifier-governed adaptation has a positive performance contribution only if:

    mean paired AULC delta > 0

and the frozen paired-bootstrap 95% lower bound is:

    > 0

Failure is reported explicitly.

---

# 13. Mechanistic representation-repair result

v1.2 reports:

- final representation depth;
- hidden-depth diagnostic after execution;
- exact-depth recovery rate;
- proposal count;
- accepted repair count;
- rejected repair count;
- verifier-supported repair count;
- authorization latency;
- canonical receipt count;
- receipt-chain integrity.

Exact-depth recovery is not substituted for the primary AULC criterion.

---

# 14. Latency result

v1.2 must explicitly compare representation authorization latency with v1.1.

The benchmark should distinguish:

    evidence already available at obstruction

from:

    additional evidence required after obstruction

and report both where applicable.

The purpose is to test whether v1.1's observed performance deficit can be
localized to evidence-acquisition latency.

---

# 15. Determinism and receipts

All authoritative v1.2 adaptive decisions must remain:

- deterministic;
- canonical;
- hash-chained;
- provenance-bound;
- replayable;
- fail-closed;
- free of timestamps and random UUIDs;
- free of native JSON floats.

Receipt tampering must be detected.

---

# 16. Development restriction

Development seeds may be used to:

- debug implementation defects;
- verify invariants;
- confirm implementation matches frozen rules;
- select the frozen fixed-history comparator.

They may not be used to tune the frozen verifier rule after adaptive
performance is observed.

A substantive rule change requires a successor version.

---

# 17. Evaluation restriction

Seeds 2000 through 2127 must remain inaccessible to ordinary development
execution.

Evaluation requires an explicit frozen-evaluation unlock path.

Before that unlock:

- adaptive rules must be frozen;
- implementation must be committed;
- tests must pass;
- worktree must be clean;
- implementation hash must be frozen;
- evaluation-analysis plan must be frozen;
- evaluation harness must be frozen.

---

# 18. Learned-memory baseline boundary

v1.2 remains a controlled mechanistic benchmark unless a learned-memory
baseline such as a recurrent model is added under a separately frozen protocol.

A positive v1.2 result alone must not be generalized into universal superiority
over learned recurrent agents.

---

# 19. Falsification

The experiment is successful scientifically even if the performance hypothesis
fails.

In particular, retain and report outcomes where:

- verifier latency remains too expensive;
- ungated adaptation remains superior;
- fixed H4 remains superior;
- sequential evidence increases false repair;
- exact-depth recovery degrades;
- added verifier state produces no measurable benefit.

No mechanism is protected from falsification.
