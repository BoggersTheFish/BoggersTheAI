# PRIME Native Cortex Verifier Semantics / Counterfactual Bridge Contract

State date: 2026-08-25

## Purpose

Directly attack the demonstrated Cortex-PRIME verifier obstruction:

ACCEPT accuracy = 0

without weakening canonical PRIME verifiers, moving development gates, accessing held-out data, or transferring authority to the neural cortex.

## Core invariant

prediction != authority

The neural verifier head remains a predictor.

Canonical PRIME verifier output remains authoritative.

## Hypothesis H1: underexposure

The first bridge may have failed ACCEPT because only approximately 400 verifier optimizer updates occurred against a 2500-record curriculum.

## Hypothesis H2: shortcut curriculum

The first five-way curriculum may have allowed the cortex to identify broad outcome families without learning the actual ACCEPT versus REJECT distinction.

These hypotheses must be separated experimentally.

## Condition A: exposure control

Reuse the existing frozen verifier curriculum.

Provide substantially greater verifier exposure.

Do not alter its canonical labels or underlying verifier semantics.

Purpose:

Test whether additional exposure alone produces genuine ACCEPT/REJECT discrimination.

## Condition B: paired counterfactual semantics

Construct matched ACCEPT/REJECT pairs.

Within each pair keep channel, wording, entities, formatting and irrelevant information as constant as practical.

Change only the verifier-relevant fact.

Arithmetic example:

37 + 18 = 55 -> ACCEPT
37 + 18 = 56 -> REJECT

Structural example:

object_declared=True -> ACCEPT
object_declared=False -> REJECT

Code-property example:

same program
same invocation
expected=13 -> ACCEPT
expected=14 -> REJECT

Canonical typed verifiers must generate the labels.

## Development-only rule

TRAIN and DEVELOPMENT may be used.

HELDOUT remains forbidden.

M26 held-out seeds also remain untouched.

## Evaluator-before-training rule

The paired development evaluator must be implemented and frozen before running paired training.

It must measure:

1. overall five-way accuracy
2. macro class accuracy
3. minimum class accuracy
4. ACCEPT accuracy
5. REJECT accuracy
6. within-channel ACCEPT/REJECT accuracy
7. matched-pair joint correctness
8. ACCEPT-minus-REJECT margin on positive examples
9. ACCEPT-minus-REJECT margin on negative examples
10. paired margin reversal
11. prediction distribution
12. confusion matrix
13. language retention

## Matched-pair correctness

For every pair consisting of an ACCEPT member and its matched REJECT counterfactual:

pair_correct = 1 only when both predictions are correct.

Predicting REJECT for both receives zero pair credit.

Primary paired score:

PAIR_ACC = mean(pair_correct)

## Margin metric

Define:

m(x) = p(ACCEPT | x) - p(REJECT | x)

For a correct matched pair we want:

m(positive) > 0
m(negative) < 0

Define:

margin_flip = m(positive) - m(negative)

A larger positive margin_flip indicates stronger counterfactual sensitivity.

## Required channels

At minimum:

arithmetic
structural
code_property

Channel identity must not determine the label.

## Language retention

Every verifier-semantics condition must rerun the existing Native Cortex V1 development language evaluator.

Reference BPB values:

pre-bridge V1:
2.0788

first bridge:
2.0821

Existing retention ceiling:
2.1788

Do not alter the threshold after observing a new result.

## Verifier integrity

Do not alter canonical verifier behaviour to improve neural accuracy.

Do not manually relabel failed examples.

Do not manufacture ACCEPT or REJECT labels without executing the corresponding typed canonical verifier.

## Provenance

Each paired record should contain:

pair_id
pair_member
channel
premises
obligation
canonical verifier result
canonical label
counterfactual field
counterfactual value
construction metadata
record hash
pair hash
authority = NONE

## Scientific interpretation

Success establishes only development-set learning of typed pass/fail distinctions under the tested channels and curriculum.

It does not establish general reasoning, general verification, theorem proving, or epistemic authority.

Failure remains a valid result.

Do not move gates after observing results.

## Next programme after genuine verifier semantics

Only after actual ACCEPT/REJECT discrimination is demonstrated should the programme advance toward:

proposal
-> verifier result
-> obstruction
-> minimal repair
-> neural repair learning

and later:

raw language
-> typed semantic proposal
-> obligation discovery
-> verifier routing
-> verification
-> repair
-> learning
