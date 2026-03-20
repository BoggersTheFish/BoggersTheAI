# BoggersTheAI

**Status: Living OS v0.1**

BoggersTheAI is a modular TS-OS runtime that uses a living graph, wave propagation, and constrained synthesis for local-first reasoning and autonomy.

## One-command install

```bash
pip install -e .
```

For development tooling:

```bash
pip install -e ".[dev]"
```

## Usage

### CLI

```bash
boggers
```

### Python runtime

```python
from BoggersTheAI import BoggersRuntime

rt = BoggersRuntime()
response = rt.ask("Explain TS-OS graph wave architecture")
print(response.answer)
print(response.hypotheses)
print(rt.get_status())
```

### Self-improvement trigger

```python
from BoggersTheAI import BoggersRuntime

rt = BoggersRuntime()
stats = rt.trigger_self_improvement()
print(stats)
```

### Dashboard

```bash
dashboard-start
```

Then open [http://localhost:8000/wave](http://localhost:8000/wave).

## Architecture

- `core/graph/`: Universal living graph + wave/rules engine.
- `core/query_processor.py`: retrieval, synthesis, hypothesis handling, trace logging.
- `core/trace_processor.py` + `core/fine_tuner.py`: self-improvement factory.
- `interface/runtime.py`: composition root, autonomy loop, scheduling, safety.
- `dashboard/app.py`: FastAPI observability endpoints.

Architecture diagram link: [TS-OS architecture reference](https://www.boggersthefish.com/)

## Endpoints

- `GET /status`: graph + wave health data.
- `GET /wave`: live tension chart using Chart.js.

## Tests

```bash
pytest -q
```

## License

MIT (`LICENSE`).
