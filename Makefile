.PHONY: demo install dev test lint format typecheck check clean

demo:  ## Run the built-in demo
	driftguard demo

install:  ## Install in production mode
	pip install .

dev:  ## Install in development mode
	pip install -e ".[dev]"

test:  ## Run all tests
	pytest tests/ -v

coverage:  ## Run tests with coverage
	pytest tests/ --cov=driftguard --cov-report=term-missing

lint:  ## Run linter
	ruff check src/ tests/

format:  ## Format code
	ruff format src/ tests/

typecheck:  ## Run type checker
	mypy src/

check: lint format typecheck test  ## Run all quality checks

clean:  ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info src/*.egg-info .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
