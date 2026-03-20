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
