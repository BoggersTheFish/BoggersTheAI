.PHONY: test lint format run dashboard install

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .
	black --check .
	isort --check .

format:
	black .
	isort .
	ruff check --fix .

run:
	boggers

dashboard:
	dashboard-start
