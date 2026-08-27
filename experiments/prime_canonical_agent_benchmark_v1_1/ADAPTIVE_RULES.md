# PRIME Canonical Agent Benchmark v1.1
## Frozen Adaptive Repair Rules

Status: FROZEN BEFORE ADAPTIVE IMPLEMENTATION OR ADAPTIVE DEVELOPMENT RESULTS

These rules specify the hypothesis-bearing adaptive mechanism.

They may not be tuned in response to development or evaluation performance.
An implementation defect may be corrected, but any substantive rule change
requires a new benchmark version and explicit lineage.

---

# 1. Initial representation

The adaptive conditions begin at representation depth:

    H0

Permitted depths are:

    H0, H1, H2, H4

where Hd contains the current binary observation and the preceding d binary
observations.

Representation growth is monotone.

---

# 2. Current-representation evidence

The policy may retain only the state exposed by its currently authorized
representation.

For each scored decision it may retain:

- current authorized representation state;
- chosen binary action;
- received binary reward;
- inferred correct binary action.

Because the action space is binary and reward is exactly 1 for the correct
action and 0 otherwise, the historical correct action is inferable as:

    target = action       if reward == 1
    target = 1 - action   if reward == 0

No latent environment state or hidden dependency depth is exposed.

---

# 3. Obstruction definition

A representation obstruction exists when one currently represented state has
repeated, contradictory verified target actions.

For each current representation state s, count:

    N(s, 0)
    N(s, 1)

An obstruction is declared when there exists s such that:

    N(s, 0) >= 8
    and
    N(s, 1) >= 8

Only evidence gathered since the most recent authorized representation change
is used for this obstruction test.

This is a structural aliasing test.

It does not inspect reward averages from frozen evaluation worlds and does not
know the hidden environment depth.

---

# 4. Proposal rule

When an obstruction is first declared, the proposal mechanism nominates every
strictly deeper permitted representation.

Examples:

    H0 -> {H1, H2, H4}
    H1 -> {H2, H4}
    H2 -> {H4}

The proposal mechanism:

- cannot authorize a repair;
- cannot access hidden environment depth;
- cannot rank candidates using frozen evaluation outcomes.

Candidate order is always increasing representation depth.

---

# 5. Prospective shadow probe

FULL-PRIME does not retain deeper historical representations before a proposal.

After a proposal, the independent verifier opens a prospective shadow probe
beginning at the next complete episode.

Probe duration:

    4 complete episodes

Each candidate representation is instantiated independently for the probe.

Candidate shadow representations receive the same newly arriving public binary
observations as the policy, but:

- they do not choose actions;
- they cannot influence policy;
- they cannot mutate canonical representation state;
- they cannot access hidden depth.

The currently authorized representation is shadow-scored over the same probe
events.

The probe therefore compares representations on common prospective evidence
without granting candidate representations policy authority.

---

# 6. Probe target reconstruction

For every scored probe event, the verifier records:

- state under current representation;
- state under each candidate representation;
- inferred historical correct binary action.

The correct action is inferred only from the policy's public action/reward
feedback using the binary complement rule specified above.

---

# 7. Train/validation split

Probe events are indexed from zero in deterministic observation order.

Training events:

    even indices

Validation events:

    odd indices

No random split is used.

Each representation learns a deterministic state-to-target predictor on the
training half.

For each represented state:

- predict target 0 when count(0) > count(1);
- predict target 1 when count(1) > count(0);
- ties predict 0.

Previously unseen validation states also predict 0.

This predictor is verifier-only and never controls the benchmark agent.

---

# 8. Paired candidate comparison

For every validation event compare:

    prediction(current)
    prediction(candidate)
    true inferred target

Count:

    wins   = candidate correct, current wrong
    losses = current correct, candidate wrong

Events on which both agree in correctness are not discordant.

Let:

    m = wins + losses

A candidate must satisfy BOTH the statistical evidence rule and the explicit
representation complexity rule.

