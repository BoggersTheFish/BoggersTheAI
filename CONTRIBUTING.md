# Contributing to BoggersTheAI

Thanks for helping improve the living TS-OS.

## Development setup

1. Fork and clone the repository.
2. Create a virtual environment.
3. Install editable + dev dependencies:

```bash
pip install -e ".[dev]"
```

## Quality checks

Run these before opening a PR:

```bash
black .
isort .
ruff check --fix .
pytest -q
```

## Pull request guidelines

- Keep changes focused and modular.
- Add or update tests for behavior changes.
- Update docs/config when introducing new features.
- Keep runtime safety defaults intact.

## Commit style

- Prefer short imperative subjects.
- Include rationale in body when needed.

## Reporting issues

Use the issue templates for bug reports and feature requests.
# Contributing to BoggersTheAI

## Development Setup

1. Create a venv:
   - `python -m venv .venv`
   - `.\.venv\Scripts\Activate.ps1` (Windows PowerShell)
2. Run quick validation:
   - `python -m compileall BoggersTheAI`

## Code Guidelines

- Keep modules decoupled and protocol-driven.
- Keep synthesis grounded to retrieved context.
- Prefer small, testable functions with deterministic behavior.
- Avoid introducing heavy dependencies unless clearly justified.

## Pull Request Expectations

- Explain why the change is needed.
- List modified modules and expected behavior changes.
- Include validation steps you ran.
- Add tests for non-trivial behavior changes when possible.

## Security

- Never commit secrets (`.env`, keys, tokens).
- Keep runtime config safe for public repositories.
