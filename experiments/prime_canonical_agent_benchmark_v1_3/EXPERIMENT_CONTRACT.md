# PRIME Canonical Agent Benchmark v1.3
## Factorized Deep-Evidence Experiment

Status:

    FROZEN BEFORE v1.3 ADAPTIVE IMPLEMENTATION OR RESULTS

v1.3 is a successor to the completed PRIME Canonical Agent Benchmark v1.2.

v1.2 remains immutable.

---

# 1. Parent result

PRIME v1.2 held-out evaluation:

    final commit:
        6f17789

    held-out worlds:
        128

    FULL-PRIME-v1.2 AULC:
        918754 ppm

    FIXED-H4 AULC:
        918084 ppm

    FULL minus FIXED-H4:
        +669 ppm

    frozen bootstrap interval:
        [-3644, +4983] ppm

    primary superiority claim:
        NOT SUPPORTED

    FULL minus ADAPTIVE-NO-VERIFIER:
        +13102 ppm

    verifier-specific frozen interval:
        [+10414, +15817] ppm

    verifier-specific claim:
        SUPPORTED

    exact final-depth recovery:
        128 / 128

    mean FULL authorization latency:
        25 scored events

    d=4 mean authorization latency:
        64 scored events

    d=4 maximum authorization latency:
        100 scored events

The principal remaining mechanistic bottleneck is deep-representation evidence
cost.

---

# 2. v1.3 research question

Can PRIME reduce the evidence complexity of discovering deep memory
requirements while preserving:

- verifier sovereignty;
- anytime-valid evidence;
- exact minimal representation selection;
- policy/verifier memory separation;
- deterministic receipts;
- held-out adaptive performance?

v1.3 specifically tests whether predictive evidence can be factorized over
new historical coordinates instead of requiring the verifier to estimate the
entire deeper representation carrier.

---

# 3. Reused task family

v1.3 reuses the canonical MemoryAlias-POMDP substrate.

Permitted policy representations remain:

    H0
    H1
    H2
    H4

The policy still begins at:

    H0

The environment semantics, horizon, reward interface and common learner are
not changed to make v1.3 easier.

---

# 4. Fresh worlds

v1.1 and v1.2 held-out worlds are permanently burned.

v1.3 development seeds:

    300 through 331 inclusive

Count:

    32

v1.3 held-out evaluation seeds:

    3000 through 3127 inclusive

Count:

    128

Evaluation seeds may not be run during development.

---

# 5. Core v1.3 experimental distinction

v1.2 candidate evidence predicts using the complete candidate representation.

Example:

    H0 -> H4

requires a verifier predictor over a five-bit H4 state carrier.

v1.3 introduces factorized lag witnesses.

For current canonical depth c and omitted historical coordinate k where:

    k > c

define witness state:

    W(c,k) =
        (current canonical state Hc, observation at lag k)

The witness therefore adds one historical coordinate to the currently
authorized state for evidential purposes.

It is not itself a policy representation.

It cannot control actions.

---

# 6. Witness-to-policy mapping

A supported witness authorizes the smallest permitted policy representation
containing that historical coordinate.

Frozen mapping:

    lag 1 -> H1
    lag 2 -> H2
    lag 3 -> H4
    lag 4 -> H4

Examples:

    from H0:
        lag-1 witness -> H1
        lag-2 witness -> H2
        lag-3 witness -> H4
        lag-4 witness -> H4

    from H1:
        lag-2 witness -> H2
        lag-3 witness -> H4
        lag-4 witness -> H4

Witness support is evidence for required representational capacity.

It is not policy authority until canonical authorization occurs.

---

# 7. Conditions

Every v1.3 held-out world must include at least:

    REACTIVE
    FIXED-H1
    FIXED-H2
    FIXED-H4
    ADAPTIVE-NO-VERIFIER
    FULL-PRIME-V1.2-REFERENCE
    FACTOR-WITNESS-CARRIER-COST
    FULL-PRIME-V1.3

The purpose of the two factorized conditions is to separate:

    evidence factorization

from:

    complexity repricing

so that a positive result cannot automatically be attributed to both.

---

# 8. FULL-PRIME-v1.2-REFERENCE

This condition reproduces the v1.2 adaptive logic on the fresh v1.3 worlds:

- complete-candidate prequential predictors;
- v1.2 anytime-valid evidence rule;
- v1.2 representation complexity rule;
- v1.2 smallest-supported candidate selection.

The implementation must be behaviourally equivalent to frozen v1.2 logic
except for use of the v1.3 seed sets and v1.3 provenance wrapper.

This condition is the primary mechanistic comparator.

---

# 9. FACTOR-WITNESS-CARRIER-COST

This ablation uses:

- factorized lag-witness predictors;
- v1.3 witness evidence;
- but the old v1.2 exponential carrier complexity penalty.

Thus it isolates the effect of evidence factorization while retaining the old
complexity pricing.

---

# 10. FULL-PRIME-v1.3

FULL-PRIME-v1.3 uses:

- factorized lag-witness evidence;
- anytime-valid sequential support;
- direct minimal policy-depth authorization;
- coordinate-description representation cost;
- canonical receipts;
- no candidate-memory leakage into policy state.

This is the full v1.3 mechanism.

---

# 11. Why complexity pricing changes

v1.2 used:

    C(d) = 2 ** (d + 1)

and required:

    wins - losses >
        C(candidate) - C(current)

For H0 -> H4 this imposes a cost of:

    30

