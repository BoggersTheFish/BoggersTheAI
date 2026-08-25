# PRIME Native Cortex Verifier Semantics A/B Experiment

State date: 2026-08-25

## Purpose

Separate two explanations for the first Cortex-PRIME verifier failure:

H1:
insufficient verifier exposure

H2:
shortcut-friendly verifier curriculum geometry

## Starting checkpoint

Both conditions start independently from the same frozen first-bridge checkpoint.

SHA256:

aa1119618e4668de79dce8d783a016d5699bd53df3232b0cffbada6938a59ca1

Neither condition continues from the other.

## Condition A

Name:

exposure_control

Verifier curriculum:

the original frozen five-way typed verifier curriculum

Train SHA256:

09a08d5924c7f0616d16beecce6c75f03e52ce6cfe100afa3f00c2d9cf4c6516

Purpose:

Test whether complete verifier-curriculum exposure alone eliminates the ACCEPT obstruction.

## Condition B

Name:

counterfactual_paired

Verifier curriculum:

the matched counterfactual five-way curriculum

Train SHA256:

b7ebab7b3b8bcee3a476a7a13cc41e356b2e25ba8c6f2c15b2c83e7994252025

Purpose:

Test whether changing training geometry so that ACCEPT and REJECT differ only in verifier-relevant facts improves genuine pass/fail discrimination.

## Controlled variables

Both conditions use:

the same starting checkpoint

the same optimizer state from that checkpoint

the same learning rate

the same model architecture

the same semantic replay stream

the same LM replay stream

the same total optimizer-step count

the same LM optimizer-step count

the same semantic optimizer-step count

the same verifier optimizer-step count

the same verifier presentation count

the same verifier class balance

the same max sequence length

the same seed policy

the same development evaluator

the same frozen counterfactual development set

the same language-retention evaluator

The treatment variable is verifier curriculum only.

## Stage-1 training schedule

Total optimizer steps:

1000

For every ten optimizer steps:

3 LM steps

2 semantic steps

5 verifier steps

Therefore:

LM optimizer steps:
300

semantic optimizer steps:
200

verifier optimizer steps:
500

## Verifier microbatch

Each verifier optimizer step accumulates gradients from:

5 verifier examples

before one optimizer update.

Therefore total verifier presentations are:

500 * 5 = 2500

Both verifier curricula contain exactly:

2500 records.

## Coverage rule

Verifier examples are shuffled deterministically without replacement.

Stage 1 presents every verifier curriculum record exactly once.

Required:

verifier presentations = 2500

unique verifier records seen = 2500

No verifier record may be omitted.

No verifier record may be repeated during Stage 1.

This removes the approximately 15-percent unique-exposure limitation of the first bridge experiment.

## Neural update rule

The complete Native Cortex remains trainable.

The verifier objective remains ordinary five-way cross entropy.

The router regularizer remains active.

Gradient norm remains clipped to:

1.0

No contrastive pair-specific loss is introduced in Stage 1.

This is deliberate.

Condition B tests whether counterfactual curriculum geometry alone improves semantics before introducing a specialized paired loss.

## Optimizer

Continue the AdamW optimizer state stored in the frozen bridge checkpoint.

Learning rate:

8e-5

Both conditions use the same optimizer continuation procedure.

## Seed

26082511

LM/semantic sampling and verifier ordering use separated deterministic random streams so changing verifier curriculum contents cannot alter LM or semantic sampling choices.

## Development evaluator

Both trained conditions are evaluated against the same frozen counterfactual development curriculum.

Development SHA256:

39e869122c1086ffcdc72d06e3dba74f4f0e228cef143c9d9bd8cb0c3cd91587

The previously frozen verifier-semantics gates remain unchanged.

## Language retention

Both conditions must rerun the existing Native Cortex V1 development language evaluator.

Reference:

pre-bridge V1 = 2.0788 BPB

first bridge = 2.0821 BPB

Frozen retention ceiling:

2.1788 BPB

## Interpretation matrix

If Condition A passes and Condition B passes:

underexposure was likely a substantial contributor; paired geometry may or may not provide additional benefit.

If Condition A passes and Condition B fails:

paired construction harmed learning under the tested protocol.

If Condition A fails and Condition B passes:

curriculum shortcut geometry was the stronger demonstrated obstruction.

If both fail:

one complete verifier epoch with ordinary five-way cross entropy was insufficient under both curricula.

A both-fail result does not prove architecture incapacity.

A later second-epoch or paired-loss experiment would require a separately frozen extension protocol.

## Authority

The neural verifier head has authority NONE.

Canonical PRIME verifiers remain authoritative.

## Held-out discipline

No held-out corpus data is accessed.

M26 held-out seeds remain untouched.

This experiment is development-only.