---

# 9. Statistical evidence rule

Use an exact one-sided paired sign test.

Under the null hypothesis that neither representation is better on discordant
events:

    W ~ Binomial(m, 1/2)

The exact upper-tail probability is represented without floating point as:

    numerator =
        sum(comb(m, k) for k in range(wins, m + 1))

    denominator =
        2 ** m

The frozen significance requirement is:

    64 * numerator <= denominator

equivalent to:

    p <= 1/64

No asymptotic approximation or floating-point p-value is used.

If m == 0, the candidate fails.

---

# 10. Explicit representation complexity cost

The representation complexity of Hd is its maximum number of binary states:

    C(d) = 2 ** (d + 1)

For current depth c and candidate depth d, define:

    complexity_cost = C(d) - C(c)

The candidate must additionally satisfy:

    wins - losses > complexity_cost

Thus a larger representation must supply correspondingly stronger paired
decision evidence.

This cost is frozen before observing adaptive results.

---

# 11. Authorization rule

FULL-PRIME independently evaluates every proposed candidate.

A candidate is verifier-supported only when:

1. its exact paired sign test passes;
2. its net paired advantage exceeds its explicit complexity cost.

If no candidate passes:

    reject proposal
    canonical depth unchanged

If one or more candidates pass:

    authorize the smallest passing depth

At most one representation repair is authorized per repair event.

After authorization:

- canonical representation depth changes;
- policy continues learning under the new representation;
- obstruction evidence is cleared;
- unused candidate shadows are discarded;
- a canonical hash-chained repair receipt is created.

Rejected proposals have zero canonical representation effect.

---

# 12. ADAPTIVE-NO-VERIFIER ablation

This condition uses the identical obstruction detector and proposal candidate
set.

It does NOT run the independent verifier authorization rule.

On obstruction it immediately accepts:

    the smallest proposed deeper representation

Thus it climbs the representation ladder one obstruction at a time.

This deliberately tests whether independent verifier selection provides value
beyond ungated adaptive growth.

Every ungated repair remains recorded.

---

# 13. VERIFIER-NO-REPAIR ablation

This condition uses:

- the identical obstruction detector;
- the identical proposal rule;
- the identical prospective shadow probe;
- the identical verifier scoring rule.

However representation mutation is disabled.

Even a verifier-supported candidate produces:

    canonical representation effect = zero

The policy therefore remains at H0.

Verifier decisions remain recorded.

---

# 14. Repair limits

Maximum accepted representation repairs per run:

    3

No representation may shrink in v1.1.

No repair may exceed H4.

---

# 15. Receipt chain

Every proposal resolution generates a deterministic canonical receipt containing
at least:

- benchmark version;
- condition;
- world seed;
- receipt sequence;
- previous receipt hash;
- obstruction episode;
- current representation depth;
- candidate depths;
- verifier evidence summary;
- complexity costs;
- supported candidates;
- authorized depth or null;
- canonical depth before;
- canonical depth after.

Canonical receipt JSON:

- sorted keys;
- compact separators;
- UTF-8;
- trailing newline;
- no native floats;
- no timestamps;
- no UUIDs.

Receipt hash:

    SHA-256(canonical receipt bytes)

Each receipt commits to the previous receipt hash.

Tampering must cause chain verification failure.

---

# 16. Development restriction

Adaptive development runs may use only seeds:

    0 through 31 inclusive

The rules in this file may NOT be changed because adaptive development
performance is poor.

Development may be used only to:

- find implementation bugs;
- verify invariants;
- verify determinism;
- verify that the implementation matches these frozen rules.

---

# 17. Evaluation restriction

Seeds:

    1000 through 1127 inclusive

remain untouched until:

- adaptive implementation is complete;
- adaptive tests pass;
- receipt tamper tests pass;
- development invariant tests pass;
- implementation source is committed;
- the worktree is clean;
- the implementation manifest is frozen.

