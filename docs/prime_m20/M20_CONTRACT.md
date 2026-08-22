# PRIME M20
## Adaptive Construction Engine

Status:

    ARCHITECTURAL CONTRACT

Parent canonical checkpoint:

    PRIME canonical agent benchmark v1.3 final commit:
        84fce73

The v1.3 benchmark remains immutable.

M20 is not benchmark v1.4.

M20 is a canonical PRIME architecture milestone.

---

# 1. Objective

Replace fixed-menu representation repair with verifier-governed
representation construction.

Previous benchmark representation family:

    H0
    H1
    H2
    H4

M20 representation:

    R = {phi_1, phi_2, ..., phi_m}

where each phi_i is a typed, content-addressed construction over observable
history or previously authorized constructions.

The system must be able to discover WHAT information or relation is missing,
not merely how many raw historical observations to retain.

---

# 2. Authority boundary

M20 preserves canonical PRIME sovereignty:

    proposal != proof
    score != proof
    confidence != proof
    learned latent state != proof
    language != proof

Only an independent verifier authorization may cause a proposed construction
to become canonical policy state.

Canonical graph mutation remains downstream of TSKernel / TSIR authority.

---

# 3. Representation algebra — M20.0

Primitive construction:

    LAG(k)

meaning:

    X[t-k]

for:

    1 <= k <= 8

Initial binary relational operators:

    XOR(a,b)
    EQ(a,b)
    AND(a,b)
    OR(a,b)

Initial M20 grammar therefore includes examples such as:

    LAG(4)

    XOR(
        LAG(1),
        LAG(4)
    )

    EQ(
        LAG(2),
        LAG(5)
    )

The initial implementation is intentionally bounded.

Higher-order composition over previously verified constructions is part of
the M20 programme but is not silently enabled before explicit tests exist.

---

# 4. Canonical construction identity

Every construction has a deterministic semantic identity.

Construction identity is derived from:

- semantics version;
- normalized typed expression.

Human-readable labels do not define identity.

Proposal source does not define semantic identity.

Equivalent normalized expressions must receive identical IDs.

---

# 5. Candidate generation

Candidate generation is proposal-only.

Default bounded grammar:

    maximum raw lag:
        8

    primitive lag constructions:
        8

    pairwise operators:
        XOR
        EQ
        AND
        OR

Candidate expressions are normalized and deduplicated.

Default maximum simultaneous candidate streams:

    128

Candidate generation cannot mutate policy state.

---

# 6. Description complexity

M20 uses structural description cost rather than induced tabular carrier size.

For a lag reference:

    K(LAG(k))
        =
    2 + bit_length(k)

For a binary construction:

    K(OP(a,b))
        =
    1 + K(a) + K(b)

This is a bounded MDL-like structural price.

It is not a claim that this is the unique correct universal coding scheme.

It is frozen for the first M20 construction experiments.

---

# 7. Prequential verification

For each current canonical policy state maintain a deterministic binary
majority predictor.

For each candidate construction q maintain a candidate predictor on:

    canonical_state + q(history)

Predictions occur BEFORE target revelation.

After target revelation:

    candidate correct, canonical wrong
        ->
    WIN

    canonical correct, candidate wrong
        ->
    LOSS

    predictions agree
        ->
    no paired evidence update

Evidence accumulated by candidate predictors cannot control policy actions.

---

# 8. Anytime-valid evidence

For candidate q:

    M_q
        =
    (3/2)^W_q (1/2)^L_q

Equivalent exact integer form:

    3^W_q
        >=
    T * 2^(W_q + L_q)

No floating-point evidence is authoritative.

---

# 9. Multiplicity budget

For N active candidate streams:

    T = 64 * N

Then each candidate has threshold-crossing budget:

    <= 1 / (64 N)

and a union bound over N streams gives run-level budget:

    <= 1/64

under the frozen null assumptions.

N is fixed for a representation epoch.

---

# 10. Complexity gate

Statistical support is insufficient by itself.

Candidate q must additionally satisfy:

    W_q - L_q > K(q)

Thus authorization requires BOTH:

1. anytime-valid statistical support;
2. structural complexity payment.

---

# 11. Obstruction

The initial M20 obstruction gate preserves the canonical benchmark rule.

For current canonical state s maintain:

    N(s,0)
    N(s,1)

An obstruction exists if:

    N(s,0) >= 8

and:

    N(s,1) >= 8

Evidence may accumulate before obstruction.

Authorization may not occur before obstruction.

---

# 12. Candidate selection

Among supported candidates select deterministically by:

1. smallest description cost K;
2. smallest required raw-history horizon;
3. canonical construction ID.

No reward-dependent post-hoc selection rule is permitted.

---

# 13. Policy/verifier memory separation

