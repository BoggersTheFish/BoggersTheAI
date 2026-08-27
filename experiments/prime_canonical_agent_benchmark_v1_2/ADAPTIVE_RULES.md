# PRIME Canonical Agent Benchmark v1.2
## Frozen Sequential Adaptive Repair Rules

Status: FROZEN BEFORE v1.2 ADAPTIVE IMPLEMENTATION OR ADAPTIVE RESULTS

These rules define the hypothesis-bearing v1.2 adaptive mechanism.

They may not be tuned in response to development or evaluation performance.

A substantive rule change requires a new explicitly linked benchmark version.

---

# 1. Purpose

v1.1 recovered the exact required representation depth in all 128 held-out
worlds but suffered a substantial online-learning penalty from its fixed
four-episode prospective verifier probe.

v1.2 tests whether the verifier can retain:

- independent authority;
- precise representation selection;
- explicit complexity cost;
- deterministic receipts;
- fail-closed canonical mutation;

while reducing authorization latency through:

- passive verifier evidence accumulated during normal interaction;
- prequential prediction;
- an anytime-valid sequential evidence process;
- immediate stopping once frozen support requirements are satisfied.

---

# 2. Permitted policy representations

Permitted representation depths are:

    H0
    H1
    H2
    H4

Hd consists of:

    current observation
    plus the previous d observations

The policy begins each run at:

    H0

Representation growth is monotone.

Maximum accepted repairs:

    3

No shrinking is permitted in v1.2.

---

# 3. Policy/verifier separation

The policy may act only through the currently authorized canonical
representation.

The verifier is a separate evidence subsystem.

The verifier may passively maintain bounded information required to construct
candidate representations.

That information:

- may not influence policy action selection;
- may not alter policy Q-values;
- may not change canonical representation;
- may not expose hidden dependency depth;
- may not inspect future observations;
- may not access evaluation labels;
- may not authorize its own proposal.

Candidate evidence is epistemic evidence only.

It is not policy authority.

---

# 4. Passive observation memory

The verifier may retain a rolling queue containing at most:

    5 binary observations

This is sufficient to construct H0, H1, H2 and H4 states.

The queue is private to the verifier.

The policy does not receive this queue unless a corresponding representation
has been canonically authorized.

Representation histories reset at episode boundaries exactly as in the frozen
environment apparatus.

Verifier predictive counts may persist across episodes within one canonical
representation epoch.

---

# 5. Canonical representation epoch

A representation epoch begins:

- at the start of the run; or
- immediately after an authorized representation repair.

Each epoch has one fixed current canonical depth.

At the beginning of a new epoch the verifier clears:

- obstruction counts;
- candidate predictor counts;
- current-representation verifier predictor counts;
- candidate evidence-process state;
- open proposal state.

Evidence from a previous canonical representation epoch may not authorize a
later repair.

---

# 6. Target reconstruction

The action space and reward are binary.

After each scored action, the verifier may infer the correct historical target:

    target = action
        when reward == 1

    target = 1 - action
        when reward == 0

This uses only public action/reward feedback.

The target must not be available before the action and reward occur.

---

# 7. Prequential verifier predictors

The verifier maintains one deterministic predictor for:

- the current canonical representation;
- every strictly deeper permitted candidate representation.

For every representation state, predictor evidence is stored as:

    count(target = 0)
    count(target = 1)

Prediction occurs BEFORE the target for the current event is revealed.

Prediction rule:

    predict 0 if count0 >= count1
    predict 1 if count1 > count0

Therefore:

- unseen states predict 0;
- exact ties predict 0.

Only after:

1. all verifier predictions are frozen for that event;
2. policy action is chosen;
3. reward is received;
4. target is reconstructed;

may predictor counts be updated.

This makes the verifier comparison prequential.

No event may train a predictor before being scored by that predictor.

---

# 8. Current-representation obstruction

Obstruction detection remains structural.

For every current canonical representation state s, maintain verified target
counts since the current representation epoch began:

    N(s, 0)
    N(s, 1)

An obstruction exists when at least one current state satisfies:

    N(s, 0) >= 8

and:

    N(s, 1) >= 8

The obstruction test uses only the current canonical representation.

Candidate representations do not cause obstruction declaration.

---

# 9. Proposal rule

At the first obstruction of a canonical representation epoch, propose every
strictly deeper permitted representation.

Examples:

    H0 -> {H1, H2, H4}

    H1 -> {H2, H4}

    H2 -> {H4}

Candidate order is increasing representation depth.

There is at most one proposal event per canonical representation epoch.

The proposal remains open until:

- a candidate is authorized;
- the run terminates without support; or
- mutation is deliberately disabled by the relevant ablation.

