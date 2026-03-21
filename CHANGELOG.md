# Changelog

All notable changes to BoggersTheAI are documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.5.0] - 2026-03-22

Seven-tier modular roadmap: correctness, security, architecture splits,
performance, config/DX, tests/CI, and plugin-shaped features. See README and
ARCHITECTURE.md for full detail.

### Added
- **`core/graph/wave_runner.py`** — `WaveCycleRunner` + `WaveConfig`; background wave thread and cycle step order live here; `UniversalLivingGraph` delegates to it.
- **`interface/autonomous_loop.py`** / **`interface/self_improvement.py`** — `AutonomousLoopMixin` and `SelfImprovementMixin`; `BoggersRuntime` composes both.
- **`core/path_sandbox.py`** — `validate_path` for safe reads under a base directory.
- **`adapters/http_client.py`** — `fetch_url` / `fetch_json` with exponential backoff and retries; Wikipedia, RSS, Hacker News use it.
- **`core/graph/operations.py`** — Pure helpers: `get_subgraph_around`, `batch_add_nodes`, `find_connected_components`, `get_nodes_by_activation_range`.
- **Tools:** `web_search.py` (DuckDuckGo instant answers), `datetime_tool.py`, `unit_convert.py`; registered in `ToolExecutor.with_defaults` and routed in `ToolRouter`.
- **Dashboard:** `get_runtime()` lazy singleton; **`GET /health/live`**, **`GET /health/ready`**.
- **`Makefile`**, **`.pre-commit-config.yaml`**, **`[tool.pytest.ini_options]`** in `pyproject.toml`.
- **`[project.optional-dependencies].security`** — `defusedxml` for safer RSS XML when installed.
- **Config:** `inference.ollama.base_url`, `os_loop.consolidation_on_shutdown`, strict validation via **`BOGGERS_CONFIG_STRICT`** / `validate_config(..., strict=True)`.
- **Tests:** New modules covered (`test_config_loader`, `test_plugins`, `test_sqlite_backend`, `test_rules_engine`, `test_inference_router`, `test_path_sandbox`, `test_wave_runner`, `test_http_client`, `test_graph_operations`, `test_new_tools`); **200+** tests total.

### Changed
- **ConsolidationEngine** — topic-bucketed candidate pairs + Jaccard early exit (was full O(n²) over all pairs).
- **`get_activated_subgraph`** — `heapq.nlargest` for global fill instead of full sort.
- **AdapterRegistry** — thread-safe cache under `Lock`.
- **`_check_guardrails`** — reads node count and cycle counters under graph `RLock`.
- **CI:** pip cache, **`--cov-fail-under=60`**, **mypy blocking**, adapter tests mock **`http_client.urlopen`**.
- **Dashboard:** default bind **`127.0.0.1`**, startup warning if no **`BOGGERS_DASHBOARD_TOKEN`**.

### Fixed
- **ModeManager.request_user_mode** — monotonic deadline; total wait cannot exceed `timeout` after spurious wakeups.
- **QueryRouter** — honors failed `request_user_mode()` with a busy response.
- **CalcTool** — `%` and `//` operators.
- **VaultAdapter** — resolves paths under `runtime.insight_vault_path`.
- **Inference fallback** — consistent tuple shape with main synthesis path.
- **`shutdown`** — optional forced nightly consolidation (configurable).

### Security
- Markdown/vault ingestion uses path sandbox; RSS XML size cap + optional **defusedxml**.
- **FileReadTool** max file size and pinned base directory.
- **LocalLLM** uses configurable Ollama **base_url** (no hardcoded host only).

---

## [0.4.0] - 2026-03-21

Comprehensive hardening pass across Phases 1–6: protocol centralization, config
validation, performance optimization, thread safety, security hardening, CI
expansion, and full test coverage overhaul.

