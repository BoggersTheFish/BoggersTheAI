# Contributing to BoggersTheAI

Welcome, and thank you for considering a contribution to BoggersTheAI — a living, graph-wave reasoning system built on the **TS-OS** (Thinking System / Operating System) philosophy.

TS-OS treats every piece of knowledge as a node in a constraint graph. Change propagates through waves of activation; truth emerges from the most stable configuration the constraints allow. Contributions that respect this mental model — protocol-driven, config-driven, wave-aware — merge fastest.

---

## Table of Contents

1. [Development Setup](#development-setup)
2. [Directory Structure](#directory-structure)
3. [Quality Checks](#quality-checks)
4. [Continuous Integration](#continuous-integration)
5. [Code Style Guide](#code-style-guide)
6. [How-To Guides](#how-to-guides)
   - [Add a New Adapter](#add-a-new-adapter)
   - [Add a New Tool](#add-a-new-tool)
   - [Add a New Health Check](#add-a-new-health-check)
   - [Add a New Metric](#add-a-new-metric)
   - [Add a New Event](#add-a-new-event)
   - [Add a New Cognitive Temperament](#add-a-new-cognitive-temperament)
7. [Pull Request Guidelines](#pull-request-guidelines)
8. [Commit Style](#commit-style)
9. [Configuration Philosophy](#configuration-philosophy)
10. [Security Guidelines](#security-guidelines)
11. [Reporting Issues](#reporting-issues)
12. [License](#license)

---

## Development Setup

### Prerequisites

- **Python 3.10, 3.11, or 3.12** (the CI matrix tests all three).
- **Ollama** running locally if you want LLM features (`ollama serve`).
- **(Optional)** A CUDA-capable GPU for the `[gpu]` extras (Unsloth fine-tuning).

### Fork, Clone, and Install

```bash
# 1. Fork via GitHub UI, then clone your fork
git clone https://github.com/<your-user>/BoggersTheAI.git
cd BoggersTheAI

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate

# 3. Install in editable mode with ALL dev extras
pip install -e ".[dev,multimodal,adapters]"

# 4. Verify the install compiles cleanly and tests pass
python -m compileall .
pytest -q
```

### Optional Dependency Groups

| Group          | Install command                     | What it adds                                        |
|----------------|-------------------------------------|-----------------------------------------------------|
| `dev`          | `pip install -e ".[dev]"`           | pytest, pytest-cov, black, isort, ruff, mypy, FastAPI, uvicorn, ollama |
| `llm`          | `pip install -e ".[llm]"`          | ollama                                              |
| `gpu`          | `pip install -e ".[gpu]"`          | ollama, unsloth, torch                              |
| `multimodal`   | `pip install -e ".[multimodal]"`   | faster-whisper, transformers, pillow, piper-tts      |
| `adapters`     | `pip install -e ".[adapters]"`     | feedparser                                          |
| `security`     | `pip install -e ".[security]"`      | defusedxml (safer RSS XML parsing)                  |
| `all`          | `pip install -e ".[all]"`          | Broader union — see `pyproject.toml`                |

**Repo automation:** From the project root, **`make test`**, **`make lint`**, **`make format`** wrap pytest / ruff / black / isort (see **`Makefile`**). Optional **`pre-commit install`** uses **`.pre-commit-config.yaml`**. Pytest defaults live in **`[tool.pytest.ini_options]`** in `pyproject.toml`.

---

## Directory Structure

```
BoggersTheAI/
├── core/                        # TS-OS engine — the beating heart
│   ├── graph/                   # Graph data structures and algorithms
│   │   ├── universal_living_graph.py  # Main graph class (thread-safe RLock)
│   │   ├── wave_propagation.py        # Propagate, relax, normalise, damping
│   │   ├── rules_engine.py            # Prune, merge, split, emerge, tension
│   │   ├── node.py                    # GraphNode dataclass
│   │   ├── sqlite_backend.py          # SQLite persistence (WAL mode)
│   │   ├── snapshots.py               # Graph versioning + rollback
│   │   ├── export.py                  # GraphML / JSON-LD export
│   │   ├── pruning.py                 # Configurable pruning policies
│   │   └── migrate.py                 # Schema migration helpers
│   ├── query_processor.py       # Query pipeline orchestrator
│   ├── router.py                # Query routing + hypothesis queue
│   ├── wave.py                  # Simplified wave API + background thread
│   ├── types.py                 # Node, Edge, Tension dataclasses
│   ├── local_llm.py             # Ollama / Unsloth LLM wrapper
│   ├── fine_tuner.py            # QLoRA fine-tuning pipeline
│   ├── trace_processor.py       # Reasoning trace → training data
│   ├── embeddings.py            # Cosine similarity + OllamaEmbedder
│   ├── contradiction.py         # Antonym-based conflict detection (O(k) scan)
│   ├── temperament.py           # Cognitive temperament presets
│   ├── context_mind.py          # Multi-context subgraph views
│   ├── protocols.py             # Shared Protocol definitions (VoiceIn/Out, ImageIn, Graph)
│   ├── config_loader.py         # YAML config loading + deep-merge
│   ├── config_resolver.py       # Safe nested config access
│   ├── config_schema.py         # Config validation on load
│   ├── mode_manager.py          # AUTO/USER mode coordination
│   ├── events.py                # In-process event bus (emit/on/off)
│   ├── plugins.py               # Entry-point plugin discovery
│   ├── health.py                # Health check registry
│   ├── metrics.py               # Thread-safe counters, gauges, timers
│   └── logger.py                # Structured logging (boggers.* namespace)
├── adapters/                    # Data ingestion adapters
│   ├── base.py                  # AdapterRegistry + caching + rate limiting
│   ├── wikipedia.py             # Wikipedia API adapter
│   ├── rss.py                   # RSS/Atom feeds (HTTPS-only enforcement)
│   ├── hacker_news.py           # Hacker News Algolia API
│   ├── markdown.py              # Local markdown file ingestion
│   ├── vault.py                 # Knowledge vault (delegates to markdown)
│   └── x_api.py                 # X (Twitter) API adapter
├── tools/                       # External tool execution
│   ├── base.py                  # ToolRegistry
│   ├── executor.py              # Tool dispatch + metrics integration
│   ├── router.py                # Rule-based keyword routing to tools
│   ├── calc.py                  # Safe arithmetic (AST-based)
│   ├── code_run.py              # Sandboxed Python execution (AST scanning)
│   ├── search.py                # HN Algolia search
│   └── file_read.py             # Safe file reading (base-dir restricted)
├── entities/                    # Domain services
│   ├── consolidation.py         # Graph node merging
│   ├── insight.py               # Markdown insight generation
│   ├── inference_router.py      # Throttled inference routing
│   └── synthesis_engine.py      # Extractive synthesis
├── multimodal/                  # Voice + image I/O
│   ├── base.py                  # Protocol re-exports (backward compatible)
│   ├── voice_in.py              # faster-whisper transcription
│   ├── voice_out.py             # piper-tts synthesis
│   ├── image_in.py              # BLIP2 captioning
│   ├── whisper.py               # Whisper backend alias
│   └── clip_embed.py            # CLIP backend alias
├── interface/                   # User-facing interfaces
│   ├── runtime.py               # BoggersRuntime — composition root
│   ├── chat.py                  # CLI chat interface + `health` command
│   └── api.py                   # HTTP API handler (singleton runtime)
├── mind/                        # TUI
│   └── tui.py                   # Rich-based terminal UI
├── dashboard/                   # Web dashboard
│   └── app.py                   # FastAPI endpoints + Cytoscape.js viz
├── tests/                       # Pytest test suite (147 tests)
├── examples/                    # Runnable demo scripts
│   ├── quickstart.py            # Minimal usage example
│   ├── autonomous_demo.py       # Full autonomous loop demo
│   └── graph_evolution_demo.py  # Graph evolution visualization
├── config.yaml                  # Central configuration file
├── pyproject.toml               # Build config, dependencies, tool settings
├── ARCHITECTURE.md              # Comprehensive architecture documentation
├── CHANGELOG.md                 # Release notes
├── .env.example                 # Environment variable template
└── .github/workflows/test.yml   # CI pipeline
```

---

## Quality Checks

Run **all** of the following before opening a PR:

```bash
# Auto-fix formatting and imports
black .
isort .

# Lint (auto-fix safe issues)
ruff check --fix .

# Static type checking
mypy BoggersTheAI --ignore-missing-imports

# Run the full test suite with coverage
pytest --cov=BoggersTheAI --cov-report=term-missing --cov-fail-under=50
```

| Tool   | Purpose                          | Config location           |
|--------|----------------------------------|---------------------------|
| ruff   | Linting (E, F, W, I rule sets)   | `[tool.ruff]` in pyproject.toml |
| black  | Code formatting (88-char lines)  | `[tool.black]` in pyproject.toml |
| isort  | Import sorting (black profile)   | `[tool.isort]` in pyproject.toml |
| mypy   | Static type checking             | CLI flags (ignore-missing-imports) |
| pytest | Test runner + coverage           | Default discovery, `tests/` dir |

---

## Continuous Integration

CI is defined in `.github/workflows/test.yml` and runs on every push and pull request.

### Matrix

| Python Version | Runner        |
|----------------|---------------|
| 3.10           | ubuntu-latest |
| 3.11           | ubuntu-latest |
| 3.12           | ubuntu-latest |

### Pipeline Steps (per matrix entry)

1. **Checkout** — `actions/checkout@v4`
2. **Setup Python** — `actions/setup-python@v5` with the matrix version
3. **Install** — `pip install -e ".[dev]"` (editable install with dev extras)
4. **Ruff lint** — `ruff check .` — fails the build on lint errors
5. **Black format check** — `black --check .` — fails if any file is unformatted
6. **isort import check** — `isort --check .` — fails if imports are mis-ordered
7. **mypy type check** — `mypy BoggersTheAI --ignore-missing-imports` — currently soft-fail (`|| true`)
8. **Pytest + coverage** — `pytest --cov=BoggersTheAI --cov-report=term-missing --cov-fail-under=50` — fails if line coverage drops below 50%

All steps must pass (except mypy, which is advisory) for the PR to be mergeable.

---

## Code Style Guide

### General Principles

- **Type hints everywhere.** All function signatures, return types, and non-trivial local variables must be annotated.
- **Protocols over concrete dependencies.** Depend on `typing.Protocol` (see `core/protocols.py`) rather than concrete classes. This keeps modules decoupled and testable.
- **Config-driven behavior.** All tuning knobs belong in `config.yaml`. Never hardcode magic numbers — use `core/config_resolver.py` to read config values, or define named constants with sensible defaults.
- **Minimal comments.** Code should be self-documenting. Comments explain *why*, never *what*. No narration ("# Import os", "# Return result").
- **Dataclasses with `__slots__`.** Use `@dataclass(slots=True)` for all data containers to reduce memory overhead.
- **Named constants.** If a number appears in logic, give it a `UPPER_SNAKE_CASE` name at module level.
- **Structured logging.** Use `core/logger.py` (`boggers.*` namespace). Never use `print()`.
- **No emoji in logs or code.** Logs must be safe for Windows cp1252 terminals.

### Import Ordering

isort with the `black` profile handles this automatically. The order is:

1. Standard library
2. Third-party packages
3. Local (`BoggersTheAI.*`) imports

All imports should be at module level (no inline `import time` inside functions).

### Error Handling

- Wrap external calls (HTTP, Ollama, file I/O) in `try/except` with structured logging.
- Never silently swallow exceptions.
- Use defensive `try/except` for non-critical paths (multimodal, backups) so failures don't crash the wave loop.

---

## How-To Guides

### Add a New Adapter

Adapters ingest external data into the graph. To add one:

1. **Create** `adapters/your_adapter.py` with a class that implements an `ingest(graph, config) -> int` method returning the number of nodes created.
2. **Register** in `interface/runtime.py` by adding your adapter to the `AdapterRegistry` during runtime init.
3. **Add a config flag** in `config.yaml` under `adapters.enabled`:
   ```yaml
   adapters:
     enabled:
       your_source: true
   ```
4. **Add tests** in `tests/test_adapters_detailed.py` (or a new test file) covering happy path, network errors, and disabled-flag behavior.
5. **(Optional)** Register as an entry point in `pyproject.toml` under `[project.entry-points."boggers.adapters"]` for plugin discovery.
6. **Update** `README.md` adapter table and `CHANGELOG.md`.

### Add a New Tool

Tools let the query processor call external capabilities (search, calculate, execute code, read files).

1. **Create** `tools/your_tool.py` with a class that implements an `execute(query: str, **kwargs) -> str` method.
2. **Register** in `tools/executor.py` — add your tool to `ToolExecutor.with_defaults()` so it is available by default.
3. **Add routing keywords** in `tools/router.py` — map trigger phrases to your tool name so the router can auto-select it.
4. **Add tests** in `tests/test_tools_detailed.py` covering normal execution, edge cases, and error handling.
5. **(Optional)** Register as an entry point in `pyproject.toml` under `[project.entry-points."boggers.tools"]`.
6. **Update** `README.md` tools table and `CHANGELOG.md`.

### Add a New Health Check

Health checks report subsystem status (healthy/degraded/unhealthy).

1. **Write a check function** with signature `def check_name(runtime) -> HealthResult` where `HealthResult` has `status` (str) and `message` (str).
2. **Register** the check in `core/health.py` by adding it to the `HealthChecker` registry, either in `__init__` or via `register(name, check_fn)`.
3. **Add a test** in `tests/test_health.py` verifying both healthy and degraded states.
4. The CLI `health` command and dashboard `/health` endpoint automatically pick up registered checks.

### Add a New Metric

Metrics track counters, gauges, and timers for observability.

1. **Instrument** your code by calling `MetricsCollector` methods:
   - `metrics.increment("your_counter")` for event counts
   - `metrics.gauge("your_gauge", value)` for current-state values
   - `metrics.time("your_timer")` as a context manager for latency
2. The dashboard `/status` endpoint automatically exposes all registered metrics.
3. **Add a test** in `tests/test_events_metrics.py` verifying the metric is recorded.

### Add a New Event

Events enable decoupled module communication through the `EventBus`.

1. **Choose an event name** following the `noun_verb` convention (e.g., `wave_cycle_complete`, `node_created`, `query_processed`).
2. **Emit** the event at the appropriate place: `event_bus.emit("your_event", payload)`.
3. **Subscribe** listeners elsewhere: `event_bus.on("your_event", handler_fn)`.
4. **Add a test** in `tests/test_events_metrics.py` verifying emission and reception.
5. **Document** the event in `ARCHITECTURE.md` if it crosses module boundaries.

### Add a New Cognitive Temperament

Temperaments are named presets that tune wave parameters (spread factor, tension threshold, relax decay, etc.).

1. **Define** the preset in `core/temperament.py` by adding an entry to the `TEMPERAMENTS` dict:
   ```python
   "your_temperament": TemperamentPreset(
       spread_factor=0.5,
       tension_threshold=0.7,
       relax_decay=0.02,
       prune_threshold=0.1,
       activation_cap=1.0,
       damping=0.05,
   )
   ```
2. **Add a config option** — users select it via `wave.temperament: "your_temperament"` in `config.yaml`.
3. **Add a test** in `tests/test_temperament.py` verifying the preset values propagate correctly.

---

## Pull Request Guidelines

- **Keep changes focused.** One logical change per PR. Avoid mixing refactors with features.
- **Add or update tests** for any behavior change. Coverage must not drop below the CI threshold (currently 50%, target is 74%+).
- **Update documentation:**
  - `README.md` if user-visible behavior or CLI/API surface changes.
  - `CHANGELOG.md` with a summary under the appropriate heading (Added/Changed/Fixed/Security/Removed).
  - `.env.example` if new environment variables are introduced.
- **Don't break backward compatibility** without discussion. If a public interface changes, provide a deprecation path or migration note.
- **Keep runtime safety defaults sensible.** Risky paths (fine-tuning, code execution) should default to safe/off (`safety_dry_run: true`).
- **Prefer protocol-driven design** over concrete dependencies.
- **Avoid heavy new dependencies** unless clearly justified. The core package depends only on `pyyaml`.
- **Run all quality checks** locally before pushing (see [Quality Checks](#quality-checks)).

---

## Commit Style

- **Imperative mood, short subject line** (50 chars soft limit, 72 hard):
  ```
  Add graph metrics endpoint
  Fix thread safety in prune()
  ```
- **Body** (separated by blank line) for non-obvious changes — explain the *why*:
  ```
  Add graph metrics endpoint

  The dashboard needs topology stats (node count, edge density,
  activation distribution) for the observability panel. Exposed
  via GET /graph with the same auth middleware.
  ```
- **No prefix conventions required** (no `feat:`, `fix:`, etc.), but they are welcome if you prefer them.
- **Reference issues** when applicable: `Closes #42`.

---

## Configuration Philosophy

All runtime tuning lives in `config.yaml`. The guiding principles:

1. **No hardcoded magic numbers.** Every threshold, interval, limit, or factor should be a config key or a named constant with a default.
2. **Sensible defaults.** The system must work out-of-the-box with zero config. Every key in `config.yaml` has a fallback in code.
3. **Safe for public repos.** `config.yaml` never contains secrets. Sensitive values come from environment variables.
4. **Deep-merge with overrides.** `config_loader.py` deep-merges the YAML file into `RuntimeConfig`. Missing keys fall back to defaults.
5. **Validated on load.** `config_schema.py` validates the config structure at startup and logs warnings for unknown keys.
6. **Accessed safely.** Use `config_resolver.resolve(cfg, "path.to.key", default)` for nested access without `KeyError` risk.

When adding a new config key:
- Add it to `config.yaml` with a comment explaining its purpose.
- Set a sensible default in the code path that reads it.
- Add validation in `config_schema.py` if the value has constraints.

---

## Security Guidelines

| Area               | Rule                                                                 |
|--------------------|----------------------------------------------------------------------|
| **Secrets**        | Never commit `.env`, API keys, or tokens. Use `.env.example` as a template. |
| **Environment vars** | All sensitive values (`X_BEARER_TOKEN`, `BOGGERS_DASHBOARD_TOKEN`, etc.) come from env vars. |
| **Code execution** | `tools/code_run.py` uses AST-based sandbox scanning that blocks `__import__`, `exec`, `eval`, and dangerous module imports (`os`, `subprocess`, `socket`, `shutil`, etc.). |
| **File access**    | `tools/file_read.py` restricts reads to the configured base directory. No path traversal. |
| **External HTTP**  | RSS adapter enforces HTTPS-only URLs. All HTTP adapters have error handling for network failures. |
| **Dashboard auth** | Token-based middleware via `BOGGERS_DASHBOARD_TOKEN`. The `/wave`, `/graph/viz` endpoints require auth headers. |
| **Config safety**  | `config.yaml` is safe for public repositories. Never put secrets in it. |
| **Multimodal I/O** | `ask_audio` and `ask_image` are wrapped in defensive `try/except` to prevent crashes from malformed input. |
| **Backups**        | `shutil.copytree` backup operations are wrapped in `try/except` so backup failures don't crash the system. |

If you discover a security vulnerability, please report it privately via the GitHub security advisory process rather than opening a public issue.

---

## Reporting Issues

Use the [GitHub issue templates](https://github.com/BoggersTheFish/BoggersTheAI/issues/new/choose) for:

- **Bug reports** — include Python version, OS, config.yaml changes, and full traceback.
- **Feature requests** — describe the use case, not just the solution.
- **Questions** — for general usage help or architecture questions.

---

## License

BoggersTheAI is released under the **MIT License**. By contributing, you agree that your contributions will be licensed under the same terms. See [LICENSE](LICENSE) for the full text.
