.PHONY: help deps deps-orchestrator deps-shared deps-agents test test-orchestrator test-shared test-agents lint lint-orchestrator lint-shared lint-agents

help:
	@echo "Available targets:"
	@echo "  deps               - Re-lock dependencies for all components"
	@echo "  deps-orchestrator  - Re-lock dependencies for orchestrator"
	@echo "  deps-shared        - Re-lock dependencies for shared"
	@echo "  deps-agents        - Re-lock dependencies for agents"
	@echo "  test               - Run tests for all components"
	@echo "  test-orchestrator  - Run tests for orchestrator"
	@echo "  test-shared        - Run tests for shared"
	@echo "  test-agents        - Run tests for agents"
	@echo "  lint               - Run linters for all components"
	@echo "  lint-orchestrator  - Run linters for orchestrator"
	@echo "  lint-shared        - Run linters for shared"
	@echo "  lint-agents        - Run linters for agents"
	@echo "  load-test          - Run load tests against the API"

# Dependency management
deps: deps-orchestrator deps-shared deps-agents

deps-orchestrator:
	@echo "Re-locking orchestrator dependencies..."
	cd orchestrator && poetry lock --no-update
	@echo "Running tests to check for upstream compatibility..."
	$(MAKE) test-orchestrator

deps-shared:
	@echo "Re-locking shared dependencies..."
	cd shared && poetry lock --no-update
	@echo "Running tests to check for upstream compatibility..."
	$(MAKE) test-shared

deps-agents:
	@echo "Re-locking agents dependencies..."
	cd agents && poetry lock --no-update
	@echo "Running tests to check for upstream compatibility..."
	$(MAKE) test-agents

# Testing
test: test-orchestrator test-shared test-agents

test-orchestrator:
	@echo "Running orchestrator tests..."
	cd orchestrator && poetry run pytest

test-shared:
	@echo "Running shared tests..."
	cd shared && poetry run pytest

test-agents:
	@echo "Running agents tests..."
	cd agents && poetry run pytest

# Linting
lint: lint-orchestrator lint-shared lint-agents

lint-orchestrator:
	@echo "Linting orchestrator..."
	cd orchestrator && poetry run black .
	cd orchestrator && poetry run isort .
	cd orchestrator && poetry run mypy .

lint-shared:
	@echo "Linting shared..."
	cd shared && poetry run black .
	cd shared && poetry run isort .
	cd shared && poetry run mypy .

lint-agents:
	@echo "Linting agents..."
	cd agents && poetry run black .
	cd agents && poetry run isort .
	cd agents && poetry run mypy .

# Load testing
load-test:
	@echo "Running load tests..."
	k6 run orchestrator/tests/load/basic_load_test.js
