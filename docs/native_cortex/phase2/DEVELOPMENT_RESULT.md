# Native Cortex Phase II — Development Result

Status:

    DEVELOPMENT ONLY

Architecture:

    BPE
    ternary-effective projections
    delta recurrent matrix memory
    four top-1 sparse experts
    954,281 total parameters

Training:

    9,756,028-token training stream
    2,000 optimizer steps
    batch size 8
    sequence length 128
    approximately 2.048 million token presentations

Tokenizer:

    4,096 vocabulary
    development sequence reduction versus byte tokenization:
        3.609427x

    BPE round-trip failures:
        0

Development evaluation:

NORMAL

    CE:
        5.9496

    PPL:
        383.59

    BPB:
        2.3732

RESET RECURRENT STATE EVERY TOKEN

    CE:
        6.2391

    PPL:
        512.38

    BPB:
        2.4886

RECURRENT BPB GAIN

    +0.1155 bits/byte

Interpretation:

    Retained recurrent state materially improves prediction on unseen
    development prose relative to the identical model with recurrent memory
    reset every token.

Routing:

Layer 0

    expert shares:
        0.242
        0.301
        0.260
        0.197

    maximum share:
        0.301

    normalized entropy:
        0.992

Layer 1

    expert shares:
        0.149
        0.001
        0.002
        0.848

    maximum share:
        0.848

    normalized entropy:
        0.320

Layer 2

    expert shares:
        0.000
        0.000
        1.000
        0.000

    maximum share:
        1.000

    normalized entropy:
        0.001

Diagnosis:

    Deep sparse routing has collapsed.

    The recurrent memory has earned continued architectural use.

Claim boundary:

    No held-out evaluation was performed.
    No language-capability or general-intelligence claim is authorized.
