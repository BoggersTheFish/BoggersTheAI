# Phase 2: World-Class Verifier + Language Stack — Start Plan

**Status**: Starting now (user: "phase 2 start")

**High-level from FRONTIER_PLAN.md**:
- Expand verifiers: Math (symbolic + numeric via BOGVM), code (full execution + property-based testing harness), science (hypothesis + evidence graphs), long-horizon consistency.
- Recursive verifiers + proof objects at scale (build on existing typed_support/proof_chain).
- TSLC vNext: Richer grammar, recursive frames, explicit ambiguity/uncertainty handling, multi-turn graph diff memory, pack system made production.
- Grounded planning: Plans are sub-graphs + BOGVM programs that can be simulated in waves before execution.
- Milestone: Verifiable agent that solves non-trivial SWE-bench-style tasks or multi-step math proofs with full receipts (higher reliability than current frontier LLMs on the same tasks).

## Detailed Subtasks for Phase 2

### 2.1 Verifier Expansion & Unification (core of Phase 2)
- Create `core/verifier/` or extend `reasoner/ts_reasoner/` integration:
  - Unified VerifierEngine that composes existing:
    - `typed_support` + `support_path_verifier` + `proof_chain`
    - Add domain verifiers:
      - MathVerifier: basic arithmetic/symbolic (use sympy if avail, or pure; integrate BOGVM for numeric).
      - CodeVerifier: parse small Python subsets, execute via BOGVM or sandbox, property checks.
      - HypothesisVerifier: for science-like (evidence accumulation).
  - Recursive verifiers: support nested proofs (claim verified by sub-verifier).
  - Proof objects: extend TypedSupportObject to full ProofObject with steps, sub-proofs, hashes.
- Integration with graph/waves:
  - After waves, run verifier on proposed deltas/claims.
  - Use tension to decide when to invoke deeper verifier.
  - Receipts always include verifier trace (build on existing tamper_evident_ledger).
- Leverage BOGVM: Use core-vm/bogvm for executing verified "programs" (plans as BOGVM bytecode? or simple ops).

### 2.2 TSLC vNext / Language Stack
- Enhance deterministic language (build on ts_chat.py, historical TSLC, candidate_language):
  - Richer parser: recursive frames, ambiguity nodes (explicit "maybe", confidence as separate graph attribute not authority).
  - Multi-turn: use graph diff memory (existing in some ts_chat), session nodes.
  - Pack system: make ts_packs / knowledge_pack_library production-ready.
  - Compile to: graph deltas + initial plan subgraphs + verifier obligations.
- Grounded: Output not just text, but executable plans (BOGVM snippets or wave programs).
- No external LLM in core path (use for thin surface only if needed, marked in receipt).

### 2.3 Grounded Planning & Execution
- Plans as first-class: sub-graphs with steps, preconditions, BOGVM programs.
- Simulate plans in waves before "commit" (tension on simulation failures).
- Execute via BOGVM: compile verified plans to bogvm programs, run in verifier sandbox, record results as support.
- Long-horizon: multi-level graphs (goals -> subplans), consistency verifiers across time.

### 2.4 Scale Verifiers & Proofs
- Make recursive + at graph scale: batch verification, incremental (only on changed subgraphs).
- Property-based testing harness for code verifier (generate cases, run in BOGVM).
- Science/hypothesis: evidence graphs with support accumulation.

### 2.5 Milestone Demo & Evaluation
- Verifiable agent demo: input a non-trivial problem (e.g., multi-step math proof, small coding task like "implement and verify gcd with properties", or logic puzzle).
  - Compiles via enhanced TSLC.
  - Waves for exploration/reasoning.
  - Verifiers (math/code) confirm.
  - Executes via BOGVM.
  - Full receipts + proof object.
- Eval on small "SWE-bench like" or math tasks (use existing benchmark_harness.py, formal_eval ideas).
- Compare reliability: agent either proves/executes correctly or abstains with explanation (no hallucination).

### 2.6 Polish & Next
- Config for verifier strictness.
- UI hooks (TS frontend for proof visualization).
- Self-audit of verifier (use existing self_audit).
- Prep for Phase 3 (massive intuition layer feeding better proposals to verifiers).

**Dependencies**:
- Phase 0/1: graph, waves, receipts, graph-native emergence, scale demo, unified adapters.
- Existing gold: reasoner/ts_reasoner/* (especially typed_support, proof_chain, support_path_verifier, ts_chat, central_brain, reasoning_channels, tamper_evident_runtime_ledger), core-vm/bogvm, knowledge packs.

**Risks**:
- Scope: Start narrow (expand math + simple code verifier + TSLC basics).
- BOGVM integration: It's already TS-native (has activation/tension/verifier_results), perfect match.
- Performance: Verifiers must be efficient or gated by tension.

**Timeline for this "start"**: Initial plan + core verifier unification stub + TSLC enhancement stub + runnable skill demo in 1 session.

## Implementation Start Log

(See code changes below in this interaction.)

**Immediate starts**:
- Unify a Verifier class that wraps existing support_path_verifier + typed + proof.
- Simple BOGVM plan executor stub.
- Enhanced demo using ts_chat for input, verifier for output claims, waves for "thinking", BOGVM for execution verification.
- Demo shows skill: solves a verifiable multi-step task transparently with receipts.

**Demo goal**: Something runnable that "thinks" (waves), "verifies" (proof + typed), "executes" (BOGVM), outputs receipt. E.g., a small logic/math problem where it proves a claim and "executes" a derived plan.

Next phases build on this for agentic power.

---

**Status after this start**: Phase 2 kicked off with plan + initial code + demo. Ready for deeper expansion.