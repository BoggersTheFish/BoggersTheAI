# TS-OS Documentation — The Trojan Horse

Developers come for the code. To use it, they must learn the epistemological
rulebook. These documents are not supplementary. They are the interface to the
physics.

**Read in this order. Do not skip.**

---

## The Ideological Stack

| # | Document | Role |
|---|----------|------|
| 1 | **[MANIFESTO.md](MANIFESTO.md)** | The front door — axioms of cognitive physics, rejection of the black box, open-source mandate |
| 2 | **[anti-token-prediction.md](anti-token-prediction.md)** | The weapon — systematic deconstruction of softmax and next-token prediction |
| 3 | **[truth-graph.md](truth-graph.md)** | The payload — exact mechanics of the living computing medium |
| 4 | **[bogpk-pipeline.md](bogpk-pipeline.md)** | The receipt — how resolution paths are frozen, hashed, and exported |
| 5 | **[directory-structure.md](directory-structure.md)** | The map — where each substrate lives in the monorepo |

If you read only the API docs, you will build a wrapper around statistical
fluency and call it reasoning. The stack above exists to make that impossible.

---

## Infrastructure & Reference

| Document | Contents |
|----------|----------|
| [bogpk-pipeline.md](bogpk-pipeline.md) | `.bogpk` serialization contract across all layers |
| [directory-structure.md](directory-structure.md) | `core-vm/`, `inference/`, `reasoner/` logic map |
| [METRICS_TODO.md](METRICS_TODO.md) | Benchmark artifacts before publishing performance claims |
| [templates/ARCHIVE_README.md](templates/ARCHIVE_README.md) | Satellite repo redirect template |

---

## Layer → Code Map

| Layer | Monorepo path | Archived from |
|-------|---------------|---------------|
| BOGVM-0 bedrock | `core-vm/bogvm/` | bogbin |
| TensionLM | `inference/tension_lm/` | bozo |
| TensionForge OpenCL | `inference/tension_forge/` | TensionForge |
| GOAT-TS / Verse Engine | `reasoner/ts_reasoner/` | TS-Reasoner-v0 |
| Living graph runtime | `core/`, `interface/` | BoggersTheMind |
| Language substrate | `inference/` patterns | BoggersTheLLM |
| Artifact pipeline | `shared/artifacts/` | unified (new) |
| Wave bridge | `reasoner/wave_bridge.py` | unified (new) |

---

## Quick Verification

After reading the ideological stack, prove you understood it:

```bash
# Full test suite (232 tests)
pytest tests/

# Wave virtualization demo
python reasoner/hooks/run_reasoning_demo.py

# TensionForge benchmark
python inference/tension_lm/train.py --benchmark-forge
```

If the demo produces a `.bogpk` receipt with `all_gates_passed: true`, the
graph settled. If it does not, that is also a valid result — abstention beats
hallucination.

---

*You cannot use this code without changing how you define reasoning. That is the design.*