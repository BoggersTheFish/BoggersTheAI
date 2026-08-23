# Mega PRIME Native Cortex V1 — Development Result

Status: DEVELOPMENT ONLY

Parameters:
    5,552,205

Training:
    2,000 optimizer steps
    batch size 4
    sequence length 128
    BPE vocabulary 4096

Development language:

NORMAL
    CE  = 5.2115
    PPL = 183.38
    BPB = 2.0788

RESET_RECURRENCE
    CE  = 5.4520
    PPL = 233.22
    BPB = 2.1747

NO_LOCAL_ATTENTION
    CE  = 5.4470
    PPL = 232.07
    BPB = 2.1727

Recurrent contribution:
    +0.0959 BPB

Local-attention contribution:
    +0.0939 BPB

Routing:

L0 H=0.991 max expert share=0.205
L1 H=0.999 max expert share=0.178
L2 H=0.992 max expert share=0.201
L3 H=0.994 max expert share=0.195

Diagnosis:

    Multi-timescale recurrence contributes on unseen prose.
    Local exact attention independently contributes on unseen prose.
    The previous deep MoE collapse has been eliminated.
    Balanced utilization does not yet establish semantic specialization.

Authority:
    NONE

No held-out evaluation was performed.
