# PRIME Native Cortex Counterfactual Verifier Semantics Evaluation Protocol

State date: 2026-08-25

## Purpose

Measure whether the Native Cortex learns actual typed ACCEPT versus REJECT distinctions rather than broad verifier outcome-family shortcuts.

This protocol is frozen before counterfactual training.

## Authority

The Native Cortex has authority NONE.

Canonical PRIME verifier outputs determine curriculum labels.

Neural verifier predictions never authorize canonical mutation.

## Curriculum design

Training remains five-way balanced:

UNKNOWN 500
ACCEPT 500
REJECT 500
REPAIR 500
ABSTAIN 500

Total:
2500 records

Development remains five-way balanced:

UNKNOWN 100
ACCEPT 100
REJECT 100
REPAIR 100
ABSTAIN 100

Total:
500 records

UNKNOWN, REPAIR and ABSTAIN controls are inherited from the frozen v1 canonical verifier curriculum.

ACCEPT and REJECT are replaced by exactly matched counterfactual pairs generated using canonical typed verifiers.

The total dataset size and five-way label balance therefore remain identical to the original bridge curriculum.

## Paired channels

Counterfactual ACCEPT/REJECT pairs are distributed across:

arithmetic
structural
code_property

The pair members use the same verifier channel.

Only the verifier-relevant fact is changed.

## Primary paired metric

For pair i:

PAIR_CORRECT_i = 1 only when:

positive member is predicted ACCEPT

and

negative member is predicted REJECT.

PAIR_ACC is the mean over all matched pairs.

A model predicting REJECT for both pair members receives zero paired credit.

## Margin metric

Define:

m(x) = p(ACCEPT | x) - p(REJECT | x)

For a correctly oriented pair:

m(positive) > 0

and

m(negative) < 0

The pair margin flip is:

m(positive) - m(negative)

The evaluator reports both mean margin flip and the proportion of pairs with correct sign reversal.

## Tokenization collision guard

The evaluator must compare paired prompts after the exact tokenizer and max-length truncation used for evaluation.

If ACCEPT and REJECT pair members become identical after truncation, the protocol is invalid for that pair.

The frozen gate requires:

full prompt collisions = 0

truncated token collisions = 0

malformed pairs = 0

## Five-way gates retained from the first bridge

overall accuracy > 0.60

macro class accuracy > 0.60

minimum class accuracy > 0.35

## New verifier-semantics gates

ACCEPT accuracy > 0.60

REJECT accuracy > 0.60

PAIR_ACC > 0.50

margin reversal rate > 0.50

Within-channel ACCEPT/REJECT accuracy must exceed 0.60 separately for:

arithmetic
structural
code_property

## Full verifier-semantics gate

The verifier-semantics gate passes only if every frozen verifier gate and every collision/integrity gate passes simultaneously.

The threshold must not be altered after observing development results.

## Language retention

Verifier-semantics success does not supersede language retention.

Every trained condition must also be evaluated using the existing Native Cortex V1 development language evaluator.

Reference:

pre-bridge V1 BPB = 2.0788

first bridge BPB = 2.0821

Frozen language-retention ceiling:

BPB <= 2.1788

A model that passes verifier semantics while exceeding the language-retention ceiling does not pass the complete programme.

## Experimental comparison

Condition A:

existing frozen verifier curriculum with substantially increased verifier exposure

Condition B:

counterfactual paired curriculum with comparable verifier exposure

The purpose is to distinguish:

underexposure

from

shortcut-friendly curriculum structure.

## Held-out discipline

The Native Cortex held-out split remains forbidden.

Frozen held-out SHA256:

509907b29546ecee73f464f44dd53a6a809b3b80a5e1d3f27c25846ac083ae8c

M26 held-out seeds also remain forbidden.

No held-out result is permitted while curriculum, training schedule, evaluator or architecture is under development.

## Scientific interpretation

Passing this development protocol establishes only that the tested Native Cortex learned development-set typed pass/fail distinctions under the tested channels.

It does not establish general verification, theorem proving, general reasoning or epistemic authority.
