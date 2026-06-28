# Phase 0: Foundation & Unification — Detailed Remainder Plan & Implementation Log

**Status**: Started (initial spike complete). This document fully plans the *remainder* of Phase 0 and tracks implementation.

**Overall Phase 0 Goal** (from FRONTIER_PLAN.md):
Build the foundation so that advanced TS reasoning (verifier-first, deterministic chains, common-ground, central brain ledger) becomes first-class with the living graph + wave physics. Eliminate default LLM crutch for core reasoning/emergence. Establish baselines. Achieve "Hello Frontier" milestone.

**Milestone Definition**:
- Runnable end-to-end demo on non-trivial formal reasoning problem (chains, contradictions, queries).
- Uses ts_reasoner primitives (proof_chain, typed support, elements of ts_chat/common_ground/central_brain) + core waves/rules.
- Produces complete glass-box receipt (wave steps, verifier decisions, hashes).
- **No external LLM** used in the core path (graph-native emergence + deterministic logic).
- Runs cleanly from the monorepo.
- Perf numbers and cleanup notes recorded.

**Duration target**: Remainder of Phase 0 ~ 2-4 weeks of focused work here (aggressive, on-device).

---

## Subtask Breakdown (Prioritized Order)

### P0.1: Detailed Audit & Mapping (1-2 days) — IN PROGRESS / COMPLETE FOR REMAINDER
- Map exact integration points (already partially done).
- Identify all LLM usages in core reasoning path.
- Inventory duplicates in workspace/.
- Measure current limits (graph size, wave perf).
- Read key files: ts_chat full flow, central_brain, reasoning_channels, support_path_verifier, runtime integration points.

**Findings (summary)**:
- ts_reasoner/ is rich but mostly isolated (internal imports only).
- LLM dependency: primarily `evolve_fn` for emergent node *content* (in rules_engine + universal_living_graph + wave).
- Main runtime wires `local_llm.synthesize_evolved_content` via `_setup_evolve_fn`.
- Receipts: advanced in ts_reasoner (TamperEvidentRuntimeLedger, firewall_receipt, central_brain receipts), weak in core (mostly logs + snapshots).
- ts_chat: excellent deterministic "no LLM" chat loop with premises, repair, common ground.
- Duplicates: workspace/ has many historical (BAGI, GOAT-TS*, TS-Reasoner-v0 copy, BoggersTheCIG*, etc.). Monorepo itself claims unification.
- Perf: Conservative constants (EMERGENCE_MAX_SPAWN=2), pure Python graph ops.

**Actions**:
- Document in this file.
- Create perf baseline script.
- Plan unification module: `core/reasoning/unified_ts_reasoner.py` or adapters.

### P0.2: Workspace & Repo Hygiene / Cleanup (2-3 days)
- In workspace/ root: create `archive/` or `history/` .
- Move or symlink obvious historical full copies:
  - BAGI/ → history/
  - GOAT-TS* variants (except any small useful) 
  - TS-Reasoner-v0/ (the workspace copy)
  - BoggersTheCIG*, BoggersTheCIG_v2
  - Other old like TS-Core, GOAT-OS etc. if not referenced.
- In BoggersTheAI/ itself: ensure reasoner/ and core/ have clear pointers.
- Add README in history/ explaining "these are preserved lineage; active development in BoggersTheAI/".
- Update .gitignore if needed, docs.

**Milestone**: `ls workspace/history/` shows moved dirs, main workspace/ is cleaner, monorepo has no confusion.

### P0.3: Hardening — Determinism, Receipts, Config (3-5 days)
- Make EMERGENCE_MAX_SPAWN and other rules params fully configurable (already somewhat in wave settings; extend).
- Add `deterministic_mode` flag: forces ordered iteration (sort keys), no hidden random, seedable.
- Implement basic receipt system in core:
  - WaveStepReceipt (step, tensions, pruned, emergent, hashes).
  - GraphDeltaReceipt.
  - Use stable_hash from ts_reasoner style.
  - Integrate into UniversalLivingGraph and WaveCycleRunner (log or return with cycles).
- Centralize receipt writing (perhaps reuse or adapter to ts_reasoner tamper_evident).
- Add to config.yaml: `reasoning.strict_determinism: true`, `emergence.max_spawn: 5`, `emergence.use_llm: false`.

**Milestone**: Any wave run can output a verifiable receipt bundle with hashes. Re-running same input + seed produces identical hashes.

### P0.4: Scale Primitives — Emergence & Graph-Native Content (4-7 days, core of "remove LLM")
- Bump default EMERGENCE_MAX_SPAWN to 5 (or config 8 for frontier).
- Implement `graph_native_evolve(source_content, neighbor_contents, topics)` pure function:
  - Templates: "Synthesis of {topics}: {src} implies {combined preds}".
  - Use proof_chain style transitivity if relations present.
  - Simple abstraction: find common patterns.
  - Fall back to content concatenation with stability note.
- Wire it: in rules_engine, if no evolve_fn or in frontier mode, use graph_native.
- Add tension-based content quality (higher tension -> more "novel" phrasing).
- Optional: small pure-Python stub for Tension proposer for content (use patterns from bozo or simple).
- Update autonomous_loop, wave_runner, tests to support graph-native.

