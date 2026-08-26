.PHONY: install test lint format check

install:
	pip install -e ".[dev]"

test:
	pytest

lint:
	ruff check .

format:
	ruff format .
	ruff check --fix .

check: lint test