### Added
- **`core/protocols.py`** — centralizes `VoiceIn`, `VoiceOut`, `ImageIn`, and `Graph` protocol definitions in a single module, eliminating scattered duck-typing.
- **`core/config_resolver.py`** — utility for safe nested config access (`resolve(cfg, "a.b.c", default)`) without `KeyError` risk.
- **`core/config_schema.py`** — validates the full `config.yaml` structure at startup; logs warnings for unknown keys and type mismatches.
- **`ARCHITECTURE.md`** — comprehensive documentation covering module layout, data flow (Mermaid), wave cycle diagram, thread model, persistence backends, and self-improvement pipeline.
- **7 new test files** with 64 new tests (147 total, up from 83):
  - `test_protocols.py` — protocol compliance and re-export verification
  - `test_config_schema.py` — schema validation edge cases
  - `test_events_metrics.py` — event bus emission/subscription and metrics recording
  - `test_health.py` — health checker registration and status aggregation
  - `test_concurrency.py` — thread safety under concurrent graph mutation
  - `test_tools_detailed.py` — tool execution, routing, and error paths
  - `test_adapters_detailed.py` — adapter ingestion, caching, and failure modes
- **`health` CLI command** — `boggers health` runs all registered health checks and prints aggregate status.
- **EventBus wired into wave loop** — emits `wave_cycle_complete` after every cycle; wired into `ask()` pipeline for `query_processed` events.
- **MetricsCollector wired into runtime** — tracks `queries_total`, `tool_calls_total`, `wave_cycles_total`; exposed via dashboard `/status`.
- **HealthChecker** — registered checks for graph connectivity, wave engine liveness, and LLM availability.
- **PluginRegistry entry-point discovery** — scans `boggers.adapters` and `boggers.tools` entry points at init for third-party plugins.
- **PruningPolicy** — configurable pruning strategies applied in consolidation paths (`core/graph/pruning.py`).
- **Python 3.10 / 3.11 / 3.12 CI matrix** — all three versions tested on every push/PR with `--cov-fail-under=50` threshold.
- **`[multimodal]` optional dependency group** — `pip install -e ".[multimodal]"` installs faster-whisper, transformers, pillow, piper-tts.
- **`[adapters]` optional dependency group** — `pip install -e ".[adapters]"` installs feedparser.
- **`[tool.ruff]` config section** in `pyproject.toml` — line-length 88, target py310, E/F/W/I rule sets.

### Changed
- **Contradiction detection** uses topic-indexed O(k) scan instead of previous O(n²) pairwise comparison.
- **`strongest_node()`** result is cached with invalidation on graph mutation, avoiding redundant full-graph scans.
- **`_count_traces()`** uses a 60-second TTL cache to avoid repeated filesystem walks.
- **`fine_cfg`** resolved once at init rather than re-reading config on every fine-tuning call.
- **`rules_engine.py`** replaces all magic numbers with named `UPPER_SNAKE_CASE` constants at module level.
- **`multimodal/base.py`** re-exports protocol types from `core/protocols.py` (backward compatible — existing `from multimodal.base import VoiceIn` still works).
- **`core/router.py`** imports protocol types from `core/protocols.py` instead of cross-boundary import from `multimodal`, breaking the circular dependency.
- **`max_retries`** is now configurable in synthesis config rather than hardcoded to 2.
- **Coverage**: 74% line coverage (up from ~50%), 147 tests (up from 83).

### Fixed
- **Thread safety** — added `threading.Lock` on:
  - `prune()` in `rules_engine.py`
  - `_hypothesis_queue` in `router.py`
  - `ContextManager` read paths in `context_mind.py`
  - API singleton creation in `api.py`
  - LLM hot-swap in `local_llm.py`
- **`ModeManager.request_user_mode`** now accepts a `timeout` parameter and returns `bool` instead of blocking indefinitely.
- **Temp file cleanup** in `voice_in.py` — temporary WAV files are deleted after transcription.
- **Missing `embedding` field** in snapshot restore and SQLite import — nodes now round-trip embeddings correctly.
- **Duplicate `detect_contradictions` call** in `run_wave()` — removed the redundant invocation that ran contradiction detection twice per cycle.
- **`split_overactivated`** now logs pre-mutation activation values for debugging, not post-split values.
- **`import time`** moved to module level in `universal_living_graph.py` (was inline inside a method).
- **`JSON load()`** now calls `migrate_graph_data()` ensuring legacy graph files are upgraded on read.

