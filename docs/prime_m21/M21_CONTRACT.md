# PRIME M21 — Persistent Adaptive Cognition

Status:

    ARCHITECTURE CONTRACT

Parent:

    Frozen PRIME M20 Universal Adaptive-State Architecture

M20 remains immutable.

M21 is not a benchmark revision.

M21 is a cognitive-system integration milestone whose purpose is to make
verified representational learning accumulate across worlds.

---

# Central objective

Build an auditable persistent adaptive cognition loop:

    experience
        ->
    representation obstruction
        ->
    proposal search
        ->
    verification
        ->
    construction
        ->
    persistent memory
        ->
    cross-world transfer
        ->
    active study
        ->
    world-model growth
        ->
    counterfactual planning
        ->
    compression / retirement
        ->
    improved future proposal search

---

# Authority invariant

No learned, recalled, generated, simulated, transferred, compressed, induced,
or counterfactual object is canonical knowledge merely because it was produced.

Proposal-producing systems include:

    persistent semantic memory;
    episodic recall;
    distributed proposal routing;
    active-study selection;
    transfer recall;
    schema induction;
    world-model hypotheses;
    counterfactual planning.

These systems MAY alter proposal order.

They MUST NOT independently authorize canonical state mutation.

Verifier-backed authority remains required.

---

# Memory classes

M21 introduces distinct memory roles.

A. Working state

    Fast prospective state used during the current interaction.

B. Episodic memory

    Immutable hash-chained records of prior worlds, constructions, studies,
    outcomes and tensions.

C. Semantic construction memory

    Persistent reusable verifier-backed constructions grouped by predictive
    quotient class.

D. World-model memory

    Explicit verifier-authorized transition structure.

E. Meta-memory

    Records which proposal sources, transfer strategies and studies have
    historically succeeded or failed.

---

# Cross-world transfer

A construction verified in one world may become a high-priority proposal in a
later world.

Transfer MUST NOT imply immediate authorization.

The lifecycle is:

    verified old construction
        ->
    portable memory representation
        ->
    transfer proposal
        ->
    new-world prospective evidence
        ->
    verifier
        ->
    reuse OR rejection

Transfer failures are themselves evidence for future routing.

---

# Distributed proposal field

M21 introduces a learned distributed routing layer.

Its role is:

    rank likely-useful constructions and proposal families.

It MAY learn from:

    verifier acceptances;
    verifier rejections;
    predictive gain;
    contexts;
    prior transfer outcomes.

It MUST NOT:

    authorize a construction;
    mutate canonical world state;
    bypass explicit construction semantics.

The intended architecture is:

    soft distributed intuition
        ->
    explicit candidate
        ->
    verifier
        ->
    canonical representation

---

# Active study

PRIME may rank possible actions or observations by how strongly they
discriminate among competing hypotheses.

Study selection is epistemic proposal machinery.

The selected study does not establish which hypothesis is true.

---

# World model

M21 introduces explicit transition hypotheses of the form:

    state + action -> next_state

Transition rules have separate proposal and authorization states.

Only verifier-authorized transition rules belong to the canonical planning
model.

---

# Planning

Planning operates over verifier-authorized world-model structure.

Unverified transition hypotheses may be used for explicitly labelled
counterfactual exploration but may not be presented as canonical prediction.

---

# Predictive quotient memory

Semantically different constructions that induce the same predictive partition
may share a semantic-memory class.

Memory reuse therefore targets useful informational structure rather than only
surface syntax.

---

# Schema induction

Repeated verified constructions may induce higher-order schema proposals.

Example:

    XOR(LAG(1), LAG(4))
    XOR(LAG(2), LAG(5))
    XOR(LAG(3), LAG(6))

may suggest a translation-invariant relation family with normalized offset:

    XOR(offsets=(0,3))

The schema itself remains a proposal until separately validated.

Long-term M21+ work may allow verified schemas to extend PRIME's construction
language.

---

# Persistence and provenance

Persistent memory artifacts must be deterministic and serializable.

Episodic records must be hash chained.

Transfer must retain source-memory identity.

Construction authority remains traceable to the originating verifier receipt
chain.

---

# Non-goals / claim boundary

M21 does not establish:

    AGI;
    human-level intelligence;
    general language understanding;
    universal representation learning;
    universal causal discovery;
    arbitrary-environment planning ability.

M21 investigates whether verifier-governed representational learning can
accumulate into reusable, increasingly efficient cognitive structure.
