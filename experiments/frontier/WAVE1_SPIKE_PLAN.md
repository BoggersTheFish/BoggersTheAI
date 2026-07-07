# Wave 1 Spike Plan: BOGVM Wave Payloads

Goal: demonstrate one narrow loop, not all of Wave 1.

A graph node can carry a bounded BOGVM program payload. A wave cycle can
discover it, execute it safely, record the execution artifact, and feed that
observation back into graph state without treating execution as proof.

## Current Spike

Implemented path:

- Typed `bogvm_program` payloads with program id, assembly source, deterministic
  program hash, bounded `max_steps`, creator and provenance.
- Graph helpers to add runnable payload nodes, discover runnable payloads and
  record `bogvm_execution_observation` nodes.
- `WaveCycleRunner.run_single_cycle()` executes at most the configured payload
  count per cycle, defaulting to one. It collects jobs under the graph lock,
  executes BOGVM outside the lock, then records observations under the lock.
- BOGVM execution artifacts expose program hash, VM receipt hash, execution
  status, exit code and artifact hash.
- Every observation records `state_commit_authorized: false`.
- The first `bogvm_observation` verifier can consume an observation artifact and
  check exact facts only: artifact hash, program hash, VM receipt hash,
  execution status, exit code, receipt presence and non-authorizing observation
  state.
- The first `bogvm_arithmetic_program` verifier can consume that observation
  evidence and check one strict property: exact integer output equality from a
  bounded `result:<integer>` BOGVM data-block convention.

Demo:

```bash
python -m experiments.frontier.bogvm_wave_payload_demo
python -m experiments.frontier.bogvm_observation_verifier_demo
python -m experiments.frontier.bogvm_arithmetic_program_verifier_demo
```

## Authority Boundary

BOGVM execution is evidence/observation. It is not semantic proof.

Kernel v0.2 remains the authority boundary:

- Language may propose.
- Confidence may suggest.
- BOGVM may execute.
- Only verifier-backed committed receipts authorize canonical TS state.

Unsupported, failed, blocked or unknown VM execution must not authorize truth
state. It may produce a failed observation for audit.

The observation verifier does not make BOGVM execution proof. It records a typed
verifier result saying exact artifact facts matched. Any future semantic claim
still needs its own verifier obligation and commit policy decision.

The arithmetic/program verifier is also intentionally tiny. It does not prove
that BOGVM understands programs. It checks a bounded observation artifact,
strict output schema and exact expected integer, then lets the existing kernel
commit policy decide.

## Not Yet

This spike does not implement:

- deep simulation
- rich scheduling
- normal master receipt linkage for graph observations
- broad code/property verification
- arbitrary program semantics
- graph scale work

## Next Work

1. Add richer verifier domains that use observations as evidence without
   treating execution completion as proof by itself.
2. Polish receipt linkage for observation-consuming transactions.
3. Improve payload scheduling and retry policy.
4. Scale only after seed receipts and wave observations stay deterministic.
