# Contributing to BoggersTheAI

Thanks for helping improve the living TS-OS.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment:

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

3. Install editable + dev dependencies:

```bash
pip install -e ".[dev]"
```

4. Verify the install:

```bash
python -m compileall BoggersTheAI
pytest -q
```

## Quality checks

Run these before opening a PR:

```bash
black .
isort .
ruff check --fix .
mypy BoggersTheAI --ignore-missing-imports
pytest -q
```

## Project structure

| Directory | Purpose |
|-----------|---------|
| `core/` | Graph engine, wave, query processing, config, logging, events, plugins, health, metrics |
| `adapters/` | Data ingestion (Wikipedia, RSS, HN, Vault, Markdown, X API) |
| `entities/` | Consolidation, insight, synthesis, inference routing |
| `tools/` | Search, calc, code execution, file reading |
| `multimodal/` | Voice in/out, image captioning |
| `interface/` | Runtime composition, CLI, API |
| `mind/` | TUI (Rich) |
| `dashboard/` | FastAPI observability endpoints |
| `tests/` | Pytest suite |

## Pull request guidelines

- Keep changes focused and modular.
- Add or update tests for behavior changes.
- Update docs/config when introducing new features.
- Keep runtime safety defaults intact (`safety_dry_run: true` in config).
- Prefer protocol-driven design over concrete dependencies.
- Avoid introducing heavy dependencies unless clearly justified.

## Commit style

- Prefer short imperative subjects (e.g. "Add graph metrics endpoint").
- Include rationale in body when the change is non-obvious.

## Configuration

All tuning knobs live in `config.yaml`. Do not hardcode magic numbers — use the config surface or add a new config key with a sensible default.

## Security

- Never commit secrets (`.env`, keys, tokens).
- Keep `config.yaml` safe for public repositories.
- Use environment variables for sensitive values (`X_BEARER_TOKEN`, `BOGGERS_DASHBOARD_TOKEN`).

## Reporting issues

Use the [issue templates](https://github.com/BoggersTheFish/BoggersTheAI/issues/new/choose) for bug reports and feature requests.
