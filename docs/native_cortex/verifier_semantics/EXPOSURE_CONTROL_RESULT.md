# Verifier Semantics A/B — Condition A Exposure Control

State date: 2026-08-26

Condition:
exposure_control

Purpose:
Test whether complete exposure to the original verifier curriculum is sufficient to eliminate the ACCEPT/REJECT obstruction.

Starting checkpoint SHA256:
aa1119618e4668de79dce8d783a016d5699bd53df3232b0cffbada6938a59ca1

Final checkpoint SHA256:
73d40bb229a1ac738e5148e67b171f7f8f8f4c6338b2454bcc0186e2a41c4df0

Verifier curriculum SHA256:
09a08d5924c7f0616d16beecce6c75f03e52ce6cfe100afa3f00c2d9cf4c6516

Verifier presentations:
2500

Unique verifier records seen:
2500

Class presentations:
UNKNOWN 500
ACCEPT 500
REJECT 500
REPAIR 500
ABSTAIN 500

Optimizer task counts:
LM 300
semantic 200
verifier 500

Development curriculum SHA256:
39e869122c1086ffcdc72d06e3dba74f4f0e228cef143c9d9bd8cb0c3cd91587

Overall accuracy:
0.7660

Macro accuracy:
0.7660

Minimum class accuracy:
0.3400

Per-class accuracy:
UNKNOWN 1.0000
ACCEPT 0.3400
REJECT 0.6600
REPAIR 0.8300
ABSTAIN 1.0000

Within-channel ACCEPT/REJECT accuracy:
arithmetic 0.5000
structural 0.5000
code_property 0.5000

Pair accuracy:
0.0000

Margin reversal rate:
0.0000

Mean ACCEPT margin:
-0.436327

Mean REJECT margin:
-0.456184

Mean margin flip:
+0.019857

Pair accuracy by channel:
arithmetic 0.0000
structural 0.0000
code_property 0.0000

Full prompt collisions:
0

Truncated token collisions:
0

Malformed pairs:
0

FULL VERIFIER SEMANTICS GATE:
FAIL

Interpretation:

Complete exposure to the original verifier curriculum materially changed the neural classifier and caused it to emit ACCEPT predictions, increasing ACCEPT development accuracy from 0.0000 to 0.3400.

However, it did not produce counterfactual verifier semantics.

The ACCEPT and REJECT confusion rows were identical:

ACCEPT -> 34 ACCEPT, 66 REJECT
REJECT -> 34 ACCEPT, 66 REJECT

Matched pair accuracy remained zero and margin reversal remained zero across arithmetic, structural and code-property channels.

Therefore the first bridge failure cannot now be attributed solely to the earlier approximately 15 percent unique verifier exposure.

Underexposure contributed to classifier behaviour, but one complete epoch of the original shortcut-friendly curriculum was insufficient to teach the verifier-relevant ACCEPT/REJECT distinction.

Condition B tests whether matched counterfactual curriculum geometry changes this result.
