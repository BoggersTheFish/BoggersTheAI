# TS-AI Constraint-Field Reasoning

This module is the first deterministic substrate for representing concepts as
structured constraint fields. It lives in `reasoner/ts_reasoner/constraint_fields`
and is intentionally verifier-first: no embedding lookup, random sampling, or
external LLM call is required for the core tests.

## Core Thesis

Concepts should be mapped to physical and mathematical constraint fields before
they are compared. Similarity is overlap in constraint topology, not token
closeness. An analogy is only accepted when the shared mechanisms, limits,
prediction surface, and counterexamples are explicit.

This is not a metaphor generator. A comparison can say that two systems overlap
through `accumulation`, `threshold`, or `feedback`, but it must also say where
that mapping breaks.

## Data Model

A `ConceptField` contains:

- `concept_id`, `name`, `description`
- `entities`, `forces`, `constraints`, `flows`
- `thresholds`, `attractors`, `failure_modes`
- `similar_systems`, `breakpoints`, `testable_predictions`
- `confidence`, `receipts`

Each internal item is a `FieldItem` with:

- `id`, `label`, `description`
- `polarity`, `strength`, `confidence`
- `evidence`, `notes`, `primitives`

Fields are normalized and validated. Underspecified input is marked
`underspecified` and capped at low confidence instead of being inflated into a
strong claim.

## Primitive Vocabulary

The first vocabulary is fixed and deterministic:

`gradient`, `threshold`, `feedback`, `oscillation`, `decay`, `growth`,
`compression`, `symmetry`, `phase_transition`, `local_minimum`, `attractor`,
`resonance`, `interference`, `constraint_satisfaction`, `accumulation`, `flow`,
`lock`, `collapse`, `propagation`, `resistance`.

These primitives are used as the auditable comparison surface. Labels are still
considered, but structural primitive overlap carries the main weight.

## Comparison

`compare_concept_fields(a, b)` normalizes both fields, builds deterministic
field signatures, and computes a weighted Jaccard overlap over category-aware
features:

- labels inside each category
- primitives inside each category
- global primitive tags
- category weights for forces, constraints, thresholds, failure modes, and flows

The result includes shared entities, forces, constraints, flows, thresholds,
attractors, and failure modes, plus similarity score, divergence score, overlap
explanation, breakpoint warnings, rejected matches, and a receipt.

## Analogy Verification

`verify_analogy(source, target)` wraps comparison with verifier gates. An
accepted analogy needs:

- explicit overlap mechanisms
- places where the analogy works
- places where it breaks
- a prediction or consequence surface
- a counterexample or breakpoint

Missing breakpoints prevent unbounded acceptance. Strong breakpoints reduce
confidence even when the surface overlap is real.

## Receipts

`export_receipt(result)` returns an audit payload with:

- `inputs`
- `normalized_fields`
- `matching_logic`
- `score_calculation`
- `rejected_matches`
- `final_decision`

This is the minimum receipt trail needed to check whether the system accepted an
analogy for explicit structural reasons.

## Examples

Built-in examples include `gravity`, `social_influence`, `debt`,
`technical_debt`, `learning`, and `operating_system`.

### Debt vs Technical Debt

`debt` and `technical_debt` score high because both expose accumulation,
compounding pressure, maintenance or servicing cost, repayment/refactor effort,
collapse thresholds, lock-in, and trust degradation. The analogy is bounded:
financial debt has formal legal/accounting enforcement, while technical debt is
enforced through engineering friction and delivery risk.

### Gravity vs Social Influence

`gravity` and `social_influence` share attraction, center/periphery structure,
distance decay, orbiting behavior, and central body influence. The verifier
flags major breakpoints: gravity is impersonal and mathematically invariant,
while social influence depends on agency, interpretation, culture, incentives,
and context.

### Operating System as Programmable Physical State Transition

An operating system is represented as a programmable state-transition manager
over physical compute resources. Its field includes process and kernel
entities, scheduling pressure, protection locks, permission thresholds, IO
flows, deadlock thresholds, and resource starvation collapse. The breakpoint is
that OS transitions are designed and discrete rather than continuous natural
fields.

## CLI

Run from the repository root:

```bash
python3 -m reasoner.ts_reasoner.field_reasoning_cli compare debt technical_debt
python3 -m reasoner.ts_reasoner.field_reasoning_cli compare gravity social_influence
python3 -m reasoner.ts_reasoner.field_reasoning_cli verify-analogy gravity social_influence
python3 -m reasoner.ts_reasoner.field_reasoning_cli verify-analogy debt technical_debt --receipt
```

The CLI prints JSON so the score and receipt trail can be inspected directly.
