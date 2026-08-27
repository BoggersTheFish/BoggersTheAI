# PRIME Native Cortex Verifier Semantics A/B Development Result

State date: 2026-08-27

## Status

The frozen A/B development experiment is complete.

Neither condition passes the full verifier-semantics gate.

Condition B nevertheless produces a substantial and strongly channel-specific counterfactual learning effect relative to Condition A.

Authority remains NONE.

## Common starting checkpoint

SHA256:

aa1119618e4668de79dce8d783a016d5699bd53df3232b0cffbada6938a59ca1

Both conditions independently started from this checkpoint.

## Condition A

Name:
exposure_control

Final checkpoint SHA256:
73d40bb229a1ac738e5148e67b171f7f8f8f4c6338b2454bcc0186e2a41c4df0

Unique verifier records presented:
2500 / 2500

## Condition B

Name:
counterfactual_paired

Final checkpoint SHA256:
440b668de1c310e6a7eded47a68da7b8f6977f4b0f36abc1fc22e205d3939e74

Unique verifier records presented:
2500 / 2500

## Aggregate comparison

Condition A accuracy:
0.7660

Condition B accuracy:
0.8400

Delta:
+0.0740

Condition A macro accuracy:
0.7660

Condition B macro accuracy:
0.8400

Delta:
+0.0740

## ACCEPT / REJECT

Condition A ACCEPT:
0.3400

Condition B ACCEPT:
1.0000

Condition A REJECT:
0.6600

Condition B REJECT:
0.3500

## Paired semantics

Condition A pair accuracy:
0.0000

Condition B pair accuracy:
0.3500

Condition A margin reversal:
0.0000

Condition B margin reversal:
0.3500

Condition A mean margin flip:
+0.019857

Condition B mean margin flip:
+0.635267

## Within-channel ACCEPT / REJECT

Arithmetic:
A = 0.5000
B = 0.5294

Structural:
A = 0.5000
B = 1.0000

Code property:
A = 0.5000
B = 0.5000

## Pair correctness by channel

Arithmetic:
A = 0.0000
B = 0.0588

Structural:
A = 0.0000
B = 1.0000

Code property:
A = 0.0000
B = 0.0000

## Main scientific result

Complete exposure to the original curriculum was not sufficient to produce counterfactual verifier semantics.

Condition A saw all 2500 verifier records exactly once but retained:

pair accuracy = 0.0000

margin reversal = 0.0000

and chance-level within-channel ACCEPT/REJECT discrimination.

Matched counterfactual training changed this substantially.

Condition B reached:

pair accuracy = 0.3500

margin reversal = 0.3500

and a strongly positive mean pair margin flip.

The effect was highly channel-specific.

Structural verification reached:

within-channel accuracy = 1.0000

pair accuracy = 1.0000

Arithmetic remained near chance.

Code-property verification remained at chance.

## Interpretation

The experiment provides development evidence that counterfactual training geometry matters beyond verifier exposure alone.

It does not establish general typed verifier semantics.

The strongest supported interpretation is:

The Native Cortex can learn an explicit relational verifier distinction when the verifier-relevant feature is directly represented in the observation, but the current training objective and architecture do not yet reliably learn computational verifier semantics requiring arithmetic evaluation or bounded program execution.

Both conditions FAIL the frozen full verifier-semantics gate.

Do not run held-out.

Do not weaken the verifier.

Do not reinterpret Condition B as full verifier-semantics success.
