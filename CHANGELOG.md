# Changelog

## [0.2.1] - 2026-03-20

### Changed
- **Documentation:** Expanded [README.md](README.md) with table of contents, prerequisites (Ollama, optional GPU), full CLI command reference, Python API table, dashboard endpoints and auth notes, data directories, and troubleshooting pointers for dashboard token vs browser `fetch`.
- [CONTRIBUTING.md](CONTRIBUTING.md) now includes a Documentation section and cross-links to README, CHANGELOG, and `.env.example`.
- [.env.example](.env.example) documents dashboard host/port/token variables.
- [examples/README.md](examples/README.md) indexes quickstart, demos, and notebook.
- Package version bumped to **0.2.1** (`pyproject.toml`, dashboard OpenAPI version).

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
