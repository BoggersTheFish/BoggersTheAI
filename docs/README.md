# BoggersTheAI Documentation — TS Engine Focus

**Current focus (2026-06)**: TS Engine (core/ts_engine.py + verifier/language/intuition) for verifiable reasoning. Graph + waves + tension + VerifierOS + BOGVM + TSLC. TensionLM *only* for synthesis from verified state. 

Fast factual paths (light: 2 waves, 0 BOGVM, direct graph). Full formal pipeline produces BOGVM traces for self-data. Self-data injection + math/proof boosts + proof prompts so self-data surfaces in reasoning. 

See root README.md, COGNITIVE_PHYSICS_ROADMAP.md (progress), ARCHITECTURE.md, CHANGELOG.md.

**Not full traditional LLM**. TS mechanisms = intelligence (verifiable, receipts, on-device). Generator for fluent output only.

---

## Key Docs (updated)

- [COGNITIVE_PHYSICS_ROADMAP](../experiments/frontier/COGNITIVE_PHYSICS_ROADMAP.md) — plan + status (Wave 0 done, loop active)
- [WAVE0_SPRINT_PLAN](../experiments/frontier/WAVE0_SPRINT_PLAN.md)
- [ARCHITECTURE](../ARCHITECTURE.md)
- [CHANGELOG](../CHANGELOG.md)
- [MANIFESTO.md](MANIFESTO.md) (ideology)
- [truth-graph.md](truth-graph.md)
- [directory-structure.md](directory-structure.md)

Full monorepo history in other .md; focus here on TS engine + self-data. 

See probes in experiments/frontier/ and gpt55_progress_demo.py for current behavior (factual light; formal + self-data feedback).
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