Proposal is not authority.

---

# 10. Paired prequential evidence

For every scored event, before target revelation, the verifier obtains:

    prediction_current

and:

    prediction_candidate(d)

for each strictly deeper candidate d.

After target revelation, candidate d receives a paired evidence update only
when:

    prediction_current != prediction_candidate(d)

Because the target is binary, exactly one prediction is correct on such an
event.

Define:

    WIN:
        candidate correct
        current wrong

    LOSS:
        current correct
        candidate wrong

When both representations predict the same target:

    no paired evidence update

Each candidate maintains cumulative counts:

    W_d
    L_d

from the beginning of the current canonical representation epoch.

---

# 11. Anytime-valid evidence process

For each candidate d define:

    M_d =
        (3 / 2) ** W_d
        *
        (1 / 2) ** L_d

Equivalently:

    M_d =
        3 ** W_d
        /
        2 ** (W_d + L_d)

No floating-point representation of M_d is required.

Under the null that the candidate is not conditionally more likely than the
current representation to win a discordant prediction event, the fixed
one-half betting process is a nonnegative test supermartingale.

Therefore Ville's inequality permits inspection after every event and stopping
when the threshold is crossed.

---

# 12. Familywise sequential threshold

Across a monotone run over:

    H0, H1, H2, H4

the maximum number of distinct deeper-candidate evidence streams is:

    3 + 2 + 1 = 6

Each individual candidate uses the frozen threshold:

    M_d >= 384

which is evaluated exactly as:

    3 ** W_d
        >=
    384 * 2 ** (W_d + L_d)

For one candidate, Ville's inequality bounds false threshold crossing by:

    1 / 384

Using a union bound across the maximum six candidate streams yields a total
run-level bound of at most:

    6 / 384
        =
    1 / 64

No p-value approximation is used.

No threshold changes with sample size.

No repeated-testing correction is added later.

The anytime-valid threshold is frozen before adaptive results.

---

# 13. Representation complexity

Representation complexity remains:

    C(d) = 2 ** (d + 1)

For current depth c and candidate depth d:

    complexity_cost(c, d)
        =
    C(d) - C(c)

Candidate d must satisfy:

    W_d - L_d
        >
    complexity_cost(c, d)

This is required in addition to the anytime-valid evidence threshold.

Examples from H0:

    H1 cost:
        4 - 2 = 2

    H2 cost:
        8 - 2 = 6

    H4 cost:
        32 - 2 = 30

A statistically supported candidate that does not pay its frozen complexity
cost is not authorizable.

---

# 14. Candidate support

A candidate is verifier-supported only when BOTH are true:

1. anytime-valid evidence:

       3 ** W_d
           >=
       384 * 2 ** (W_d + L_d)

2. representation complexity:

       W_d - L_d
           >
       C(d) - C(current)

Supported status is monotone only with respect to the current evidence state;
future losses may reduce M before authorization.

However authorization is evaluated immediately after each complete scored
event.

Once authorization occurs, the canonical epoch ends and no future event may
retroactively alter that decision.

---

# 15. Sequential authorization

Before obstruction:

    candidate evidence accumulates passively

but:

    canonical representation cannot change

At the event that first creates an obstruction:

1. proposal candidate set is opened;
2. candidate support is evaluated using all valid prequential evidence
   accumulated during the current canonical representation epoch.

If one or more candidates already satisfy the frozen support rule:

    authorize immediately after the obstruction event

and before the next policy action.

If no candidate is supported:

    keep the proposal open

and after every subsequent scored event:

1. produce predictions before target;
2. receive target;
3. update paired evidence;
4. update predictor counts;
5. evaluate support.

The first time support exists:

    authorize the smallest supported candidate depth

No fixed probe duration is imposed.

---

# 16. Authorization latency

For every proposal record:

    obstruction_scored_event_index

and:

    authorization_scored_event_index

Define additional authorization latency:

    authorization_scored_event_index
        -
    obstruction_scored_event_index

Therefore immediate authorization has latency:

    0

Also report:

    paired discordant events already accumulated at obstruction

and:

    additional paired discordant events after obstruction

for the ultimately authorized candidate.

This directly measures how much new evidence the verifier required after the
representation failure became detectable.

---

# 17. Authorization effect

When FULL-PRIME-V1.2 authorizes candidate depth d:

- canonical policy representation becomes Hd;
- the mutation becomes effective before the next policy action;
- policy representation history begins under the newly authorized depth;
- canonical epoch evidence is closed;
- a deterministic authorization receipt is appended;
- a new representation epoch begins.

Candidate-side passive history from the previous epoch may not become hidden
policy memory.

At an episode boundary, normal representation reset applies.