### Security
- **AST-based sandbox scanning** in `code_run.py` blocks `__import__()`, `exec()`, `eval()`, and all known evasion patterns (attribute access, string concatenation, `getattr` tricks).
- **`FileReadTool`** restricted to configured base directory — rejects all paths outside the allowed root, preventing directory traversal.
- **RSS adapter HTTPS-only enforcement** — feed URLs using plain HTTP are rejected with a logged warning.
- **Dashboard `/wave` and `/graph/viz`** include auth header requirements — unauthenticated requests receive 401.
- **Dashboard `/graph/viz`** requires the auth dependency (was previously unprotected).
- **`ask_audio` / `ask_image`** wrapped with defensive `try/except` — malformed audio or image input logs the error and returns a graceful fallback instead of crashing.
- **`shutil.copytree` backup** wrapped with `try/except` — backup failures are logged and do not abort the operation that triggered them.

---

## [0.3.0] - 2026-03-20

### Added
- **Node embeddings** via Ollama (`nomic-embed-text`) — auto-embed on node creation when enabled (`core/embeddings.py`).
- **Hybrid propagation** — cosine similarity as second channel alongside topological spread in `wave_propagation.py`.
- **Activation normalization + damping** — configurable `damping` and `activation_cap` in wave settings; global cap enforced in propagate/relax.
- **Contradiction detection** — `core/contradiction.py` finds conflicting high-activation nodes sharing topics with antonym content; auto-resolves by weakening lower-stability node.
- **Cognitive temperament presets** — `core/temperament.py` with contemplative, analytical, reactive, critical, creative, default profiles applied via `wave.temperament` config.
- **Multiple concurrent contexts/minds** — `core/context_mind.py` with `ContextManager` for topic/node-filtered subgraph views per context.
- **Graph state versioning + rollback** — `core/graph/snapshots.py` with save/list/restore/delete snapshot methods.
- **GraphML + JSON-LD export** — `core/graph/export.py` with `export_graphml()` and `export_json_ld()`.
- **Resource guardrails** — max nodes (5000), max cycles/hour (200), high-tension pause (0.95) in wave loop.
- **Immutable snapshot reads** — `snapshot_read()` returns deep copies for thread-safe reads without locking.
- **Code sandbox** — `tools/code_run.py` blocks dangerous imports (os, subprocess, socket, etc.) via import hook; configurable on/off.
- **LLM-powered evolve** — `spawn_emergence` and `evolve()` accept optional `evolve_fn` callback; wired to `LocalLLM.synthesize_evolved_content`.
- **Incremental save every N waves** — configurable `incremental_save_interval` (default 5) instead of every cycle.
- **Self-improvement first-run warning** — logs experimental warning when fine-tuning is enabled.
- **Cytoscape.js graph visualization** — replaced Sigma.js in `/graph/viz` with Cytoscape.js (cose layout, activation/stability mapping).
- **Mermaid wave cycle diagram** in README.
- **Optional dependency groups** — `pip install .[llm]` / `.[gpu]` / `.[dev]` / `.[all]`; core only needs `pyyaml`.
- 43 new tests (83 total) covering embeddings, contradiction, temperament, snapshots, export, context_mind, code sandbox, graph guardrails, damping, embeddings roundtrip.

### Changed
- **SQLite is now default** persistence backend (`runtime.graph_backend: "sqlite"` in config).
- **Fine-tuning off by default** — `fine_tuning.enabled: false`, `auto_schedule: false`, `safety_dry_run: true`.
- `rules_engine.py` now runs contradiction detection + resolution as part of `run_rules_cycle`.
- `wave.py` relax/break steps now integrate `rules_detect_tension` and contradiction resolution.
- `propagate()` uses damping factor and activation cap throughout.
- Wave logging uses `logger.info` instead of print.
- Heavy dependencies (`ollama`, `unsloth`, `torch`) moved to optional extras.
- Dashboard version bumped to 0.3.0.

---

## [0.2.1] - 2026-03-20

### Changed
- **Documentation:** Expanded [README.md](README.md) with table of contents, prerequisites (Ollama, optional GPU), full CLI command reference, Python API table, dashboard endpoints and auth notes, data directories, and troubleshooting pointers for dashboard token vs browser `fetch`.
- [CONTRIBUTING.md](CONTRIBUTING.md) now includes a Documentation section and cross-links to README, CHANGELOG, and `.env.example`.
- [.env.example](.env.example) documents dashboard host/port/token variables.
- [examples/README.md](examples/README.md) indexes quickstart, demos, and notebook.
- Package version bumped to **0.2.1** (`pyproject.toml`, dashboard OpenAPI version).

---

## [0.2.0] - 2026-03-20

