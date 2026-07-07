# Wave 0 Sprint Plan: Production Foundation + First Non-Toy Verifiable Capability

Goal (per COGNITIVE_PHYSICS_ROADMAP): Turn excellent scattered components into one coherent, usable TS Engine that can do *real* (small but non-toy) frontier-style tasks with full receipts.

**Definition of "non-toy" for this sprint gate**:
- Multiple deterministic formal seed tasks that require language parsing,
  verifier gates, explicit commit/reject/quarantine/branch decisions and
  replayable receipts.
- Example class: "Given these axioms and a goal, produce a bounded proof object,
  link any required BOGVM proof artifact, and prove or reject the final claim
  with a receipt."
- Must work end-to-end without falling back to pure stubs for the core path.
- Full glass-box receipt that a third party could replay.

**Duration target**: 4-6 weeks of focused work.

## Concrete Sub-Tasks (prioritized)

1. **BOGVM + Graph Unification (highest leverage)**
   - Make BOGVM programs first-class payloads in the living graph (store program + manifest as node payload or special edge type).
   - Allow waves to spawn and monitor sub-BOGVM executions as "thought steps" (with their own tension/verifier accounting that feeds back to the parent graph).
   - Link graph deltas to BOGVM receipt ledgers in the master TurnReceipt / artifact receipt.
   - Files to touch: core/graph/universal_living_graph.py (new methods), core-vm integration points, receipts.py, wave_runner.py.
   - Success: A wave cycle can contain BOGVM steps and the receipt shows the mapping.

2. **Verifier OS v0.1**
   - Create `core/verifier/` (or reasoner/verifier_os) that wraps the best existing pieces:
     - VerifierFirstRuntimeKernel
     - TypedSupport + support_path_verifier
     - Proof chains + reasoning channels
     - CentralBrainRuntime for ledger
   - Add one real new domain verifier: basic arithmetic + simple code property checking that uses BOGVM execution.
   - Make it easy to call from wave rules and ts_chat-style compilation.
   - Must produce TypedSupportObject + hash-chained receipt on every gate.
   - Success: Can take a chain of premises + claim and either accept with proof object or reject with explanation + tension impact.

3. **Deterministic Language → Verifier Obligations (TSLC v0.2)**
   - Take the best from ts_chat.py + candidate_language + session_compiler.
   - Make it compile natural language into:
     - Graph deltas (premises as nodes/edges)
     - Initial verifier obligations (claims that must be proven)
     - Skeleton plan (sub-graph of steps that can become BOGVM programs)
   - Support basic ambiguity/uncertainty as explicit nodes (not hidden probability).
   - Success: End-to-end from text problem to graph + obligations + plan skeleton, fully receipted.

4. **First Serious Self-Data + Proposer**
   - Use the unified engine on 100-500 curated synthetic + small real formal problems (leverage existing generators in bozo/ and reasoner).
   - Filter aggressively to traces where final verifier passed + BOGVM execution succeeded.
   - Use those to train/fine-tune a Tension-based proposer (use bozo/ pipeline + ts_bridge patterns).
   - Plug the proposer into high-tension emergence and candidate generation.
   - Success: At least one measurable improvement in proposal quality on held-out formal tasks vs pure graph-native.

5. **Scale Probe + Bottleneck Fixes (10k-20k nodes)**
   - Stress the unified system on synthetic graphs of increasing size (chains + branches + contradictions).
   - Fix the biggest perf/memory issues (adjacency, receipt writing, BOGVM spawn overhead).
   - Hierarchical cluster support must actually help at this scale (summary waves).
   - Success: Clean runs at 10k+ nodes with reasonable time and full receipts.

6. **Hard Task Seed Set (north star)**
   - Curate 20-30 genuinely non-trivial verifiable tasks:
     - Multi-step math (transitivity + arithmetic + one non-trivial proof).
     - Small algorithm with full spec + properties.
     - Simple long-horizon planning with verification at steps.
   - Every task must have ground-truth verifiable outcome (executable or provable).
   - These become the permanent test suite. No more toy "all A are B" only.

**Gate Demo (the one runnable thing at end of sprint)**:
- Single command/script that:
  1. Loads the hard seed tasks as deterministic JSON.
  2. Runs each task through `TSKernel.transact()`.
  3. Produces one receipt per task and replays it.
  4. Shows verifier outcomes, BOGVM proof artifacts where required, replay
     status and commit decision.
- Must run on this device without external LLM in the core path.
- Should feel like "this could actually do useful formal work if we scale it."

**Status (2026-06)**: Kernel v0.2 is the current authority boundary. Unified
engine pieces, BOGVM-linked proof artifacts for supported formal proofs,
VerifierOS compatibility, TSLC compatibility, self-data skeleton, hard seeds
and scale probes exist. Factual paths remain light/fast. Current formal
reasoning is narrow and receipt-gated, not general intelligence.

**Kernel v0.2 update**: The authority boundary is now the canonical kernel:
language may propose, confidence may suggest, and BOGVM may execute, but only
verifier-backed committed receipts authorize canonical TS state. The current
non-toy gate command is:

```bash
python -m experiments.frontier.run_seed_tasks
boggers kernel run-seeds
```

This runner loads `experiments/frontier/seed_tasks/*.json`, runs every task
through `TSKernel.transact()`, saves receipts under `artifacts/seed_receipts/`,
replays each receipt, and exits nonzero on any expected-decision or replay
failure. The seed suite demonstrates commit, reject, quarantine and branch
decisions, plus allowlisted arithmetic and one tiny bounded code/property
example verifier. Current formal reasoning is still narrow; unsupported
verifier domains must be receipt-visible and must reject, abstain, quarantine or
branch rather than silently passing.

## Risks for this sprint
- Import hell in the monorepo will slow unification — use adapters and thin wrappers aggressively.
- BOGVM spawn overhead — profile early, keep simulations short at first.
- Verifier power still limited — start narrow and deep rather than broad and shallow.

## Success criteria (not vibes)
- At least 5 hard seed tasks run end-to-end and produce replayable receipts.
- The seed runner clearly shows commit, reject, quarantine, branch or abstain.
- Receipt format is stable enough that we can start versioning it.
- No external LLM is used for core reasoning, proposals, or verification in the gate demo.
- Next Wave 1 work deepens verifier power, moves BOGVM toward normal wave
  payloads, and scales the graph after seed receipts remain stable.

---

After this sprint we re-assess against the full COGNITIVE_PHYSICS_ROADMAP and decide what Wave 1 looks like.

Let's execute like it matters.
