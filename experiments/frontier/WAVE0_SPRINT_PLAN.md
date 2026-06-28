# Wave 0 Sprint Plan: Production Foundation + First Non-Toy Verifiable Capability

Goal (per SERIOUS_GPT55_ROADMAP): Turn excellent scattered components into one coherent, usable TS Engine that can do *real* (small but non-toy) frontier-style tasks with full receipts.

**Definition of "non-toy" for this sprint gate**:
- Multi-step formal task that requires language parsing → graph state → wave exploration + tension → verifier gate → BOGVM execution of a plan → receipt that proves the result.
- Example class: "Given these axioms and a goal, produce a verified plan, execute it in BOGVM, and prove the final claim with full chain."
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
  1. Takes one of the hard seed tasks as text.
  2. Runs the full pipeline (language → graph + waves + BOGVM simulation + verifier gates + proposer where useful).
  3. Produces a correct, checkable artifact (proof or passing execution) + complete tamper-evident receipt bundle.
  4. Receipt is rich enough that you can see tension driving focus, which verifier steps passed/failed, BOGVM execution trace, etc.
- Must run on this device without external LLM in the core path.
- Should feel like "this could actually do useful formal work if we scale it."

**Status (2026-06)**: Mostly complete. Unified engine + BOGVM + VerifierOS + TSLC + self-data skeleton + hard tasks + scale probe + demos (gpt55_progress etc.) running. Factual light/fast (2 waves/0 BOGVM); formal produces real BOGVM traces; self-data injection + math boosts + proof prompts live. Graph ~35 nodes. See SERIOUS_GPT55_ROADMAP.md for details/progress. Probes confirm loop starting.

## Risks for this sprint
- Import hell in the monorepo will slow unification — use adapters and thin wrappers aggressively.
- BOGVM spawn overhead — profile early, keep simulations short at first.
- Verifier power still limited — start narrow and deep rather than broad and shallow.

## Success criteria (not vibes)
- At least 5 of the hard seed tasks run end-to-end and produce correct receipts.
- Measurable improvement from the new Tension proposer on a held-out set.
- Receipt format is stable enough that we can start versioning it.
- No external LLM used for core reasoning, proposals, or verification in the gate demo.

---

After this sprint we re-assess against the full SERIOUS_GPT55_ROADMAP and decide what Wave 1 looks like.

Let's execute like it matters.