### Added
- Config loader (`core/config_loader.py`) — reads `config.yaml` and deep-merges into RuntimeConfig.
- Structured logging (`core/logger.py`) — all modules use `boggers.*` namespace instead of print().
- Event bus (`core/events.py`) — decoupled module communication via emit/on/off.
- Plugin registry (`core/plugins.py`) — entry-point discovery for adapters and tools.
- Health check system (`core/health.py`) — timed checks with aggregate healthy/degraded status.
- Metrics collector (`core/metrics.py`) — thread-safe counters, gauges, and timers.
- Graph metrics method (`get_metrics()`) — topic distribution, activation/stability averages, edge density.
- Wave history tracking (`core/wave.py`) — last 100 cycle snapshots via `get_wave_history()`.
- LLM health check (`local_llm.py`) — verify model can generate before declaring hot-swap success.
- Real multimodal backends — faster-whisper STT, piper TTS, BLIP2 captioning with graceful fallback.
- X API adapter — full implementation with bearer token auth from environment variable.
- Adapter response caching — 5-minute TTL cache in AdapterRegistry.
- Dashboard auth — token-based middleware via `BOGGERS_DASHBOARD_TOKEN` env var.
- Dashboard endpoints — `/graph` (topology) and `/traces` (reasoning traces).
- Configurable dashboard host/port via `BOGGERS_DASHBOARD_HOST` and `BOGGERS_DASHBOARD_PORT`.
- Path validation in FileReadTool — extension allowlist prevents traversal attacks.
- 22 new test functions across 12 modules (26 total).
- `py.typed` marker for PEP 561 type-checker support.
- `CHANGELOG.md` for version tracking.
- mypy added to dev dependencies.

### Changed
- Config pipeline now actually reads `config.yaml` — previously all settings were hardcoded defaults.
- Adapter registration respects `adapters.enabled` flags from config.
- Wave parameters (spread_factor, relax_decay, tension_threshold, prune_threshold) are configurable.
- Query processor sufficiency weights are configurable via synthesis config.
- LoRA hyperparameters (r, alpha, dropout, target_modules, batch_size, grad_accum) are configurable.
- Search backend URL is configurable in SearchTool.
- ToolExecutor wires code_run_timeout_seconds from config to CodeRunTool.
- Similarity threshold in ConsolidationEngine is configurable.
- LLM synthesis has 2-attempt retry with logged failures.
- All print() calls replaced with structured logging (Windows cp1252-safe, no emoji).
- `handle_query` in api.py uses singleton runtime instead of creating one per call.
- CLI chat loop has error handling around `rt.ask()`.
- CI workflow expanded with ruff, black, isort checks alongside pytest.
- License field uses SPDX string format (no deprecation warnings).

### Fixed
- Router `_enqueue_hypotheses` type mismatch — now handles both `List[dict]` and `List[str]`.
- Thread safety — RLock on UniversalLivingGraph, Lock on runtime shared state, Lock on dashboard history.
- Swallowed exceptions in consolidation and LLM adapter now logged.
- Network error handling added to all HTTP adapters (Wikipedia, RSS, HackerNews).

### Removed
- Orphaned `core/graph/edge.py` (GraphEdge was never used; Edge from types.py is canonical).
- Deprecated license classifier from pyproject.toml.
- Duplicate content in CONTRIBUTING.md.

---

## [0.1.0] - 2026-03-20

### Added
- Core TS-OS graph engine with wave propagation, tension detection, and emergence.
- Background wave thread with configurable interval and auto-save.
- Query processor with topic extraction, context retrieval, and synthesis.
- Local LLM integration via Ollama with hypothesis generation.
- Self-improvement factory: trace processor, dataset builder, Unsloth fine-tuner.
- Auto-scheduling, validation gating, and adapter rollback for fine-tuning.
- Adapters: Wikipedia, RSS, HackerNews, Vault, Markdown, X API (stub).
- Tools: search, calc, code_run, file_read with router.
- Multimodal: voice in/out, image captioning (placeholders).
- OS loop with autonomous exploration, consolidation, and insight modes.
- Nightly consolidation and multi-turn conversation memory.
- FastAPI dashboard with /status and /wave endpoints.
- TUI via Rich library.
- 4 initial tests (graph, wave, synthesis).
- GitHub Actions CI with pytest.
- MIT license, CONTRIBUTING.md, issue templates.
