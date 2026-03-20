# Changelog

## [0.1.0] - 2026-03-20

### Added
- Core TS-OS graph engine with wave propagation, tension detection, and emergence.
- Background wave thread with configurable interval and auto-save.
- Query processor with topic extraction, context retrieval, and synthesis.
- Local LLM integration via Ollama with hypothesis generation.
- Self-improvement factory: trace processor, dataset builder, Unsloth fine-tuner.
- Auto-scheduling, validation gating, and adapter rollback for fine-tuning.
- Adapters: Wikipedia, RSS, HackerNews, Vault, Markdown, X API.
- Tools: search, calc, code_run, file_read with router.
- Multimodal: voice in/out, image captioning with real backend support.
- OS loop with autonomous exploration, consolidation, and insight modes.
- Nightly consolidation and multi-turn conversation memory.
- FastAPI dashboard with /status, /wave, /graph, /traces endpoints.
- TUI via Rich library.
- Config loader reading config.yaml with deep-merge into RuntimeConfig.
- Structured logging under "boggers" namespace.
- Thread safety with RLock on graph, Lock on runtime state.
- Event bus for decoupled module communication.
- Plugin architecture for adapter/tool discovery.
- Health check and metrics collection systems.
- Pytest suite with 12 test modules.
- GitHub Actions CI with lint, format, and test steps.
- MIT license, CONTRIBUTING.md, issue templates.
