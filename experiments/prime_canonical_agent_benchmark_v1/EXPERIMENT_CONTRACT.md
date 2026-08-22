# PRIME Canonical Agent Benchmark v1
## Frozen Experimental Contract

Status: FROZEN BEFORE BENCHMARK IMPLEMENTATION OR RESULT INSPECTION

This document defines the first canonical controlled experiment for testing
whether verifier-governed adaptive representation repair provides measurable
decision-making benefit under partial observability.

The contract must not be edited in response to benchmark outcomes.

If the design itself later proves defective, the experiment is retired and a
new version is created with explicit lineage. Results from this version are not
silently reinterpreted under a changed contract.

---

# 1. Primary research question

Does verifier-governed adaptive representation repair improve online learning
under partial observability when the minimum useful memory representation
varies between worlds?

The tested mechanism is not merely "more memory."

The tested mechanism is:

    observation/history
        -> detect representation obstruction
        -> propose bounded representation growth
        -> independently verify candidate repair
        -> authorize or reject repair
        -> continue learning with canonical receipt history

Proposal is never authority.

---

# 2. Primary claim

The FULL PRIME condition will be considered supported on this benchmark only if
it achieves better frozen-evaluation learning efficiency than the fixed
representation selected using development worlds, while maintaining competitive
final task performance.

The benchmark does not presuppose that this claim is true.

A null or negative result is a valid result.

---

# 3. Explicit non-claims

This benchmark does NOT by itself establish:

- general intelligence;
- AGI;
- universal superiority of TS or PRIME;
- superiority over all recurrent neural architectures;
- optimal POMDP solution;
- production security;
- external scientific replication;
- broad real-world generalisation;
- that the sealed PRIME v18 proposal model is semantic authority.

The first benchmark is a controlled mechanistic test.

Broader claims require stronger external environments and learned-memory
baselines.

---

# 4. Controlled environment family

Working environment name:

    MemoryAlias-POMDP

Each world contains a latent dependency depth:

    d in {0, 1, 2, 4}

The agent is NOT told d.

At each decision step the environment exposes only the current binary
observation.

The correct action depends on information whose required temporal depth is
determined by d.

Therefore the current observation is insufficient in worlds with d > 0.

The implementation may retain past observations/actions only through the
representation supplied to that experimental condition.

No agent may inspect:

- latent environment state;
- d;
- future observations;
- evaluation labels before acting;
- another condition's internal state.

Environment randomness must be deterministic from an explicit seed.

The exact environment transition/reward implementation must be committed before
the first reported benchmark result and thereafter remain frozen for v1.

---

# 5. Representation family

The initial representation is observation-only.

Permitted candidate history depths are:

    0
    1
    2
    4

Representation growth is monotone within an experimental run.

FULL PRIME begins at depth 0.

A repair proposal may only request the next permitted representation depth.

The maximum number of accepted representation-growth operations in one run is
three.

No repair may inject the hidden world parameter d.

---

# 6. Experimental conditions

At minimum the benchmark must contain:

A. REACTIVE
   Observation-only representation for the entire run.

B. FIXED-H1
   Fixed history depth 1.

C. FIXED-H2
   Fixed history depth 2.

D. FIXED-H4
   Fixed history depth 4.

E. ADAPTIVE-NO-VERIFIER
   Uses the same obstruction/proposal mechanism as FULL PRIME but accepts a
   proposed representation expansion without independent verifier authority.

F. VERIFIER-NO-REPAIR
   Runs verifier/evidence machinery but representation growth is disabled.

G. FULL-PRIME
   Obstruction detection, proposal, independent verification, authorization,
   canonical repair receipt, and continued learning.

All conditions must use the same underlying task-learning algorithm wherever
the comparison permits.

Representation management, not a secretly stronger learner, is the intended
independent variable.

---

# 7. Verifier requirement

FULL PRIME candidate repair must be evaluated using evidence distinct from the
proposal decision itself.

The verifier must independently compare the current representation against the
candidate representation on a bounded replay/evidence slice.

The acceptance rule must include both:

1. predictive/decision evidence supporting the candidate representation; and
2. an explicit complexity cost for representation growth.

The proposal component may not directly authorize canonical representation
change.

Rejected proposals have zero canonical representation effect.

---

# 8. Development/evaluation separation

Development world seeds:

    0 through 31 inclusive

Frozen evaluation world seeds:

    1000 through 1127 inclusive

Evaluation seeds are frozen but NOT claimed to be cryptographically blinded
from the implementer.

Development worlds may be used to:

