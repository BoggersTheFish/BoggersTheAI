# PRIME M20 Universal Arena v0.2

Status:

    DEVELOPMENT PROTOCOL

Held-out seeds remain:

    6000..6031

They have not been run.

v0.2 corrects three v0.1 development issues:

1. condition-independent exploration schedule;
2. predictive-partition recovery in addition to syntactic recovery;
3. imbalance diagnostics.

Architecture and task families are otherwise unchanged.

Primary future held-out comparison remains:

    M20-CONSTRUCTION
        versus
    FIXED-H8

AULC remains the online-learning-efficiency metric.

Additional reporting:

    exact-expression recovery;
    predictive-partition recovery;
    balanced accuracy;
    target prevalence;
    best constant accuracy;
    excess accuracy over best constant;
    oracle gap.

Predictive partition equivalence for binary features includes exact complement:

    q(h) = f(h)

or

    q(h) = 1 - f(h)

because either induces the same two-cell partition of history space.

This equivalence rule is frozen before v0.2 development results.
