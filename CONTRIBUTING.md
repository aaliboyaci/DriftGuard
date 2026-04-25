# Contributing to DriftGuard

Thank you for considering contributing to DriftGuard! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/aaliboyaci/DriftGuard.git
cd DriftGuard

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install in development mode
pip install -e ".[dev]"

# Verify everything works
pytest
ruff check src/ tests/
mypy src/
```

## Making Changes

1. **Fork** the repository and create a feature branch from `main`
2. **Write tests** for any new functionality
3. **Run the full test suite** before submitting:
   ```bash
   pytest
   ruff check src/ tests/
   ruff format --check src/ tests/
   mypy src/
   ```
4. **Update CHANGELOG.md** under `[Unreleased]` if your change is user-facing
5. **Submit a pull request** with a clear description of the change

## Code Style

- **Formatter:** ruff (line length 120)
- **Linter:** ruff
- **Type checker:** mypy (strict mode)
- **Python:** 3.11+ with modern type annotations

Run `ruff format src/ tests/` to auto-format before committing.

## Adding a New Collector

See [docs/adapters.md](docs/adapters.md) for a step-by-step guide. In short:

1. Create `src/driftguard/collectors/your_collector.py`
2. Implement the `BaseCollector` interface
3. Register it in `cli/app.py` `_create_collector()`
4. Add the source type to `schema/models.py` `SourceType`
5. Write unit tests with fixture files

## Test Structure

| Directory | Purpose |
|---|---|
| `tests/unit/` | Fast, isolated tests for individual components |
| `tests/golden/` | Snapshot pairs with expected outputs (regression) |
| `tests/integration/` | Tests requiring external services (Postgres via Docker) |

### Running specific tests

```bash
# Single file
pytest tests/unit/test_diff_engine.py

# Single test
pytest tests/unit/test_diff_engine.py::TestDiffEngineFields::test_type_changed -v

# With coverage
pytest --cov=driftguard
```

## Pull Request Guidelines

- Keep PRs focused on a single change
- Include tests for new functionality
- Update documentation if behavior changes
- Ensure CI passes (lint + type-check + tests across Python 3.11/3.12/3.13)

## Reporting Issues

Use [GitHub Issues](https://github.com/aaliboyaci/DriftGuard/issues) to report bugs or request features. Please include:

- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Python version and OS
- DriftGuard version (`driftguard --version`)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
