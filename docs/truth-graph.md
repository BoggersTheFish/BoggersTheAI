# Truth Graph — The Mechanics

This is where the trap closes.

If you have read [MANIFESTO.md](MANIFESTO.md) and
[anti-token-prediction.md](anti-token-prediction.md), you already accept that
next-token prediction cannot enforce global constraint satisfaction. This
document hands you the **exact mechanics** of what replaces it.

The Truth Graph is not a database. It is not a knowledge base. It is not a
vector store with edges drawn on top.

**The Truth Graph is a living computing medium** — a field where concepts hold
epistemological weight, relations exert mathematical force, and answers emerge
when the system finds a stable configuration.

You cannot "query" it like SQL. You **introduce energy** and wait for the wave
to settle.

---

## I. Nodes as Anchors

A node is not a row. A node is an **anchor** — a specific claim, concept, or
proposition that carries epistemological weight in the field.

Each node in the living graph (`core/graph/universal_living_graph.py`) carries:

| Field | Meaning |
|-------|---------|
| `activation` | Current wave amplitude — how much energy is flowing through this concept *right now* |
| `stability` | Resistance to perturbation — how entrenched this anchor is against revision |
| `base_strength` | Intrinsic weight before wave dynamics — prior importance |
| `topics` | Indexed clusters for fast topic-filed lookup |

A node with high activation is not "more true." It is **more hot** — more
energetically engaged in the current resolution. Truth is not a scalar on a
node. Truth is the **global configuration** the constraints permit.

In the reasoner layer, the Central Brain (`reasoner/ts_reasoner/central_brain.py`)
maintains typed nodes — candidates, repair targets, branch worlds, proof
boundaries — each with explicit status (`accepted`, `proposed`, `rejected`,
`quarantined`). A node enters the field only through verifier support. It does
not appear because a model sounded confident.

**Epistemological rule:** A node is a claim under tension, not a fact in storage.

---

## II. Edges as Constraints (Tensions)

An edge is not a relationship label. An edge is an **active mathematical
constraint** — a declaration of how one anchor restricts or supports another.

| Edge sign | Meaning |
|-----------|---------|
| **Positive** (+1) | Support, entailment, co-activation — these concepts must align |
| **Negative** (−1) | Contradiction, conflict — these concepts cannot both hold |

Each edge also carries:

- **Weight** — how strongly the constraint binds
- **Provenance weight** — how much to trust the source that asserted this constraint
- **Status** — whether typed verifier support has accepted this edge

In the spectral engine (`reasoner/ts_metacompute/spectral/laplacian.py`), edges
define the **signed Laplacian** — the matrix that governs how energy flows and
where contradictions create irreducible tension:

```
Energy = Σ_edges  w · (x_source − sign · x_target)²
```

Support edges want equal values. Conflict edges want opposite values. The graph
cannot satisfy all constraints simultaneously unless the configuration is
**consistent**. When it is not, tension is not a bug. It is **information**
— the system telling you the current state is impossible.

This is the opposite of token prediction, where contradictions are smoothed over
by the next fluent sentence. Here, contradictions **surface** and **block**
acceptance until resolved.

---

## III. Wave Propagation — The Engine

Reasoning in TS-OS is not a forward pass. It is **wave propagation**.

An input does not trigger token generation. It introduces **energy** into the
graph — a perturbation that disturbs the current field configuration. That
energy propagates through nodes and edges, triggering constraint resolutions
at every step.

The operational cycle (`core/graph/wave_runner.py`, `core/wave.py`):

```
Propagate → Relax → Prune → Merge → Detect Tension → Evolve
```

| Phase | What happens |
|-------|--------------|
| **Propagate** | Activation spreads along edges with decay — energy flows through the constraint network |
| **Relax** | Nodes settle toward local attractors — the field begins to find equilibrium |
| **Prune** | Weak connections below threshold are archived, not deleted — history is preserved |
| **Merge** | Redundant anchors consolidate — the field simplifies without losing structure |
| **Detect Tension** | Contradictions surface as high-tension pairs — the system names what cannot coexist |
| **Evolve** | Emergent structure spawns when stable configurations form and verifier support is typed |

The same rhythm runs at every layer:

- **Living graph** (`core/`) — continuous background wave thread
- **TensionLM** (`inference/tension_lm/`) — sigmoid tension fields per layer
- **BOGVM-0** (`core-vm/bogvm/vm.py`) — 16-opcode deterministic state machine
- **Central Brain** (`reasoner/ts_reasoner/central_brain.py`) — wave cycles over typed constraint graphs

The wave bridge (`reasoner/wave_bridge.py`) connects VM state snapshots to
spectral metacompute and cognitive physics substrates. Low-level machine states
become signed graphs. Signed graphs become Laplacian energy landscapes. Energy
landscapes become receipts.

---

## IV. State Stabilization — How the Graph "Thinks"

The graph does not "generate an answer." It **settles**.

Wave propagation continues until tensions resolve toward a configuration of
**lowest energy** — the state where the constraint network stops fighting
itself. That stable configuration *is* the answer.

This is not metaphor. It is implemented:

1. Energy is computed over the signed graph (`total_energy` in `laplacian.py`)
2. High-tension hotspots trigger repair proposals (`central_brain.run_wave_cycle`)
3. The cognitive physics engine (`cognitive_physics_engine.py`) runs zero-tension
   verifier gates before any output is accepted
