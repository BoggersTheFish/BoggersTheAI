.PHONY: help install fmt fmt-check lint typecheck test unit-test integration-test smoke benchmark docs demo clean check-architecture

PYTHON ?= python3
VENV_PYTHON ?= .venv/bin/python
VENV_PYTEST ?= .venv/bin/pytest

help:
	@echo "Thinking System Monorepo Management Commands:"
	@echo "  make install           - Install thinking-system package and dev dependencies"
	@echo "  make fmt               - Format codebase with black and isort"
	@echo "  make fmt-check         - Check formatting (black --check, isort --check)"
	@echo "  make lint              - Lint codebase with ruff"
	@echo "  make typecheck         - Type check core packages with mypy"
	@echo "  make test              - Run full test suite"
	@echo "  make unit-test         - Run fast unit tests (excluding slow/network)"
	@echo "  make integration-test  - Run integration tests"
	@echo "  make smoke             - Run deterministic kernel smoke demo"
	@echo "  make benchmark         - Validate benchmark suite"
	@echo "  make docs              - Validate documentation links and consistency"
	@echo "  make demo              - Run canonical offline demonstration (ts demo --json)"
	@echo "  make check-architecture- Verify dependency direction rules"
	@echo "  make clean             - Clean build, cache, and temporary files"

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e ".[dev]"

fmt:
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

fmt-check:
	$(PYTHON) -m black --check .
	$(PYTHON) -m isort --check .

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy core/kernel --explicit-package-bases --ignore-missing-imports --follow-imports=skip --no-error-summary

test:
	$(PYTHON) -m pytest

unit-test:
	$(PYTHON) -m pytest -m "not slow and not network"

integration-test:
	$(PYTHON) -m pytest tests/test_integration.py tests/test_bogvm_wave_payload.py

smoke:
	$(PYTHON) -m core.kernel.demo --json

benchmark:
	$(PYTHON) scripts/run_benchmarks.py --smoke

docs:
	$(PYTHON) tools/check_docs.py

demo:
	$(PYTHON) -m thinking_system.apps.cli.main demo --json

check-architecture:
	$(PYTHON) tools/check_architecture.py

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
