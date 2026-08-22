# PRIME M20 Universal Arena v0.1
## Development Diagnosis

Held-out seeds 6000..6031 were not run.

Development result:

    M20-CONSTRUCTION AULC:
        887347

    FIXED-H8 AULC:
        704211

    ORACLE-FEATURE AULC:
        945416

    REACTIVE AULC:
        632637

Receipt integrity:

    PASS

Reported syntactic target recovery:

    80 / 96

Two development issues were identified before any held-out execution.

## 1. Representation-equivalence metric

XOR(a,b) and EQ(a,b) are binary complements:

    EQ(a,b) = 1 - XOR(a,b)

They induce the same binary partition of histories.

A downstream tabular policy can therefore use either representation with no
loss of predictive sufficiency by reversing the output mapping.

The v0.1 exact-expression metric counts this as failure even when the recovered
representation contains the same predictive information.

Arena v0.2 must therefore retain exact-expression recovery but additionally
report predictive-partition recovery.

This is a diagnostic correction, not a claim that arbitrary different
expressions are equivalent.

## 2. Condition-specific exploration randomness

v0.1 derives learner exploration randomness partly from the condition name.

Thus REACTIVE, FIXED-H8, ORACLE-FEATURE and M20-CONSTRUCTION do not receive
identical exploration schedules.

Arena v0.2 will use one condition-independent exploration schedule for every
task/seed pair.

## 3. Class imbalance

AND / OR families have unequal target prevalence.

Raw accuracy and AULC remain useful for paired comparisons, but v0.2 must also
report:

    target prevalence;
    best-constant accuracy;
    excess accuracy over constant;
    balanced accuracy.

## Status

Arena v0.1 is retained as development evidence.

It is superseded for future held-out evaluation by a separately frozen Arena
v0.2 protocol.

No held-out result exists for Arena v0.1.