4. Contradictions that cannot resolve are **quarantined**, not hallucinated over

```
The Lazy Universe Engine orchestrates substrates and emits an answer
only when a zero-tension, verifier-supported state forms.
```

If no such state exists, the correct output is **abstention** — not fluent
fabrication. That is the epistemological difference.

---

## V. The Three-Layer Stack

The Truth Graph is not one program. It is a **stack** of substrates, each
enforcing the same physics at a different resolution:

```
┌─────────────────────────────────────────────────────────────┐
│  interface/          Gateway — API, CLI, autonomous loop    │
├─────────────────────────────────────────────────────────────┤
│  core/               Living graph — wave cycle, synthesis    │
├─────────────────────────────────────────────────────────────┤
│  reasoner/           GOAT-TS — constraint resolution,      │
│                      spectral metacompute, verifier gates   │
├─────────────────────────────────────────────────────────────┤
│  inference/          TensionLM + TensionForge — neural      │
│                      tension fields (proposals, not verdicts)│
├─────────────────────────────────────────────────────────────┤
│  core-vm/            BOGVM-0 — deterministic 16-opcode VM   │
│                      (bedrock — same input, same state)     │
└─────────────────────────────────────────────────────────────┘
```

Data crosses layer boundaries **only** through `.bogpk` artifacts
(`shared/artifacts/bogpk.py`). No layer whispers state to another through
unlogged side channels. If it happened, there is a receipt.

---

## VI. External Graph Stores (Persistence, Not Truth)

The reasoner hooks (`reasoner/hooks/`) connect the Truth Graph to external
infrastructure for scale — not for authority:

| Store | Role |
|-------|------|
| **NebulaGraph** | Persistent constraint-graph storage |
| **Redis** | Hot activation cache and receipt indexing |
| **Spark** | Batch ingestion for large-scale metacompute |

These are **substrates**. They store and retrieve. They do not decide. Typed
verifier support remains the proof boundary regardless of where the graph is
hosted.

---

## VII. The Receipt — `.bogpk`

Every resolution path can be frozen, hashed, and exported.

Because wave propagation in BOGVM-0 is governed by a **deterministic
instruction set** (16 opcodes, fixed-point wave-state semantics), the entire
resolution trace can be:

1. **Executed** — same program, same input, same final state
2. **Logged** — VM receipt ledger with per-opcode events
3. **Packed** — highly compressed `.bogpk` binary container per `BOGPK_SPEC.md`
4. **Verified** — SHA-256 reconstruction proof

```python
from shared.artifacts import serialize_json_payload, ArtifactKind

serialize_json_payload(
    {"nodes": [...], "edges": [...], "cycle": "propagate"},
    "artifacts/core-vm/wave_snapshot_001",
    kind=ArtifactKind.WAVE_SNAPSHOT,
)
```

Artifact kinds across layers:

| Kind | Layer | What it freezes |
|------|-------|-----------------|
| `vm_state` | `core-vm/` | BOGVM opcode transitions |
| `tension_field` | `inference/` | TensionLM / TensionForge field output |
| `reasoner_receipt` | `reasoner/` | Verifier-gated resolution receipts |
| `wave_snapshot` | Any | Full graph state at a cycle boundary |

**Perfect reproducibility is not a feature. It is the minimum bar for calling
something reasoning instead of guessing.**

The container is a reconstruction blueprint. The VM and verifier are proof
authority. The receipt is the contract.

---

## VIII. Cognitive Physics Substrates (Bounded Simulators)

The Verse Engine (`reasoner/ts_reasoner/cognitive_physics_engine.py`) composes
deterministic simulator substrates over the Truth Graph:

| Substrate | Function |
|-----------|----------|
| `Photonic_State_Ledger` | Graph state as deterministic frequency slots |
| `ContradictionFirewall_as_interference_grating` | Constructive/destructive interference over support/conflict edges |
| `Retrocausal_Fuzzer` | Late-contradiction probes |
| `Temporal_Tension_Bridge` | Back-propagated tension into earlier assumptions |
| `Spectral_Coupling_Telepathy` | Constraint-shape telemetry across nodes (no answer packets) |
| `Unified_Field_Kernel` | Zero-tension verifier gate |
| `The_Lazy_Universe_Engine` | Full-stack orchestrator — answer only at zero tension |

These are **simulator contracts**. They are inspectable, auditable, and bounded.
They are not claims of literal photonic hardware, physical retrocausality, or
telepathy. They are the mechanical vocabulary for describing how constraint
fields behave when you take the physics seriously.

---

## IX. You Cannot Use This Without Believing It

That is the point.

If you treat the Truth Graph as a fancy database, you will build a fancy database
and wonder why it does not reason. If you treat edges as labels, you will get
labels and no constraints. If you treat wave propagation as a metaphor, you will
get a batch job and no stabilization.

The graph thinks by **settling**. The VM proves it settled the same way every
time. The receipt proves you watched.

Read [bogpk-pipeline.md](bogpk-pipeline.md) for the serialization contract.
Read [directory-structure.md](directory-structure.md) for where each substrate
lives. Run the demo:

```bash
python reasoner/hooks/run_reasoning_demo.py
```

Watch the central brain pass constraint matrices to spectral metacompute. Watch
the wave virtualization receipt land as `.bogpk`. Watch the gates pass — or
don't, which is also a result.

---

*The Truth Graph is not where you store what you know. It is where knowing happens.*