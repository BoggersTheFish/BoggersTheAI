# PRIME Native Cortex Counterfactual Verifier Pre-Training Baseline

State date: 2026-08-25

## Purpose

Freeze the counterfactual verifier-semantics performance of the existing first Cortex-PRIME bridge checkpoint before any verifier-semantics retraining.

Authority remains NONE.

## Checkpoint

Path:
artifacts/native_cortex/prime-bridge-v1/cortex-prime-final.pt

SHA256:
aa1119618e4668de79dce8d783a016d5699bd53df3232b0cffbada6938a59ca1

## Development curriculum

Path:
data/native_cortex/verifier_semantics/counterfactual_v1/development.jsonl

SHA256:
39e869122c1086ffcdc72d06e3dba74f4f0e228cef143c9d9bd8cb0c3cd91587

Records:
500

Matched ACCEPT/REJECT pairs:
100

## Aggregate result

Accuracy:
0.7960

Macro accuracy:
0.7960

Minimum class accuracy:
0.0000

## Per-class accuracy

UNKNOWN:
1.0000

ACCEPT:
0.0000

REJECT:
1.0000

REPAIR:
0.9800

ABSTAIN:
1.0000

## Within-channel ACCEPT/REJECT accuracy

Arithmetic:
0.5000

Structural:
0.5000

Code property:
0.5000

## Counterfactual pair result

Pair accuracy:
0.0000

Margin reversal rate:
0.0000

Mean ACCEPT margin:
-0.773904

Mean REJECT margin:
-0.766134

Mean margin flip:
-0.007770

## Pair accuracy by channel

Arithmetic:
0.0000

Structural:
0.0000

Code property:
0.0000

## Integrity diagnostics

Full prompt collisions:
0

Truncated token collisions:
0

Malformed pairs:
0

## Frozen gate status

Overall accuracy gate:
True

Macro accuracy gate:
True

Minimum-class gate:
False

ACCEPT gate:
False

REJECT gate:
True

Pair-accuracy gate:
False

Margin-reversal gate:
False

Within-channel gate:
False

Prompt-collision integrity:
True

Truncation-collision integrity:
True

Pair-integrity gate:
True

FULL VERIFIER SEMANTICS GATE:
False

## Interpretation

The existing bridge cortex exactly preserves the previously observed outcome-family shortcut under the new matched counterfactual evaluator.

It predicts no ACCEPT examples correctly.

It predicts all REJECT examples correctly.

It achieves zero matched-pair correctness.

It produces zero correct ACCEPT/REJECT margin reversals.

Both ACCEPT and REJECT members have strongly negative mean ACCEPT-minus-REJECT margins.

There are zero full-prompt collisions, zero post-truncation token collisions, and zero malformed pairs.

Therefore the failure cannot be attributed to the paired distinction disappearing from the neural observation channel.

The immediate experimental question is now cleanly separated:

Does substantially greater exposure to the old curriculum eliminate this obstruction, or does matched counterfactual training provide an advantage that exposure alone does not?