**Milestone**: Emergence creates useful, verifiable new nodes without calling LLM. Demo shows "Emerged: All whales are mortal" from chain facts.

### P0.5: Unification Implementation (biggest, 7-10 days)
Create integration layer without breaking existing:

- New dir: `core/reasoning/` (or `reasoner/` at top if better, but keep existing reasoner/ for advanced).
  - `unified_verifier.py`: adapter that uses TypedSupportObject + simple support_path.
  - `proof_integration.py`: expose universal_bridge_path as a graph operation / reasoning primitive.
  - `ts_chat_adapter.py`: thin wrapper to compile text -> graph deltas using ts_chat ideas (common_ground, premises) without full runtime deps.
  - `central_brain_adapter.py`: optional persistent ledger for main graph updates (use when enabled).
- Modify `UniversalLivingGraph` or add `ReasoningEngine` mixin/class that can:
  - Accept "proposals" from ts_chat style.
  - Run verifier (typed + proof_chain) before/after wave updates.
  - Record CentralBrain-style receipts.
- In interface/runtime or a new `frontier_runtime.py`: option for "ts_reasoner_mode".
- Make reasoning_channels pluggable for future (start with logic_transitivity).

**Key Integration Points**:
- After compiler-like step: use ts_chat premise extraction → create nodes/edges as proposals.
- In rules cycle or after: run proof_chain on is_a chains.
- Use TypedSupport for any derived claim.
- On acceptance: update graph + emit hashed receipt.

**Milestone**: Code in core can do end-to-end "assert facts with ts_chat logic → waves → proof verification" using the real modules.

### P0.6: Perf Baseline & Profiling (parallel, 2-3 days)
- New: `experiments/frontier/perf_baseline.py`
  - Generate graphs of increasing size (synthetic chains, random).
  - Time: add 1000 nodes, full wave cycle (propagate+relax+rules), tension detect, emergence.
  - Measure memory (sys, or tracemalloc).
  - Vary EMERGENCE_MAX_SPAWN, wave steps.
  - Output JSON + simple plots (text or matplotlib if avail).
- Run and save to artifacts/baseline_phase0.json.
- Identify quick wins (e.g. adjacency dicts, caching).

**Milestone**: Documented numbers, e.g. "10k nodes: X ms per wave on this hardware".

### P0.7: "Hello Frontier" End-to-End Milestone Demo (final, 3-5 days)
- Build `experiments/frontier/hello_frontier.py` (evolve the existing spike).
  - Input: complex formal scenario (e.g. transitivity chain + contradiction + query like "All A are B, B are C, C are D. Is A D? Also: No D are E.").
  - Use: simplified or real ts_chat premise extraction (or hardcode for demo) + graph.
  - Run waves with graph-native emergence + increased spawn.
  - Apply proof_chain for the query.
  - Use TypedSupport + simple verifier.
  - Optional: minimal central brain receipt.
  - Output: full printed receipt + "success: verified transitive answer with waves".
  - Assert no LLM calls in core path (mock or check).
- Make it the canonical "Phase 0 complete" demo.
- Add to README or FRONTIER_PLAN.

**Milestone**: `python experiments/frontier/hello_frontier.py` prints beautiful glass-box trace and says "VERIFIED" for a non-trivial problem.

### P0.8: Polish, Docs, Tests (2 days)
- Add tests for new graph-native evolve, receipt hashing, unification adapters.
- Update ARCHITECTURE.md, CHANGELOG.md, BoggersTheAI/README with Phase 0 notes.
- Update FRONTIER_PLAN.md with "Phase 0 status: COMPLETE (date)".
- Minor: fix any broken imports surfaced.
- Optional: small TS frontend note or viz hook for receipts.

**Overall Phase 0 Exit Criteria**:
- All subtasks above done or explicitly deferred with note.
- Clean `git status` or documented changes.
- "Hello Frontier" demo passes and is impressive (glass box, correct deterministic reasoning, waves doing work).
- No regression on existing tests (run pytest on core/reasoner areas).
- Plan for Phase 1 ready (or next items queued).

---

## Implementation Log (Live)

### Completed So Far (before this doc)
- Initial spike in experiments/frontier/phase0_unification_spike.py (proof_chain + typed + waves).
- FRONTIER_PLAN.md created.
- Basic audit.

### Now Executing (this session):
[Will fill as we code using tools]

Priorities in this response:
1. Write this detailed plan file (done).
2. Start P0.4 (graph-native emergence) + bump spawn.
3. Implement basic receipt in core.
4. Create perf baseline script and run it.
5. Build improved Hello Frontier demo using more real pieces.
6. Document cleanup plan + do light moves if safe.
7. Unification: create the adapter files.

Risks for Phase 0:
- Import hell in monorepo (use adapters, avoid full import of heavy ts_reasoner into core until cleaned).
- Over-scoping: keep unification "thin adapters + examples" rather than full refactor.
- Time: focus on runnable milestone over perfect.

Next: implement via edits.