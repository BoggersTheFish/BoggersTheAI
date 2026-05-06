# BoggersTheAI — TS-OS (Thinking System Operating System)

**A local-first, living cognitive runtime.**

Instead of a static LLM, BoggersTheAI runs a **continuous wave-propagation graph** where concepts are nodes with activation/stability, and thoughts emerge from constraint resolution and wave dynamics.

The graph is alive in the background — propagating, relaxing, pruning, resolving tensions, and spawning emergent structure — while remaining fully observable and controllable.

**Local. Self-improving. Multimodal. No cloud required.**

---

## Quick Start

```bash
git clone https://github.com/BoggersTheFish/BoggersTheAI.git
cd BoggersTheAI

pip install -e ".[all]"

# Start Ollama + recommended models
ollama pull llama3.2
ollama pull nomic-embed-text

# Launch the CLI
boggers
```

Type `help` in the prompt for commands.

Launch the web dashboard:
```bash
dashboard-start
```

---

## Core Philosophy

> **Thought is not token prediction. Thought is the stable configuration of constraints under wave propagation.**

The system maintains a living graph that evolves continuously through cycles of:

**Propagate → Relax → Prune → Merge → Detect Tension → Evolve**

LLMs are used only as a synthesis tool when needed. The real intelligence lives in the graph dynamics.

---

## Key Features

- **Living Wave Graph** with continuous background evolution
- **Self-Improvement** via trace → QLoRA fine-tuning + hot-swap
- **Multimodal** (voice in/out, image understanding)
- **Rich observability** — CLI, TUI, and beautiful FastAPI dashboard with live graph viz
- **Tool use + external adapters** (web, RSS, Wikipedia, etc.)
- **Thread-safe** with proper mode locking between user queries and autonomous cycles

---

## Part of the TS Ecosystem

- **BoggersTheCIG** — Self-evolving epistemic knowledge graph engine
- **TS-Core** — Lightweight graph dynamics kernel (Python + Rust acceleration)
- **GOAT-TS** — Theoretical foundation
- **TensionLM / bozo** — Experimental models using tension graphs

---

## Next Steps

- Run your first queries in the CLI
- Explore the live graph in the dashboard (`/graph/viz`)
- Watch the wave cycle in real time
- Trigger self-improvement with `improve` command

Full technical deep-dive and configuration reference is preserved in the [previous long README version](https://github.com/BoggersTheFish/BoggersTheAI/commits/main/README.md) while we iterate on clarity.

---

**Status**: Actively developing (v0.5+ wave)

**License**: MIT
