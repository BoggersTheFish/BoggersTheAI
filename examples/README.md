# BoggersTheAI Examples

This folder contains small, runnable programs and a notebook that teach **BoggersTheAI** from the outside in: one-shot queries, autonomous background behavior, programmatic wave cycles, and interactive exploration.

---

## Prerequisites

1. **Python 3.10+**
2. **Install the package in editable mode** from the **`BoggersTheAI` directory** (where `pyproject.toml` lives):

   ```bash
   cd BoggersTheAI
   pip install -e .
   ```

3. **Ollama** (for LLM-backed answers): have the daemon running and pull the model named in `config.yaml` (for example `ollama pull llama3.2` if `inference.ollama.model` is `llama3.2`).

4. **Run examples from the `BoggersTheAI` project root** so paths like `config.yaml`, `traces/`, and the default graph locations resolve the same way as the CLI.

---

## Example files

### `quickstart.py`

The **simplest** end-to-end demo.

- Builds a **`BoggersRuntime`**, calls **`ask(...)`** once with a project-related question, and prints the **answer** and **hypotheses** list.
- **What it shows**
  - Basic API: construct runtime → `ask` → read fields on the response object.
  - The shape of **`QueryResponse`**: at minimum you get `answer` and `hypotheses`; the same type also carries **`confidence`**, **`reasoning_trace`**, topics, sufficiency metadata, and other fields useful for debugging or UI (see the main [README](../README.md) for the full field list).
- **Runtime**: typically **~2–5 seconds** per run when Ollama is warm; faster if LLM calls are disabled (see Tips).

```bash
python examples/quickstart.py
```

---

### `autonomous_demo.py`

Seeds the graph with a **few knowledge-seeking queries**, then **lets the runtime run idle** so you can watch **background behavior**.

- **What it shows**
  - **OS loop** behavior when the system is not actively answering you: exploration, consolidation, and insight modes (configured via `os_loop.autonomous_modes`).
  - **Background wave engine**: with `wave.enabled` and `wave.log_each_cycle` on, periodic wave cycles run while you wait.
  - **Tension and emergence in practice**: consolidation and insight paths log how tension and graph operations evolve over time.
- **What to watch**: log lines prefixed with **`OS Loop:`** (exploration, consolidation, nightly-style consolidation, insight) describe what the autonomous scheduler chose to do and key metrics (tension, prune/merge counts, etc.).

The script sleeps for **60 seconds** after seeding; adjust that duration in the source if you want a shorter or longer observation window.

```bash
python examples/autonomous_demo.py
```

---

### `graph_evolution_demo.py`

Builds a small **`UniversalLivingGraph`** in memory, **injects deliberately weak nodes and low-weight edges**, then runs **several programmatic wave cycles** via **`run_wave()`** from `BoggersTheAI.core.wave`.

- **What it shows (this script, directly)**
  - **Propagation**: activation spreads along edges (and can use semantic similarity when embeddings exist).
  - **Relaxation / tension**: `relax` combines local checks with the rules engine and runs **contradiction detection and resolution** when applicable.
  - **Break / evolve**: under sufficient total tension, the **weakest** high-tension pattern can **collapse**; the **`evolve`** step can **spawn a new node** from a collapsed parent (you will see `collapsed` and evolved counts in the printed **`WaveResult`** / history).
  - **Metrics**: before/after **`get_metrics()`** and a short **wave history** tail illustrate how the graph state moves across cycles.
- **Related behavior (full `BoggersRuntime` / background waves)**  
  The **living graph** used by **`BoggersRuntime`** also runs a richer **background wave loop** (elect → propagate → relax → **prune** weak edges/nodes → tension → **emergence** spawning). That path is easiest to observe in logs from **`autonomous_demo.py`** or normal CLI/TUI usage with waves enabled—not every step is duplicated inside this standalone `run_wave()` loop.

```bash
python examples/graph_evolution_demo.py
```

---

### `TS-OS_Living_Demo.ipynb`

A **Jupyter notebook** walkthrough for **interactive** exploration.

Suggested topics covered (run cells in order):

- Creating or loading a graph and **inspecting** nodes/edges/metrics.
- Running **queries** with different topics and comparing responses.
- Observing **wave-cycle** effects on the graph over time.
- Checking **conversation history** and session-related state.
- **Autonomous mode** hooks (how the runtime behaves when idle).
- High-level **self-improvement pipeline**: traces → dataset → optional fine-tuning (as configured).

**Best for**: learners who want to tweak parameters, re-run cells, and inspect objects in the REPL.

---

## Tips

| Tip | Why it helps |
|-----|----------------|
| **Keep Ollama running** | Default config uses local Ollama for synthesis; without it, behavior depends on fallbacks and may error or degrade. |
| **Faster demos without an LLM** | Set `inference.ollama.enabled: false` in `config.yaml` to avoid Ollama round-trips when you only care about graph/runtime mechanics. |
| **Wave speed** | Adjust `wave.interval_seconds` in `config.yaml` to make background cycles more or less frequent (lower = busier logs, more graph churn). |
| **Live graph metrics** | From the project root, use the CLI (**`graph stats`**) to inspect the current graph without writing code. |
| **Reasoning traces** | After **high-confidence** queries (see `inference.self_improvement.min_confidence_for_log`), trace JSONL files are written under **`traces/`** (path configurable via `inference.self_improvement.traces_dir`). |

---

## How examples connect to the main system

Every script here that uses **`BoggersRuntime`** is exercising the **same runtime** that backs the **CLI**, optional **TUI**, and **API/dashboard**: same **config loading**, **graph**, **query processor**, **wave settings**, and **OS loop** (subject to what you enable in code or `config.yaml`). The **`graph_evolution_demo.py`** uses the **graph and wave primitives** directly for a minimal, print-driven view of one slice of the pipeline.

Nothing in this folder is a “mock” of the product stack—it's either the real runtime or the same graph/wave code the runtime uses internally.

---

## Quick reference

| File | Entry style | Primary focus |
|------|----------------|---------------|
| [quickstart.py](quickstart.py) | `python examples/quickstart.py` | One `ask()`, response fields |
| [autonomous_demo.py](autonomous_demo.py) | `python examples/autonomous_demo.py` | Idle OS loop + background waves |
| [graph_evolution_demo.py](graph_evolution_demo.py) | `python examples/graph_evolution_demo.py` | `run_wave()` cycles on a toy graph |
| [TS-OS_Living_Demo.ipynb](TS-OS_Living_Demo.ipynb) | Jupyter | Interactive end-to-end tour |

For architecture depth, see [../README.md](../README.md) and [../ARCHITECTURE.md](../ARCHITECTURE.md). Release **v0.5.0+** adds a modular runtime (wave runner + mixins), shared HTTP client with retries, path sandboxing, extra tools (web search, datetime, unit convert), dashboard lazy loading, and `/health/live` / `/health/ready` — all documented in the main README.
