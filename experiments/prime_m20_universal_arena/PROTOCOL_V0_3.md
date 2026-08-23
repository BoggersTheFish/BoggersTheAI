# PRIME M20 Universal Adaptive-State Arena v0.3

Status:

    DEVELOPMENT PROTOCOL
    FROZEN BEFORE v0.3 DEVELOPMENT RESULTS

v0.3 supersedes the unexecuted v0.2 held-out evaluation.

No v0.2 or v0.3 held-out seed had been executed when this protocol was frozen.

Development seeds:

    600..607 inclusive

Held-out seeds:

    6000..6031 inclusive

Task families:

    CURRENT
    LAG-1
    LAG-4
    LAG-7
    XOR-1-4
    XOR-2-7
    EQ-1-4
    AND-1-4
    OR-2-7
    XOR-1-2-3
    AND-1-2-4
    OR-2-3-4

Conditions:

    REACTIVE
    FIXED-H8
    ORACLE-FEATURE
    M20-CONSTRUCTION

Scored steps:

    1536 per world

Final window:

    256

Candidate field:

    max lag = 8
    max simultaneous candidates = 256
    non-authoritative higher-order scaffolds enabled

Matched exploration:

    all conditions on a task/seed world use the same
    condition-independent action-randomness schedule.

Predictive quotient:

    exact binary complements count as the same predictive partition.

Global adaptive evidence budget:

    alpha_run <= 1/64

For zero-indexed adaptive representation epoch e:

    alpha_e =
        1 / (64 * 2^(e + 1))

For N_e candidate streams:

    T_e =
        64 * N_e * 2^(e + 1)

Evidence condition:

    3^W >= T_e * 2^(W + L)

plus the existing structural-complexity gate.

This replaces the v0.2 adaptive per-epoch reuse of the 1/64 budget.

Primary DEVELOPMENT diagnostics:

    AULC ppm
    final-window accuracy
    balanced accuracy
    predictive-partition recovery
    exact-expression recovery
    authorization latency
    receipt integrity
    paired M20 - FIXED-H8 differences
    paired M20 - ORACLE differences

No inferential scientific claim may be made from development seeds.

A separate v0.3 held-out analysis plan must be frozen after development and
before seed 6000 is executed.
