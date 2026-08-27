# PRIME Canonical Agent Benchmark v1.3
## Frozen Factorized Deep-Evidence Rules

Status:

    FROZEN BEFORE v1.3 ADAPTIVE IMPLEMENTATION OR RESULTS

---

# 1. Current policy representations

Permitted canonical policy depths:

    0
    1
    2
    4

Initial depth:

    0

Policy growth is monotone.

---

# 2. Obstruction

The obstruction detector is unchanged from v1.2.

For each current canonical representation state s maintain:

    N(s,0)
    N(s,1)

An obstruction exists when:

    N(s,0) >= 8

and:

    N(s,1) >= 8

for at least one current state.

Only the current canonical policy representation participates in obstruction
detection.

---

# 3. Verifier private history

The verifier may maintain at most:

    5 binary observations

for evidential state construction.

This private queue may never control policy actions.

It resets at episode boundaries.

---

# 4. Factorized witnesses

For current canonical depth c, define one witness for every historical lag:

    k in {c+1, ..., 4}

Witness state:

    Z(c,k) =
        (Hc state, X[t-k])

Thus each witness adds exactly one omitted historical coordinate.

Examples from H0:

    Z(0,1) = (X[t], X[t-1])
    Z(0,2) = (X[t], X[t-2])
    Z(0,3) = (X[t], X[t-3])
    Z(0,4) = (X[t], X[t-4])

The witness is evidential only.

It is not an authorized policy representation.

---

# 5. Prequential predictors

Maintain:

- one predictor for current canonical state Hc;
- one predictor for every active witness Z(c,k).

Each predictor stores per-state target counts:

    count0
    count1

Prediction rule:

    predict 1 iff count1 > count0

Otherwise:

    predict 0

Therefore unseen states and ties predict 0.

Every prediction is frozen before target revelation.

Counts update only after:

- policy action;
- reward;
- target reconstruction.

No event trains itself before being scored.

---

# 6. Target reconstruction

As in v1.2:

    reward == 1:
        target = action

    reward == 0:
        target = 1 - action

Only public action/reward feedback is used.

---

# 7. Paired witness evidence

For each witness k compare:

    witness prediction

against:

    current canonical predictor

When predictions agree:

    no paired update

When they disagree:

    WIN:
        witness correct
        current wrong

    LOSS:
        current correct
        witness wrong

Maintain:

    W_k
    L_k

from the beginning of the current canonical representation epoch.

---

# 8. Anytime-valid witness e-process

For each witness:

    M_k =
        (3/2) ** W_k
        *
        (1/2) ** L_k

Equivalent exact integer comparison:

    M_k >= T

iff:

    3 ** W_k
        >=
    T * 2 ** (W_k + L_k)

No native floating-point evidence is used.

---

# 9. Multiplicity accounting

Across a monotone run, the maximum number of distinct witness streams is:

    current H0:
        lag 1, lag 2, lag 3, lag 4
        = 4

    current H1:
        lag 2, lag 3, lag 4
        = 3

    current H2:
        lag 3, lag 4
        = 2

Total maximum:

    4 + 3 + 2 = 9

The frozen per-witness threshold is:

    T = 576

For each witness, Ville's inequality bounds false threshold crossing by:

    1 / 576

Using a union bound over at most nine witness streams gives:

    9 / 576
        =
    1 / 64

Thus the run-level false-support budget remains at most:

    1 / 64

under the frozen null assumptions.

Optional stopping is permitted.

---

# 10. Witness-to-policy depth

Define:

    required_depth(1) = 1
    required_depth(2) = 2
    required_depth(3) = 4
    required_depth(4) = 4

A witness may authorize only its mapped policy representation.

---

# 11. FACTOR-WITNESS-CARRIER-COST complexity

For the factorization-only ablation retain v1.2 carrier complexity:

    C(d) = 2 ** (d + 1)

For witness k mapping current c to required depth d:

    cost =
        C(d) - C(c)

Witness support additionally requires:

    W_k - L_k > cost

This isolates evidence factorization from complexity repricing.

---

# 12. FULL-PRIME-v1.3 complexity

For FULL-PRIME-v1.3 use frozen coordinate-description cost:

    K(c,d) = d - c

Witness support additionally requires:

    W_k - L_k > K(c,d)

No development-dependent scaling factor exists.

The larger policy representation continues to pay its empirical learning cost
through ordinary state visitation and policy learning.

The verifier does not additionally charge the complete induced state-carrier
cardinality.

---

# 13. Support rule

