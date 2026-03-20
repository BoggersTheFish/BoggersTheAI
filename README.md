# BoggersTheAI

**Status: Living OS v0.2**

BoggersTheAI is a modular TS-OS (Thinking System Operating System) runtime that uses a living graph, wave propagation, and constrained synthesis for local-first reasoning and autonomy. It favors structure, constraint satisfaction, and emergent behavior over monolithic model scale.

## Install

```bash
pip install -e .
```

With development tooling (pytest, black, ruff, mypy, fastapi, uvicorn):

```bash
pip install -e ".[dev]"
```

## Quick start

### CLI chat

```bash
boggers
```

Type queries, type `status` for wave health, type `exit` to quit.

### Python runtime

```python
from BoggersTheAI import BoggersRuntime

rt = BoggersRuntime()
response = rt.ask("Explain TS-OS graph wave architecture")
print(response.answer)
print(response.hypotheses)
print(response.confidence)
print(rt.get_status())
rt.shutdown()
```

### Self-improvement

```python
rt = BoggersRuntime()

# Build training dataset from reasoning traces
stats = rt.build_training_dataset()

# Fine-tune and hot-swap (with validation gating)
result = rt.trigger_self_improvement()
print(result)
```

### Dashboard

```bash
dashboard-start
```

Open [http://localhost:8000/wave](http://localhost:8000/wave) for the live tension chart.

## Repository layout

```text
BoggersTheAI/
├── core/
│   ├── graph/              # Universal living graph + wave/rules engine
│   ├── config_loader.py    # YAML config loader with deep-merge
│   ├── logger.py           # Structured logging under "boggers" namespace
│   ├── query_processor.py  # Retrieval, synthesis, hypothesis, trace logging
│   ├── router.py           # Query routing + autonomous cycle orchestration
│   ├── wave.py             # TS-OS wave steps with history tracking
│   ├── local_llm.py        # Ollama / Unsloth adapter with health check
│   ├── fine_tuner.py       # QLoRA fine-tuning with configurable LoRA params
│   ├── trace_processor.py  # Alpaca dataset builder from reasoning traces
│   ├── events.py           # Event bus for decoupled module communication
│   ├── plugins.py          # Plugin registry with entry-point discovery
│   ├── health.py           # Health check system
│   ├── metrics.py          # Thread-safe counters, gauges, and timers
│   └── mode_manager.py     # USER/AUTO mode coordination
├── adapters/               # Wikipedia, RSS, HackerNews, Vault, Markdown, X API
├── entities/               # Consolidation engine, insight engine, synthesis, inference router
├── tools/                  # Search, calc, code_run, file_read + router/executor
├── multimodal/             # Voice in (faster-whisper), voice out (piper), image (BLIP2)
├── interface/              # BoggersRuntime, CLI chat, API handler
├── mind/                   # Rich TUI for wave observability
├── dashboard/              # FastAPI dashboard with Chart.js
├── tests/                  # 26 tests across 12 modules
├── examples/               # Quickstart script + Jupyter demo notebook
├── config.yaml             # Central configuration (loaded automatically)
└── pyproject.toml          # Package metadata, scripts, dependencies
```

## Configuration

All settings live in `config.yaml` and are loaded automatically on runtime startup. Sections:

| Section | Controls |
|---------|----------|
| `modules` | Enable/disable core, adapters, tools, multimodal |
| `inference` | Ollama model, self-improvement, synthesis, fine-tuning |
| `adapters.enabled` | Per-adapter enable flags (wikipedia, rss, hacker_news, vault, x_api) |
| `tools` | Tool enable flags, code_run timeout |
| `multimodal` | Voice/image backend selection |
| `wave` | Interval, logging, auto-save |
| `os_loop` | Autonomy interval, idle threshold, nightly schedule |
| `autonomous` | Exploration strength, prune threshold, insight tension |
| `tui` | Enable + theme |
| `deployment_tiers` | Laptop/desktop/cloud presets |

## API endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /status` | Token | Graph + wave health data |
| `GET /wave` | Public | Live tension chart (Chart.js) |
| `GET /graph` | Token | Full graph topology as JSON |
| `GET /traces` | Token | Recent reasoning traces |

Set `BOGGERS_DASHBOARD_TOKEN` env var to enable auth. Configure host/port with `BOGGERS_DASHBOARD_HOST` and `BOGGERS_DASHBOARD_PORT`.

## Architecture

BoggersTheAI follows TS-OS principles:

- **Everything = stable clusters of constraints** (nodes + edges in a living graph)
- **Change = wave propagation** through the graph
- **Complexity = emergence** from local interactions
- **Truth = the most stable configuration** the constraints allow

The core loop: `Propagate -> Relax -> Break (if tension high) -> Evolve`

Key subsystems:
- **Living Graph** with thread-safe RLock, configurable wave parameters, and JSON persistence
- **Query Processor** with topic extraction, graph-aware retrieval, LLM synthesis with retry, and hypothesis consistency checking
- **Self-Improvement Factory** that logs reasoning traces, builds datasets, fine-tunes via QLoRA, and hot-swaps with validation gating
- **Autonomous OS Loop** with exploration, consolidation, and insight modes
- **Event Bus** for decoupled module communication
- **Plugin Registry** with entry-point discovery for extensibility
- **Health Checker** and **Metrics Collector** for observability

Architecture reference: [boggersthefish.com](https://www.boggersthefish.com/)

## Testing

```bash
pytest -q                          # quick run
pytest --cov=BoggersTheAI -v       # with coverage
```

26 tests across 12 modules covering graph, wave, synthesis, router, runtime, consolidation, insight, adapters, tools, traces, fine-tuner, LLM, dashboard, and integration.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, quality checks, and PR guidelines.

## License

MIT. See [LICENSE](LICENSE).
