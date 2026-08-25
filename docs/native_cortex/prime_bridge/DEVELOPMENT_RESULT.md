# Mega PRIME Cortex-PRIME Bridge Development Result

State date: 2026-08-25

## Status

This document freezes the observed development result of the first Cortex-PRIME mixed-learning bridge experiment.

The full preregistered verifier gate FAILED.

This result must not later be rewritten as a successful five-way verifier result.

## Core invariant

Neural prediction is not epistemic authority.

The Native Cortex may propose and predict.

Canonical PRIME verifiers remain authoritative.

## Base Native Cortex checkpoint

Path:
artifacts/native_cortex/v1/cortex-v1-final.pt

SHA256:
abf0d27a0fb29cb1d91853f4ff83c77720fbe3abb60477000448663553253cdd

## Bridge checkpoints

Step-2000 path:
artifacts/native_cortex/prime-bridge-v1/cortex-prime-step-002000.pt

Step-2000 SHA256:
e3c7790e988cf64612ef37ca302374cae6467885206a1128683f95a6b90a1b98

Final path:
artifacts/native_cortex/prime-bridge-v1/cortex-prime-final.pt

Final SHA256:
aa1119618e4668de79dce8d783a016d5699bd53df3232b0cffbada6938a59ca1

## Training programme

Total optimizer steps:
2000

Learning rate:
8e-5

Task mixture:
50 percent language modelling
30 percent semantic proposal learning
20 percent verifier prediction

Semantic records:
6000

Verifier records:
2500

Verifier curriculum:
UNKNOWN 500
ACCEPT 500
REJECT 500
REPAIR 500
ABSTAIN 500

Authority:
NONE

## Exposure limitation

Approximate verifier updates:
400

Expected unique verifier examples seen under random sampling with replacement:
approximately 370 of 2500

Approximate semantic updates:
600

Expected unique semantic examples seen:
approximately 571 of 6000

Therefore this experiment was an initial-exposure bridge experiment, not curriculum saturation.

## Language retention

Pre-bridge Native Cortex V1 development BPB:
2.0788

Post-bridge development BPB:
2.0821

Difference:
+0.0033 BPB

Approximate relative degradation:
0.16 percent

Frozen language-retention ceiling:
2.1788 BPB

Language-retention gate:
PASS

## Post-bridge ablations

NORMAL:
CE 5.2200
PPL 184.93
BPB 2.0821

RESET recurrence:
CE 5.4734
PPL 238.26
BPB 2.1832

NO local attention:
CE 5.4408
PPL 230.63
BPB 2.1702

Recurrent contribution:
+0.1011 BPB

Local-attention contribution:
+0.0881 BPB

Both architectural mechanisms retained measurable utility after bridge training.

## Routing health

Layer 0:
0.178 0.179 0.117 0.176 0.205 0.146

Layer 1:
0.186 0.158 0.178 0.183 0.147 0.148

Layer 2:
0.211 0.162 0.202 0.126 0.157 0.142

Layer 3:
0.177 0.107 0.161 0.188 0.181 0.187

Approximate normalized routing entropy:
L0 0.992
L1 0.997
L2 0.991
L3 0.991

There was no recurrence of the earlier catastrophic deep-expert collapse.

Balanced routing is not evidence of semantic expert specialization.

## Verifier development evaluation

Development examples:
500

Examples per class:
100

Overall accuracy:
0.7960

Macro class accuracy:
0.7960

Minimum class accuracy:
0.0000

Per-class accuracy:
UNKNOWN 1.0000
ACCEPT 0.0000
REJECT 1.0000
REPAIR 0.9800
ABSTAIN 1.0000

Prediction distribution:
UNKNOWN 100
ACCEPT 0
REJECT 202
REPAIR 98
ABSTAIN 100

Confusion matrix:

true/pred  UNKNOWN ACCEPT REJECT REPAIR ABSTAIN
UNKNOWN    100     0      0      0      0
ACCEPT     0       0      100    0      0
REJECT     0       0      100    0      0
REPAIR     0       0      2      98     0
ABSTAIN    0       0      0      0      100

Balanced chance:
0.20

## Frozen verifier gates

Required:
overall accuracy greater than 0.60
macro class accuracy greater than 0.60
minimum per-class accuracy greater than 0.35

Observed:
overall gate PASS
macro gate PASS
minimum-class gate FAIL

FULL FROZEN VERIFIER GATE:
FAIL

The criterion must not be moved after observing the result.

## Interpretation

The approximately 79.6 percent aggregate result does not establish full verifier semantics.

The learned behaviour was approximately:

UNKNOWN -> UNKNOWN
ACCEPT -> REJECT
REJECT -> REJECT
REPAIR -> REPAIR
ABSTAIN -> ABSTAIN

On five equally balanced classes this shortcut produces approximately 80 percent accuracy.

The most defensible conclusion is:

The cortex learned broad PRIME operational outcome topology but did not learn the internal pass/fail semantics of typed verification.

## Prompt-collision diagnostic

Development prompts:
500

Unique prompts:
500

Exact cross-label prompt collisions:
0

The ACCEPT failure therefore cannot be explained by ACCEPT and REJECT being serialized into identical neural inputs.

The verifier-relevant distinction was present.

## Current obstruction

Current behaviour:

typed obligation
-> broad outcome-family recognition

Target behaviour:

typed obligation
-> verifier-relevant relational or computational distinction
-> correct ACCEPT or REJECT prediction

Three hypotheses remain distinct:

1. insufficient verifier exposure
2. shortcut-friendly curriculum structure
3. insufficient learned relational or computational semantics

These hypotheses must not be conflated.

## Next development programme

Verifier Semantics / Counterfactual Bridge Development

The next curriculum should contain paired ACCEPT and REJECT examples where surface form is held as constant as practical and only the verifier-relevant fact changes.

Example:

37 + 18 = 55 -> ACCEPT
37 + 18 = 56 -> REJECT

The evaluator must be built before training.

It must include:

paired ACCEPT/REJECT joint correctness
within-channel ACCEPT/REJECT accuracy
ACCEPT-minus-REJECT score margins
paired margin reversal
five-way class metrics
language-retention evaluation

A control must compare:

existing curriculum plus substantially greater verifier exposure

against:

paired counterfactual curriculum with comparable exposure

This is required to distinguish underexposure from curriculum shortcutting.

## Held-out discipline

Native Cortex held-out SHA256:
509907b29546ecee73f464f44dd53a6a809b3b80a5e1d3f27c25846ac083ae8c

The held-out split remains untouched.

M26 held-out seeds also remain untouched.

## Canonical conclusion

The first Cortex-PRIME bridge experiment demonstrated that PRIME-shaped continual neural training can occur while preserving essentially all previously measured language competence and maintaining healthy recurrent, local-attention and sparse-MoE behaviour.

It also demonstrated substantial learning of PRIME operational outcome families.

However, the experiment FAILED its full preregistered verifier gate because ACCEPT accuracy was 0 percent.

The cortex therefore did not demonstrate genuine five-way typed verifier semantics.

This failure is preserved as a canonical research result.
