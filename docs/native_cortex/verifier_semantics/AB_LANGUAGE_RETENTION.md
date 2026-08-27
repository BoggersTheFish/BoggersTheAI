# PRIME Native Cortex Verifier Semantics A/B Language Retention

State date: 2026-08-27

## Retention criterion

Frozen NORMAL development retention ceiling:

2.1788 BPB

The RESET_RECURRENCE and NO_LOCAL_ATTENTION measurements are diagnostic ablations, not retention gates.

## Reference measurements

Native Cortex V1 before bridge training:

NORMAL BPB = 2.0788

First Cortex-PRIME bridge:

NORMAL BPB = 2.0821

## Condition A: exposure control

Final checkpoint SHA256:

73d40bb229a1ac738e5148e67b171f7f8f8f4c6338b2454bcc0186e2a41c4df0

NORMAL:

CE = 5.2159
PPL = 184.17
BPB = 2.0805

RESET_RECURRENCE:

BPB = 2.1850

NO_LOCAL_ATTENTION:

BPB = 2.1704

Recurrent BPB contribution:

+0.1045

Local-attention BPB contribution:

+0.0899

Retention result:

PASS

## Condition B: counterfactual paired

Final checkpoint SHA256:

440b668de1c310e6a7eded47a68da7b8f6977f4b0f36abc1fc22e205d3939e74

NORMAL:

CE = 5.2068
PPL = 182.52
BPB = 2.0769

RESET_RECURRENCE:

BPB = 2.1757

NO_LOCAL_ATTENTION:

BPB = 2.1695

Recurrent BPB contribution:

+0.0988

Local-attention BPB contribution:

+0.0926

Retention result:

PASS

## Comparison

Condition A NORMAL BPB:

2.0805

Condition B NORMAL BPB:

2.0769

B minus A:

-0.0036 BPB

The difference is too small to interpret as evidence of meaningful language improvement.

The important result is that both conditions remain below the frozen language-retention ceiling.

## Combined interpretation

The counterfactual-paired condition changed verifier behaviour without catastrophic degradation of the Native Cortex language model.

Condition B nevertheless remains a partial verifier-semantics result.

It achieved:

35 percent matched-pair accuracy

35 percent margin reversal

100 percent structural matched-pair accuracy

while arithmetic remained near chance and code-property matched-pair accuracy remained zero.

Therefore the supported development result is that matched counterfactual supervision can teach an explicit relational verifier distinction while preserving language capability, but general computational verifier semantics have not yet been demonstrated.

The full frozen verifier-semantics gate remains failed.

Authority remains NONE.

No held-out data was accessed.