The policy learner already pays for the larger H4 carrier through sparse
state visitation and slower parameter learning.

v1.3 tests whether additionally charging the verifier the full induced
tabular-carrier cardinality double-prices representational complexity.

The full v1.3 condition therefore prices the additional memory description
itself rather than the complete induced carrier.

Frozen coordinate-description cost:

    K(c,d) = d - c

Examples:

    H0 -> H1:
        1

    H0 -> H2:
        2

    H0 -> H4:
        4

    H2 -> H4:
        2

This rule is frozen before adaptive results.

---

# 12. Statistical validity

Factorization must not weaken the run-level false-support budget.

All witness evidence is:

- prequential;
- deterministic;
- paired against the current canonical predictor;
- anytime-valid;
- evaluated without native floating-point arithmetic.

The exact e-process and multiplicity accounting are frozen separately before
implementation.

---

# 13. Primary v1.3 mechanistic claim

For every held-out world i define:

    D_i =
        AULC(FULL-PRIME-v1.3, i)
        -
        AULC(FULL-PRIME-v1.2-REFERENCE, i)

The primary v1.3 upgrade claim is supported only if:

1. mean paired D_i > 0;
2. frozen deterministic paired-bootstrap lower bound > 0;
3. exact final-depth recovery is not degraded relative to the v1.2 reference;
4. mean final-window performance is not degraded;
5. all integrity checks pass.

This tests whether the new evidence architecture actually improves the parent
mechanism.

---

# 14. Fixed-H4 boundary

A separate comparison remains:

    FULL-PRIME-v1.3
        versus
    development-selected fixed representation

The fixed comparator is selected on v1.3 development worlds before adaptive
development results are inspected.

A superiority claim over that fixed comparator requires the same frozen
paired-bootstrap criterion used in v1.2.

This comparison is reported separately from the primary mechanistic claim.

---

# 15. Factorization-only ablation

Report paired performance:

    FACTOR-WITNESS-CARRIER-COST
        minus
    FULL-PRIME-v1.2-REFERENCE

This isolates the effect of factorized evidence while retaining v1.2
complexity pricing.

---

# 16. Repricing increment

Report paired performance:

    FULL-PRIME-v1.3
        minus
    FACTOR-WITNESS-CARRIER-COST

This measures the additional effect of coordinate-description pricing after
factorization.

It is an ablation diagnostic unless separately frozen as an inferential claim.

---

# 17. Structural preservation

Report for every adaptive condition:

- final policy depth;
- exact required-depth recovery;
- unnecessary d=0 repairs;
- proposal count;
- accepted repair count;
- rejected repair count;
- authorization latency;
- receipt-chain validity.

The strongest structural preservation result requires:

    FULL-PRIME-v1.3 exact final-depth recovery = 128/128

No performance gain may be described as successful exact repair if this gate
fails.

---

# 18. Deep-evidence diagnostic

For held-out d=4 worlds report:

- mean authorization latency;
- maximum authorization latency;
- evidence already available at obstruction;
- additional discordant events after obstruction.

The central mechanistic diagnostic is whether FULL-PRIME-v1.3 reduces d=4
authorization latency relative to FULL-PRIME-v1.2-REFERENCE on the same fresh
worlds.

---

# 19. Policy/verifier separation

The verifier may maintain the bounded observation history required to score
witnesses.

The policy may access only its currently authorized canonical representation.

A witness may never:

- control the policy;
- initialize unauthorized policy memory;
- alter policy Q-values;
- expose hidden depth;
- copy private verifier history into policy memory after repair.

Upon authorization, policy memory is initialized only from observations
legitimately available under the prior authorized policy state plus future
observations.

---

# 20. Receipts

All authoritative repair decisions remain:

- deterministic;
- canonical;
- provenance-bound;
- hash chained;
- replayable;
- tamper detectable;
- free of timestamps;
- free of random UUIDs;
- free of native JSON floats.

Witness identity and witness evidence must be included in authorization
receipts.

---

# 21. Development discipline

Development seeds may be used to:

- implement frozen rules;
- debug defects;
- run invariant tests;
- select the fixed comparator;
- inspect development diagnostics.

After factorized adaptive rules are frozen, poor adaptive performance may not
be used to tune:

- witness definitions;
- evidence threshold;
- multiplicity correction;
- complexity pricing;
- witness-to-policy mapping.

A substantive change requires a successor benchmark.

---

# 22. Evaluation discipline

Before seeds 3000 through 3127 are unlocked:

- contract must be frozen;
- factorized adaptive rules must be frozen;
- fixed comparator must be frozen;
- implementation must be committed;
- tests must pass;
- development diagnostic must be frozen;
- implementation hash must be frozen;
- analysis plan must be frozen;
- evaluation harness must be frozen;
- Git worktree must be clean.

---

# 23. Learned-memory boundary

v1.3 remains a controlled representation-repair experiment.

It does not yet establish superiority over recurrent learned-memory agents.

A GRU/RNN or comparable learned-memory baseline remains a required subsequent
benchmark.

---

# 24. Falsification

Scientifically valid negative outcomes include:

- factorization fails to reduce d=4 latency;
- factorized witnesses cause incorrect deep repairs;
- v1.3 loses to the v1.2 reference;
- coordinate repricing increases unnecessary repair;
- exact-depth recovery falls below the parent reference;
- fixed H4 remains superior;
- no measurable performance benefit occurs.

These results must be retained rather than tuned away.
