# TS-OS Directory Structure — The Logic Map

Strict hierarchical layout reflecting how the system actually computes.

```
BoggersTheAI/
├── core-vm/              # Bedrock: BOGVM-0 (16-opcode wave-state VM)
│   ├── bogvm/            # VM implementation (opcodes, container, archive)
│   ├── spec/             # BOGPK-0.1 specification
│   ├── schemas/          # JSON schemas for container validation
│   └── artifact_log.py   # VM state → .bogpk logging
│
├── inference/            # Neural execution layer
│   ├── tension_lm/       # TensionLM (CausalTensionGraphs, from bozo)
│   ├── tension_forge/    # OpenCL runtime for tension-field GPU execution
│   └── artifact_export.py
│
├── reasoner/             # Constraint resolution layer
│   ├── ts_reasoner/      # GOAT-TS engine, Verse Engine, verifier gates
│   ├── ts_metacompute/   # Spectral metacompute substrates
│   ├── hooks/            # NebulaGraph, Redis, Spark connectors
│   └── artifact_receipts.py
│
├── shared/
│   └── artifacts/        # Unified .bogpk serialization API
│
├── core/                 # Living graph runtime (wave, query, synthesis)
├── interface/            # CLI, API, autonomous loop
├── entities/             # Ingestion, consolidation, simulation
├── docs/                 # Unified manifesto and cognitive physics docs
└── ...
```

## Computation Flow

```
Input → core-vm (deterministic VM state)
      → inference (tension fields via TensionLM/TensionForge)
      → reasoner (GOAT-TS constraint resolution + verifier gates)
      → .bogpk artifact trail at every boundary
      → core/ (living graph integration)
      → interface/ (user-facing synthesis)
```

## Migration Map (Archived Satellites)

| Former Repo | Monorepo Path |
|-------------|---------------|
| bogbin | `core-vm/bogvm/` |
| bozo | `inference/tension_lm/` |
| BoggersTheLLM | `inference/` (substrate patterns) |
| TS-Reasoner-v0 | `reasoner/ts_reasoner/` |
| BoggersTheMind | `core/`, `interface/`, `entities/`, `mind/` |
| GOAT-TS | `reasoner/hooks/` + `reasoner/ts_reasoner/` |