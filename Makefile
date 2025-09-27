# Makefile for RAGFlow MCP Server

.PHONY: help install install-dev test test-unit test-integration lint format type-check clean build upload docs

# Default target
help:
	@echo "Available targets:"
	@echo "  install      - Install the package"
	@echo "  install-dev  - Install in development mode with dev dependencies"
	@echo "  test         - Run all tests"
	@echo "  test-unit    - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code with black and isort"
	@echo "  type-check   - Run type checking with mypy"
	@echo "  clean        - Clean build artifacts"
	@echo "  build        - Build distribution packages"
	@echo "  upload       - Upload to PyPI (requires credentials)"
	@echo "  docs         - Generate documentation"

# Installation targets
install:
	pip install .

install-dev:
	pip install -e ".[dev]"

# Testing targets
test:
	pytest

test-unit:
	pytest tests/unit/

test-integration:
	pytest tests/integration/

test-cov:
	pytest --cov=ragflow_mcp_server --cov-report=html --cov-report=term

# Code quality targets
lint:
	flake8 ragflow_mcp_server/
	flake8 tests/

format:
	black ragflow_mcp_server/ tests/
	isort ragflow_mcp_server/ tests/

type-check:
	mypy ragflow_mcp_server/

# Quality check all
check: format lint type-check test

# Build and distribution targets
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

build: clean
	python -m build

upload: build
	python -m twine upload dist/*

upload-test: build
	python -m twine upload --repository testpypi dist/*

# Documentation targets
docs:
	@echo "Documentation is in README.md and examples/"
	@echo "For API docs, run: python -c 'import ragflow_mcp_server; help(ragflow_mcp_server)'"

# Development helpers
run:
	python -m ragflow_mcp_server

run-debug:
	RAGFLOW_LOG_LEVEL=DEBUG python -m ragflow_mcp_server

example:
	python examples/usage_examples.py

# Docker targets (if needed)
docker-build:
	docker build -t ragflow-mcp-server .

docker-run:
	docker run --rm -it ragflow-mcp-server

# Pre-commit setup
pre-commit:
	pre-commit install
	pre-commit run --all-files