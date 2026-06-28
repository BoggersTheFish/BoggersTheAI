# Phase 1: Scale the Graph + Dynamics — Detailed Plan & Implementation

**From FRONTIER_PLAN.md (Phase 1 excerpt):**
- Large-graph support: Hierarchical nodes (clusters/subgraphs as first-class), sparse activation, on-disk + in-memory hybrid, embedding ANN for fast semantic prop.
- Accelerated waves: Implement vectorized propagate/relax/tension (Torch or custom) + keep pure Python fallback. Port/integrate TensionForge ops.
- Richer structures: First-class node payloads (SymPy exprs for math, AST for code, plan graphs).
- Better emergence & split/merge: Domain-specific (math, code), use tension *fields* and spectral methods from cognitive_physics_engine. Target 10-100x more emergent power.
- Adaptive compute: Full TSQ-style — tension and verifier failure drive deeper/more precise waves or sub-simulations.
- **Milestone**: 50k+ node graphs with coherent multi-step reasoning on held-out formal + coding tasks; measurable emergence of novel correct structures.

**Overall Phase 1 Goal**:
Take the Phase 0 foundation (graph + waves + graph-native emergence + receipts + verifier primitives) and scale the *dynamics* to support much larger state spaces while keeping everything deterministic, glass-box, and on-device. Focus on performance, structure, and smarter control so the system can handle non-trivial reasoning chains without collapsing under scale or time.

**Duration target**: 2-4 weeks focused iteration here (aggressive local work). Not full 2-4 months.

**Success Criteria for Milestone**:
- Can build and run waves on 5k-50k node graphs in reasonable time (<10s for several cycles on this hardware).
- Coherent multi-hop reasoning works (e.g. chains of 10+ facts resolve correctly via proof + waves).
- Emergence produces measurably more "useful" nodes (e.g. via verifier acceptance or tension reduction).
- Adaptive depth: high-tension areas get more compute automatically.
- Full receipts for all operations.
- Demo that is impressive and runnable.
- No breakage of determinism or existing Phase 0 behavior.
- Pure Python fallback always works; numpy acceleration when available.

**Key Constraints (stay true to TS)**:
- Everything must remain glass-box (receipts, traces, inspectable state).
- Deterministic (ordered ops, no hidden randomness unless seeded and logged).
- On-device / no cloud required.
- Verifier authority preserved (waves propose/settle, verifiers decide).
- Leverage existing: wave_propagation, rules_engine, receipts, tension_forge ideas, cognitive_physics_engine spectral, sqlite_backend.

---

## Subtask Breakdown (Prioritized, Parallelizable where noted)

### P1.1: Audit & Baseline Extension (1 day)
- Profile current limits more deeply (use/extend perf_baseline.py on real graph up to memory limit).
- Identify bottlenecks: dict overhead in adjacency, Python loops in propagate, embedding cosine calls, full graph scans.
- Check integration points: how current run_wave_cycle, autonomous_loop use the graph.
- Inventory richer payload ideas from reasoner (e.g. from proof_object_examples, learned_model).
- Decide on numpy vs torch for vectorized (numpy is lighter, torch available per env checks).

**Actions**:
- Run extended perf on current code.
- Document findings in this file.
- Choose: numpy for vectorized core (universal fallback).

### P1.2: Large-Graph Support - Core Optimizations (3-5 days)
- Optimize UniversalLivingGraph:
  - Use numpy arrays for activations, base_strengths, stabilities (parallel to dicts for nodes).
  - Sparse adjacency: use scipy.sparse if avail, or simple dict-of-lists + batching; fallback dict.
  - Lazy/ incremental updates: only process dirty nodes in waves.
  - On-disk hybrid: improve sqlite_backend usage for nodes > RAM; add simple paging for embeddings.
- Hierarchical nodes:
  - Add "cluster" or "subgraph" nodes.
  - Nodes can have `parent_cluster` or `is_cluster`.
  - Waves can operate at cluster level (summary propagation) then drill down.
  - Simple impl: add attributes, helper methods like `get_subgraph`, `propagate_to_cluster`.
- Embedding ANN: for semantic prop, add simple brute-force top-k with numpy, or note future faiss/hnsw (keep pure for now).
- Guardrails: raise max_nodes safety, add config for target scale.

**Milestone for this subtask**: Can instantiate 20k node graph, run 10 wave cycles without OOM or >5s.

### P1.3: Accelerated / Vectorized Waves (4-6 days, core of Phase 1)
- Create `wave_propagation_vectorized.py` (numpy-based versions of propagate, relax, detect_tensions, normalise).
  - Use numpy arrays for bulk ops.
  - Keep semantic (cosine) vectorized where possible.
  - Pure Python fallback in wave_propagation.py if no numpy.
- Integrate:
  - In UniversalLivingGraph.propagate/relax: option for vectorized=True (default in frontier mode).
  - Update run_wave_cycle to use vectorized path.
- Port ideas from TensionForge: simple tension ops if applicable (but keep wave semantics).
- Benchmark: compare vectorized vs pure on 1k/10k nodes.