This is mandatory.

The verifier may maintain private history for candidate evaluation.

Policy state may use only authorized constructions.

When construction q is authorized:

    verifier history MUST NOT be copied into policy memory.

The newly authorized construction receives an EMPTY prospective policy buffer.

Its historical inputs become available only from observations occurring after
authorization.

Thus no construction gains retroactive policy knowledge.

---

# 14. Canonical construction lifecycle

Construction states:

    PROPOSED
    AUTHORIZED
    RETIRED

Future M20 extensions may add:

    QUARANTINED
    SUPERSEDED

Only verifier receipts may transition canonical status.

Required lifecycle operations:

    propose
    authorize
    retire
    restore

Retirement and restoration must remain receipt-backed.

---

# 15. Canonical representation state

Canonical policy state is:

    (
        current_observation,
        phi_1(policy_history_1),
        phi_2(policy_history_2),
        ...
    )

where phi_i are AUTHORIZED constructions only.

Proposal candidates never appear in policy state.

---

# 16. Receipt discipline

Every authorization receipt must record at least:

- construction ID;
- expression;
- evidence wins;
- evidence losses;
- statistical operands;
- threshold;
- structural cost;
- obstruction index;
- authorization index;
- parent receipt hash;
- sequence;
- resulting active construction set.

Receipts are:

- deterministic;
- canonical;
- hash chained;
- replayable;
- tamper detectable;
- timestamp free in scientific output.

---

# 17. Active study selection

M20 may rank unresolved candidates by expected informational usefulness.

Study selection is proposal-only.

It may decide:

    what evidence would be useful to seek

It may NOT decide:

    what is true

or:

    what becomes canonical

Verifier sovereignty remains unchanged.

---

# 18. Distributed / learned proposal field

Later M20 phases may introduce:

- soft structural embeddings;
- learned candidate ranking;
- recurrent proposal state;
- tension-field credit assignment;
- contextual routing.

These systems may accelerate proposal generation.

They may never authorize canonical construction.

The learned substrate is therefore:

    proposer

not:

    epistemic authority

---

# 19. Higher-order relational growth

Later M20 phases may permit expressions over verified constructions:

    XOR(phi_a, phi_b)

    relation(phi_a, phi_b)

    temporal(phi_a, lag_k)

    quotient(phi_a, phi_b)

This is how M20 reconnects canonical agent work with PRIME higher-order
relational geometry.

Such growth must be typed and bounded.

---

# 20. Predictive quotient integration

A set of histories may be quotiented when verifier evidence supports equal
relevant predictive behaviour under the task interface.

This reconnects M20 with TSASA-style adaptive state abstraction.

Construction adds distinctions.

Quotienting removes distinctions.

Together they form:

    representation growth
        +
    representation compression

---

# 21. Memory classes

M20 distinguishes:

A. verifier-private sensory/evidence memory

B. canonical working representation

C. episodic evidence ledger

D. persistent verified construction library

No information moves from A into B without verifier authorization.

Persistent D-memory does not automatically become authoritative in a new
environment.

Transfer still requires applicable evidence.

---

# 22. Repair / retirement / restoration

M20 representation lifecycle is:

    obstruction
        ->
    proposal
        ->
    verification
        ->
    authorization
        ->
    use
        ->
    continuing audit
        ->
    retain / repair / retire

A retired construction may later be restored only through a new receipt-backed
authorization.

---

# 23. Initial scientific targets

M20 must eventually handle task families including:

- single-lag dependency;
- multiple relevant lags;
- XOR / parity dependency;
- equality relations;
- switching relevant features;
- irrelevant distractor history;
- compositional hidden state;
- partial transfer across worlds.

A fixed H-depth menu is not sufficient for these tasks.

---

# 24. Recurrent comparison

A strong recurrent learned-memory comparator is mandatory before claims about
superiority over learned latent state.

The recurrent comparator must not be intentionally crippled.

Development-only architecture/hyperparameter selection must be frozen before
held-out comparison.

---

# 25. Falsification

Scientifically valid failures include:

- construction grammar fails to find useful features;
- multiplicity burden becomes too large;
- composition causes sample inefficiency;
- MDL pricing is poorly calibrated;
- recurrent memory dominates PRIME;
- transfer constructions fail to generalize;
- active study selection provides no advantage;
- learned proposal field provides no benefit;
- representation growth explodes combinatorially.

Such outcomes must be retained, not tuned away.

---

# 26. Claim boundary

M20 is an adaptive representation-construction architecture.

Successful controlled benchmarks would not by themselves establish:

- AGI;
- human-level intelligence;
- universal reasoning;
- universal POMDP superiority;
- general world modelling;
- safe autonomous self-improvement.

Claims remain tied to frozen evidence.