- debug implementation;
- set implementation-correctness constants;
- select the fixed-history comparison baseline from H1/H2/H4.

Frozen evaluation worlds must not be used to choose:

- thresholds after seeing evaluation performance;
- alternative metrics;
- favourable baseline definitions;
- favourable environment variants;
- favourable seed subsets.

All 128 frozen evaluation seeds must be reported.

---

# 9. Primary metric

Primary metric:

    area under the online learning curve

computed over the preregistered training horizon.

The exact horizon and normalization must be fixed in code before the first
evaluation-result inspection and recorded in the benchmark manifest.

Higher is better.

The metric must use every preregistered evaluation episode.

No episode deletion is allowed except for a run that fails a predeclared
integrity check, in which case the complete failed run remains recorded.

---

# 10. Secondary metrics

The benchmark must also report:

- final-window mean reward;
- cumulative regret against the environment's available optimal action;
- accepted repair count;
- rejected repair count;
- proposed repair count;
- final representation depth;
- representation-change episode indices;
- adaptation latency;
- canonical receipt count;
- integrity failures;
- deterministic run identity.

Where meaningful, representation complexity must be reported alongside reward.

---

# 11. Baseline selection rule

The single FIXED representation used for the primary head-to-head comparison is
selected using development worlds only.

The rule is:

1. run FIXED-H1, FIXED-H2, and FIXED-H4 on every development seed;
2. select the depth with the highest mean primary metric;
3. ties select the smaller representation.

After selection, that baseline is frozen for evaluation.

All fixed baselines must still be reported on evaluation worlds.

---

# 12. Success criterion

The primary claim is supported only if, on all frozen evaluation worlds:

1. FULL PRIME has positive paired mean primary-metric difference versus the
   development-selected fixed baseline;

2. a deterministic paired bootstrap 95% confidence interval for that
   difference has lower bound greater than zero;

3. FULL PRIME final-window reward is not materially degraded relative to that
   selected fixed baseline;

4. the improvement is not reproduced equally or better by the
   ADAPTIVE-NO-VERIFIER ablation without being explicitly reported;

5. all integrity and receipt checks pass.

If condition 1 or 2 fails, the primary advantage claim is unsupported.

If FULL PRIME loses, that result is retained.

---

# 13. Ablation interpretation

The benchmark must not report only FULL PRIME versus weak baselines.

Interpretation requires examining:

FULL PRIME vs ADAPTIVE-NO-VERIFIER

to test whether verifier gating contributes useful selectivity;

FULL PRIME vs VERIFIER-NO-REPAIR

to test whether representation repair itself contributes useful adaptation;

FULL PRIME vs fixed representations

to test whether adaptive representation choice contributes learning efficiency.

Ablation failures must be discussed rather than hidden.

---

# 14. Determinism and provenance

Each run must bind at least:

- benchmark version;
- source commit;
- environment configuration;
- condition;
- world seed;
- learner seed;
- representation parameters;
- verifier parameters;
- result payload;
- receipt chain or equivalent canonical evidence.

Canonical reports must contain no timestamps, random UUIDs, machine-specific
absolute paths, or scheduler-dependent ordering.

Repeated execution from the same source/configuration must reproduce identical
canonical result bytes.

---

# 15. Tamper and replay requirements

Before public interpretation, v1 must test:

- result tampering;
- receipt tampering;
- representation-repair receipt tampering;
- seed/configuration mismatch;
- replay from an empty benchmark state;
- duplicate result insertion;
- altered environment manifest;
- altered frozen contract.

Tampered evidence must fail closed.

---

# 16. Public-result gate

A public claim stronger than:

    "controlled benchmark evidence"

requires at least one additional learned-memory baseline.

Candidate later baselines include:

- recurrent neural agent;
- GRU/LSTM state estimator;
- learned latent-state model.

Those may require PyTorch and belong to a later benchmark layer if not present
in the dependency-free v1 harness.

Their absence must be stated clearly.

---

# 17. Architecture constraint

This benchmark does not create a parallel PRIME.

It lives in the existing BoggersTheAI / PRIME research lineage.

Existing PRIME authority boundaries remain authoritative.

The sealed PRIME v18 archive remains immutable and proposal-only.

Learned or heuristic machinery may propose.

Verifier-governed authority decides canonical repair.

---

# 18. Falsification policy

No mechanism is protected from a negative result.

If:

- representation repair does not improve learning;
- verifier gating does not help;
- fixed history wins;
- complexity costs dominate;
- the adaptive condition becomes unstable;

the result is evidence about the architecture.

The benchmark exists to reduce uncertainty, not to manufacture a win.