**Milestone**: 5-10x speedup on wave cycles for medium graphs. Measurable in perf_baseline.

### P1.4: Richer Node Structures & Payloads (3-4 days)
- Extend Node/GraphNode (in node.py and universal):
  - Add optional `payload: dict | None` (for structured data).
  - Typed payloads: e.g. support "math_expr", "code_ast", "plan_step", "hypothesis" via simple registry.
  - Update add_node, serialization, wave ops to respect payloads (e.g. emergence can copy/merge payloads).
- Basic examples:
  - In demo: nodes with "relation_strength" or simple metadata.
- Update receipts to include payload summaries.
- Hook for future: allow BOGVM execution on "executable" payload nodes.

**Milestone**: Nodes can carry extra data, emergence preserves it, queries can filter on payload type.

### P1.5: Better Emergence, Split/Merge & Spectral (3-5 days)
- Enhance rules_engine.py and graph_native_evolve:
  - Use tension *fields* (not just scalar): e.g. per-topic or per-neighbor tension.
  - Integrate spectral ideas: from reasoner/ts_reasoner/cognitive_physics_engine or ts_metacompute/spectral (laplacian for clusters?).
  - Domain-specific: simple hooks for "logic" vs "fact" nodes.
  - More powerful emergence: generate 5-10x nodes, use neighbor relations for richer content (build on proof_chain transitivity for "implied" nodes).
  - Improve split/merge: use payload similarity, activation + tension.
- Target: emergence that reduces overall graph tension measurably.

**Milestone**: In large graph, emergence produces nodes that participate in later successful proofs/chains.

### P1.6: Adaptive Compute (TSQ-style) (2-3 days)
- In wave_runner.py or UniversalLivingGraph:
  - Add `run_adaptive_waves(max_steps=20, tension_target=0.1)` :
    - Run waves in batches.
    - High-tension subgraphs get extra cycles (or targeted propagate only on high-t nodes).
    - Verifier failure (if integrated) escalates depth.
  - Config: `wave.adaptive: true`, `tension_escalation_factor`.
- Tie to receipts: log "adaptive_depth" per step.

**Milestone**: Hard problems (high tension or contradictions) automatically get 2-3x more compute; easy ones converge fast.

### P1.7: Phase 1 Milestone Demo & Evaluation (3 days)
- Create/enhance `experiments/frontier/phase1_scale_demo.py`:
  - Generate large synthetic graphs (5k-20k nodes, long chains + some branches + contradictions).
  - Run with/without vectorized + adaptive.
  - Perform multi-step queries (use proof_chain on resulting stable graph).
  - Show: time, final tension, #emergent useful nodes (e.g. those enabling new proofs), sample full receipt.
  - Bonus: simple "coding" task sim (nodes as "requirements", emergence as "plan steps").
- Extend perf_baseline to Phase 1 metrics.
- Verify glass-box: receipts contain everything needed to replay "why" a conclusion was reached.
- Update skill_demo or add new runnable that shows "50x scale with coherent reasoning".

**Milestone**: Demo runs, prints impressive numbers + traces, proves scaling + better emergence vs Phase 0 baseline.

### P1.8: Polish, Integration, Docs (ongoing)
- Wire new features into runtime/config (use existing graph_native_primary as base).
- Ensure no regression on small graphs / Phase 0 demos.
- Add tests or verification in experiments.
- Update FRONTIER_PLAN.md status, ARCHITECTURE.md, CHANGELOG.md.
- Optional: simple hook to reasoner spectral for emergence.
- Prepare for Phase 2 (verifiers).

**Risks & Mitigations**:
- Performance still Python-bound: numpy vectorized + sparse will help a lot for this phase.
- Complexity explosion in hierarchical: start simple (cluster attrs + summary waves).
- Breaking determinism: all new paths must be seedable/ordered; test re-runs produce same receipts.
- Scope creep: stick to "scale the dynamics" not full verifiers yet.

**Dependencies on prior**:
- Phase 0 graph_native, receipts, prefer flag.
- Existing sqlite, embeddings, rules_engine.

**Order**: P1.1 -> P1.2/P1.3 (parallel) -> P1.4/P1.5 -> P1.6 -> P1.7 -> P1.8

---

## Implementation Notes & Log

This document will be updated as we implement (like PHASE0).

Start by extending the perf baseline and graph for scale, then vectorize the propagation functions (they are the hot path).

Leverage:
- numpy (confirmed available)
- TensionForge concepts for ops (but wave is different from training)
- cognitive_physics_engine for spectral inspiration (read later if needed)

End state after Phase 1: The core "engine" is ready for 10k+ node coherent operation, setting up richer reasoning in later phases.

---

**Next steps after this plan doc**: Implement vectorized propagation first (high impact), then hierarchical basics, then the demo. Use search_replace for edits, write new files in experiments/frontier/ and core/graph/.

All changes must preserve:
- Determinism
- Glass box (update receipts)
- On-device purity
- Verifier-first philosophy (waves settle, don't decide)