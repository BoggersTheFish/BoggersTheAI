# Truth Graph Mechanics

The Truth Graph is the living constraint network at the heart of TS-OS. It is
not a knowledge base in the traditional sense — it is a **dynamic field** where
concepts are nodes, relations are edges, and truth emerges from the most stable
configuration the constraints allow.

## Node Semantics

Each node carries:

| Field | Meaning |
|-------|---------|
| `activation` | Current wave amplitude — how "hot" this concept is |
| `stability` | Resistance to perturbation — higher = more entrenched |
| `base_strength` | Intrinsic importance before wave dynamics |
| `topics` | Indexed clusters for fast topic-filed lookup |

## Edge Semantics

Edges encode typed relations with signed support:

- **Positive edges** — support, entailment, co-activation
- **Negative edges** — contradiction, conflict, tension
- **Provenance weight** — how much to trust this edge's source

## The Wave Cycle

```
Propagate → Relax → Prune → Merge → Detect Tension → Evolve
```

1. **Propagate** — activation spreads along edges with decay
2. **Relax** — nodes settle toward local attractors
3. **Prune** — weak edges below threshold are archived (not deleted)
4. **Merge** — similar nodes consolidate to reduce redundancy
5. **Detect Tension** — contradictions surface as high-tension pairs
6. **Evolve** — emergent nodes spawn when stable configurations form

## GOAT-TS Integration

The reasoner layer (`reasoner/`) connects GOAT-TS constraint resolution to
external graph stores:

- **NebulaGraph** — persistent constraint-graph storage
- **Redis** — hot activation cache and receipt indexing
- **Spark** — batch ingestion for large-scale metacompute

All graph mutations require typed verifier support before acceptance.

## Verse Engine (Cognitive Physics)

The Verse Engine (`reasoner/ts_reasoner/cognitive_physics_engine.py`) orchestrates
deterministic simulator substrates:

- `Photonic_State_Ledger` — frequency-slot graph state
- `ContradictionFirewall_as_interference_grating` — wave interference over edges
- `Retrocausal_Fuzzer` — late-contradiction probes
- `Temporal_Tension_Bridge` — back-propagated tension
- `Spectral_Coupling_Telepathy` — constraint-shape telemetry (no answer packets)
- `Unified_Field_Kernel` — zero-tension verifier gate
- `The_Lazy_Universe_Engine` — full-stack orchestrator

These are **simulator contracts**, not hardware claims.

## Artifact Trail

Every graph state transition logs through `.bogpk`:

```python
from shared.artifacts import serialize_json_payload, ArtifactKind

serialize_json_payload(
    {"nodes": [...], "edges": [...], "cycle": "propagate"},
    "artifacts/core-vm/wave_snapshot_001",
    kind=ArtifactKind.WAVE_SNAPSHOT,
)
```