If authorization occurs mid-episode, the newly authorized policy
representation may be initialized only from observations legitimately present
in the current authorized policy state plus observations arriving after
authorization.

The verifier's private deeper rolling queue may NOT be copied into policy
memory.

This prevents verifier evidence storage from secretly becoming policy memory.

---

# 18. End-of-run unresolved proposal

If a proposal remains open when the final scored event of the run ends and no
candidate satisfies the frozen rule:

    resolution = VERIFIER_REJECT_END_OF_RUN

Canonical representation remains unchanged.

A deterministic rejection receipt is appended.

The negative evidence is retained.

---

# 19. FULL-PRIME-V1.2

FULL-PRIME-V1.2 uses:

- structural obstruction detection;
- bounded passive candidate evidence;
- prequential prediction;
- anytime-valid paired evidence;
- explicit complexity cost;
- smallest-supported-candidate selection;
- explicit canonical authorization;
- hash-chained receipts.

Only an authorized candidate changes policy representation.

---

# 20. ADAPTIVE-NO-VERIFIER

The ungated adaptive condition uses the same:

- current representation;
- obstruction detector;
- proposal candidate set.

It does not use verifier support for authority.

At obstruction it immediately authorizes:

    the smallest strictly deeper proposed representation

Thus:

    H0 -> H1

before:

    H1 -> H2

before:

    H2 -> H4

when later obstructions occur.

This condition does not receive the verifier's passive deeper memory as policy
input.

Its repair decisions remain receipted.

---

# 21. VERIFIER-NO-REPAIR

VERIFIER-NO-REPAIR uses the identical:

- current-representation obstruction rule;
- passive verifier evidence;
- prequential predictors;
- sequential e-process;
- complexity rule;
- proposal set;
- smallest-supported selection.

However canonical representation mutation is disabled.

When a candidate becomes supported:

    record verifier support

but:

    canonical policy depth remains unchanged

The first supported resolution for the epoch is receipted.

The same current depth is not repeatedly reproposed after that resolution.

---

# 22. No hidden-depth access

None of the following may access the environment's hidden dependency depth:

- policy;
- proposal mechanism;
- verifier predictor;
- sequential evidence process;
- authorization logic.

Hidden depth may be added to reports only after a run for diagnostic grouping.

---

# 23. Determinism

All adaptive decisions must be deterministic.

No native JSON floats are permitted in canonical results.

No wall-clock timestamps are permitted.

No random UUIDs are permitted.

No scheduler-dependent ordering is permitted.

Identical:

    source
    configuration
    condition
    world seed

must yield byte-identical canonical evidence.

---

# 24. Receipt requirements

Every resolved proposal receipt contains at least:

- benchmark version;
- condition;
- world seed;
- sequence number;
- previous receipt hash;
- canonical depth before;
- obstruction episode;
- obstruction scored-event index;
- candidate depths;
- W and L for every candidate at resolution;
- integer evidence-threshold operands;
- complexity costs;
- supported candidate depths;
- selected verifier depth or null;
- authorized depth or null;
- canonical depth after;
- authorization latency;
- resolution type.

Receipts are:

- canonical JSON;
- sorted keys;
- compact separators;
- UTF-8;
- newline terminated;
- SHA-256 hash chained.

Tampering must fail closed.

---

# 25. Evidence-process tamper tests

The implementation test suite must reject or detect at least:

- changed W count;
- changed L count;
- changed candidate depth;
- changed complexity cost;
- changed authorization depth;
- changed previous receipt hash;
- changed world seed;
- receipt deletion;
- receipt insertion;
- receipt reordering.

---

# 26. Development seeds

v1.2 adaptive development may use only:

    100 through 131 inclusive

No adaptive-development call may run:

    2000 through 2127 inclusive

without the separately frozen evaluation unlock.

---

# 27. Frozen-rule discipline

The following may not be modified because development results are poor:

- obstruction threshold 8/8;
- candidate set;
- prequential predictor;
- prediction tie rule;
- one-half e-process bet;
- threshold 384;
- run-level familywise accounting;
- complexity definition;
- complexity inequality;
- smallest-supported rule;
- passive-memory bound;
- evidence reset at representation change.

If these prove defective rather than merely unsuccessful, v1.2 is retired and
a successor version is created.

---

# 28. Falsification

A scientifically valid negative v1.2 outcome includes:

- slower AULC than FIXED-H4;
- slower AULC than ungated adaptation;
- degraded exact-depth recovery;
- false unnecessary repairs;
- excessive sequential waiting;
- no measurable benefit from passive evidence;
- verifier support that arrives too late to matter.

These outcomes must be retained rather than tuned away.
