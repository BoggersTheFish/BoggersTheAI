# Examples

Run these from the **`BoggersTheAI` project root** (where `pyproject.toml` lives), with the package installed (`pip install -e .`).

| File | What it does |
|------|----------------|
| [quickstart.py](quickstart.py) | Minimal script: one `BoggersRuntime().ask(...)` and prints answer + hypotheses. |
| [autonomous_demo.py](autonomous_demo.py) | Runs the runtime for a period with seeded knowledge; observe autonomy + status. |
| [graph_evolution_demo.py](graph_evolution_demo.py) | Injects weak nodes and runs wave cycles to show graph evolution. |
| [TS-OS_Living_Demo.ipynb](TS-OS_Living_Demo.ipynb) | Jupyter walkthrough: graph, queries, autonomy hooks, self-improvement overview. |

**Tip:** Ensure Ollama is running and the model in `config.yaml` is pulled (`ollama pull <model>`) for LLM-backed answers.
