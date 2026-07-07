# Configuration

Runtime settings are loaded from `config.yaml`, deep-merged over
`RuntimeConfig` defaults by `core/config_loader.py`, and validated by
`core/config_schema.py`.

Set `BOGGERS_CONFIG_STRICT=1` to raise on validation warnings instead of only
logging them.

## Main Sections

| Section | Purpose |
|---------|---------|
| `modules` | Feature toggles for core graph, adapters, tools, multimodal, consolidation, and interfaces. |
| `inference` | Local synthesis mode, Ollama settings, trace logging, dataset building, and optional fine-tuning knobs. |
| `adapters` | External data adapters such as Wikipedia, RSS, Hacker News, vault files, and X/Twitter. |
| `tools` | Built-in tool toggles for search, calculator, sandboxed code execution, and restricted file reads. |
| `multimodal` | Voice and image backend selection. Optional dependencies degrade to placeholders when absent. |
| `runtime` | Graph persistence, backend selection, SQLite path, sessions, snapshots, and local vault paths. |
| `wave` | Wave scheduling, damping, activation cap, propagation, pruning, tension threshold, and BOGVM payload execution bounds. |
| `os_loop` | Background exploration, consolidation, insight cadence, and multi-turn session behavior. |
| `tui` | Rich terminal UI toggle and theme. |
| `autonomous` | Local autonomous behavior tuning. |
| `guardrails` | Resource limits such as max nodes, max cycles per hour, and high-tension pause threshold. |
| `embeddings` | Embedding generation toggle and local embedding model. |
| `deployment_tiers` | Informational presets only; these are not enforced constraints. |

For exact current defaults, read `core/config.py`, `core/config_schema.py`, and
the checked-in `config.yaml`.

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `BOGGERS_CONFIG_STRICT` | Raise on config validation warnings when set to `1` or `true`. |
| `BOGGERS_DASHBOARD_TOKEN` | Protects dashboard endpoints with `Authorization: Bearer <token>`. |
| `BOGGERS_DASHBOARD_HOST` | Dashboard bind host. Defaults to `127.0.0.1`. |
| `BOGGERS_DASHBOARD_PORT` | Dashboard bind port. Defaults to `8000`. |
| `X_BEARER_TOKEN` | Bearer token for the optional X/Twitter adapter. |