A witness is supported only when BOTH are true:

1. anytime-valid evidence:

       3 ** W_k
           >=
       576 * 2 ** (W_k + L_k)

2. the condition-specific frozen complexity margin passes.

No alternative threshold is permitted.

---

# 14. Proposal

At the first obstruction of a canonical representation epoch:

    open all active omitted-lag witnesses

Evidence accumulated prequentially before obstruction is eligible.

Before obstruction:

    evidence may accumulate

but:

    policy representation cannot change

After obstruction, support is evaluated after every scored event.

---

# 15. Selection

If one or more witnesses are supported:

1. map every supported witness to its required policy depth;
2. choose the smallest required policy depth;
3. within equal required depth choose the smallest lag witness;
4. authorize that policy depth.

Examples:

    supported lag 2 and lag 4:
        choose H2

    supported lag 3 and lag 4:
        both map to H4
        choose lag 3 as canonical evidential witness

The selected witness identity is receipted.

---

# 16. Policy memory after authorization

Private verifier history may not be copied into policy memory.

After authorization the policy may initialize the new representation only
from state information legitimately available through the old authorized
policy representation.

New deeper history must be acquired prospectively.

This is identical in spirit to the v1.2 memory-separation rule.

---

# 17. Representation epoch reset

After an authorized representation change:

- current-representation obstruction counts reset;
- witness predictor counts reset;
- witness W/L evidence resets;
- proposal state resets.

Evidence from one canonical epoch cannot authorize a later epoch.

---

# 18. End-of-run rejection

If an obstruction opened a proposal but no witness becomes supported before
run termination:

    VERIFIER_REJECT_END_OF_RUN

is receipted.

Canonical policy representation remains unchanged.

---

# 19. FULL-PRIME-v1.2-REFERENCE

The reference condition must preserve the v1.2 mechanism:

- complete candidate-state predictors;
- candidate depths H1/H2/H4 as applicable;
- v1.2 threshold 384;
- v1.2 maximum six candidate streams;
- v1.2 complexity:

      C(d) = 2 ** (d + 1)

- v1.2 condition:

      wins - losses >
          C(candidate) - C(current)

- smallest supported candidate.

It exists solely to test the new architecture on common fresh worlds.

---

# 20. ADAPTIVE-NO-VERIFIER

Ungated adaptation remains:

    obstruction
        ->
    smallest strictly deeper permitted representation

with no verifier evidence required for authority.

---

# 21. Authorization latency

For every authorized repair record:

    obstruction_scored_event_index

    authorization_scored_event_index

Define:

    latency =
        authorization_index
        -
        obstruction_index

Immediate authorization:

    latency = 0

For the selected witness also record:

    discordant_at_obstruction

and:

    additional_discordant_after_obstruction

---

# 22. Required receipts

Every resolved factorized proposal receipt must include at least:

- benchmark version;
- condition;
- world seed;
- canonical depth before;
- candidate witness lags;
- witness-to-depth mapping;
- W/L for every witness;
- exact evidence operands;
- complexity rule identifier;
- complexity cost;
- supported witnesses;
- selected witness lag;
- selected required depth;
- authorized depth;
- canonical depth after;
- obstruction index;
- authorization index;
- latency;
- previous receipt hash;
- receipt sequence.

---

# 23. Tamper tests

The implementation must detect alteration of at least:

- witness lag;
- witness W;
- witness L;
- mapped policy depth;
- complexity rule;
- complexity cost;
- authorized depth;
- world seed;
- previous receipt hash;
- receipt deletion;
- receipt insertion;
- receipt reordering.

---

# 24. Development seeds

Adaptive development may run only:

    300 through 331

Evaluation seeds:

    3000 through 3127

remain inaccessible without the later frozen evaluation unlock.

---

# 25. Frozen-rule discipline

Development performance may not modify:

- obstruction threshold 8/8;
- witness definitions;
- witness lag set;
- witness-to-policy mapping;
- prequential prediction rule;
- e-process bet;
- threshold 576;
- multiplicity count 9;
- carrier-cost ablation rule;
- coordinate-description cost;
- selection order;
- evidence epoch reset.

A defect requiring one of these to change retires v1.3 and creates a successor.

---

# 26. Falsification

Retain negative outcomes including:

- deep witness evidence remains slow;
- factorization-only provides no benefit;
- coordinate repricing causes false repair;
- v1.3 loses exact-depth recovery;
- v1.3 loses to v1.2 reference;
- v1.3 loses to FIXED-H4;
- increased variance eliminates apparent development gains.
