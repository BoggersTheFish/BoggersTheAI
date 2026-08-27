# PRIME M20 Global Sequential Alpha Spending

Status:

    FROZEN ARCHITECTURE CORRECTION BEFORE HELD-OUT EVALUATION

The original M20 construction evidence corrected multiplicity across candidate
streams inside one representation epoch.

Adaptive compositional PRIME may open multiple representation epochs after
verifier-authorized construction changes.

Applying the full run-level alpha budget independently to every adaptive epoch
would not provide a run-level family-wise budget across an unbounded sequence
of epochs.

M20-F0 therefore allocates the evidence budget across epochs.

For zero-indexed epoch e:

    alpha_e =
        1 / (64 * 2^(e + 1))

Hence:

    sum_e alpha_e = 1 / 64

For N_e simultaneous candidate evidence streams in epoch e, each stream uses
the exact threshold denominator:

    T_e =
        64 * N_e * 2^(e + 1)

Equivalently:

    epoch 0:
        128 * N_0

    epoch 1:
        256 * N_1

    epoch 2:
        512 * N_2

and so on.

The evidence gate remains:

    3^W >= T_e * 2^(W + L)

together with the existing structural-complexity gate.

This establishes the scheduled run-level family-wise budget under the same
conditional e-process validity assumptions used by the existing verifier.

Legacy single-epoch M20-A behaviour remains reproducible when EvidenceEpoch is
constructed without an adaptive epoch index.

Every adaptive compositional EvidenceEpoch must supply its zero-indexed
representation epoch.

No PRIME M20 Universal Arena held-out seeds had been executed when this
correction was introduced.

Arena v0.1 and v0.2 development artifacts remain immutable historical evidence.
The unexecuted v0.2 held-out plan is superseded by Arena v0.3.
