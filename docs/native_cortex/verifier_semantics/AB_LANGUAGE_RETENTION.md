# PRIME Native Cortex Verifier Semantics A/B Language Retention

State date: 2026-08-27

## Frozen retention criterion

NORMAL development BPB must be less than or equal to:

2.1788

The criterion applies to normal model operation.

RESET_RECURRENCE and NO_LOCAL_ATTENTION are diagnostic ablations and are not themselves retention gates.

## References

Native Cortex V1 before bridge training:

NORMAL BPB = 2.0788

First Cortex-PRIME bridge:

NORMAL BPB = 2.0821

## Condition A — exposure_control

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

Language retention:

PASS

## Condition B — counterfactual_paired

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

Language retention:

PASS

## Comparison

Condition A NORMAL BPB:

2.0805

Condition B NORMAL BPB:

2.0769

Difference B minus A:

-0.0036 BPB

This small difference is not interpreted as evidence of meaningful language improvement.

The important result is that neither condition exhibits language degradation relative to the frozen retention ceiling.

Routing remains distributed across experts in both conditions.

Recurrence and local attention remain measurably useful under both conditions.

## Scientific interpretation

Condition B's improvement in counterfactual verifier behaviour was not purchased through catastrophic degradation of the Native Cortex language model.

The verifier-semantics A/B result can therefore be interpreted together with preserved language capability.

Condition B still fails the full frozen verifier-semantics gate.

The supported result is partial and channel-specific:

structural counterfactual semantics were learned strongly;

arithmetic counterfactual semantics remained near chance;

code-property counterfactual semantics remained unresolved.

Authority remains NONE.

No held-out data was accessed.
