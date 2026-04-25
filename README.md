# DriftGuard

[![CI](https://github.com/aaliboyaci/DriftGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/aaliboyaci/DriftGuard/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Enterprise Data Contract & Schema Drift Monitor**

DriftGuard is a Python CLI tool that detects schema and data contract drift across databases, APIs and files before it breaks production pipelines. It compares current contracts with a saved baseline, classifies changes by risk, and fails CI when a breaking change is detected.

---

## The Problem

In large systems, data structures don't live in one place. The same domain data exists in database tables, REST API responses, event payloads, BI exports, and ETL jobs. When one team makes a seemingly small change, another team's system can break silently.

**Typical breakage examples:**
- A column is renamed in a table; the ETL job crashes at night
- An "optional" field is removed from an API response; mobile integration breaks
- An integer field becomes a string; dashboard aggregation produces wrong results
- A non-nullable field becomes nullable; downstream validation behavior changes

The worst part: these changes don't fail at deploy time. Errors surface hours later in data jobs, partner integrations, or reporting layers.

## Why DriftGuard?

Most schema tools focus on **one layer**: a database migration linter checks SQL, an API linter checks OpenAPI specs. But real drift happens **across layers** — a Postgres column rename breaks a downstream CSV export, an API field removal crashes a partner's mobile app.

DriftGuard doesn't lint individual schemas. It **takes snapshots** of your contracts at different points in time and **compares them semantically**. It understands that renaming a field is a breaking change, that widening `integer` to `number` is a warning, and that adding an optional field is safe. It works across Postgres, OpenAPI, JSON Schema, and CSV — giving you one unified view of contract drift.

**DriftGuard is not:**
- A **linter** — it doesn't check style or best practices on a single schema
- A **migration tool** — it doesn't generate ALTER TABLE or manage state
- A **runtime monitor** — it runs at build time, in CI, or on demand

It is a **contract drift detector**: snapshot, compare, classify, gate.

**Use DriftGuard when:**
- Multiple teams consume the same data sources and nobody owns the contract
- Schema changes deploy without review and break downstream at 2 AM
- You need a CI gate that blocks breaking changes before they merge
- You want to track how your data contracts evolve over time

## Features

- **Semantic diff** - Not just text diff: detects field removed, type narrowed, nullable changed, enum expanded
- **Risk classification** - Every change is classified as `breaking`, `warning`, or `info`
- **Multiple sources** - PostgreSQL, OpenAPI/JSON Schema, JSON payloads, CSV/Parquet files
- **CI gate** - Fails pipeline on breaking changes; reports warnings
- **Multiple report formats** - Terminal (Rich), JSON, Markdown, HTML
- **Versioned snapshots** - Baseline and current snapshots stored and compared

## Installation

```bash
# pip
pip install driftguard

# uv
uv pip install driftguard

# poetry
poetry add driftguard
```

## Quick Start

```bash
# Initialize config in your project
driftguard init

# Take a baseline snapshot
driftguard snapshot --name baseline

# ... make schema changes ...

# Take current snapshot and compare
driftguard snapshot --name current
driftguard diff --baseline baseline --current current

# CI gate: exits non-zero on breaking changes
driftguard check --baseline baseline --current current
```

## Example Output

Real output from `driftguard check` on the [OpenAPI demo](examples/openapi-demo/):

```
$ driftguard check --baseline baseline --current current

Schema Drift Report: baseline -> current
Changes: 5 | Breaking: 2 | Warnings: 2 | Info: 1

+-------------------------------------------------------------------------------------------------------------------+
| Severity   | Resource   | Change                                   | Reason                                      |
|------------+------------+------------------------------------------+---------------------------------------------|
|  INFO      | Owner      | Field added: Owner.address (string)      | Adding an optional field is backward        |
|            |            |                                          | compatible                                  |
| [!]        | Owner      | Type changed: Owner.id (integer ->       | Type widened from integer to string;        |
| WARNING    |            | string)                                  | some consumers may accept this              |
| [X]        | Pet        | Field removed: Pet.tag (string)          | Consumers expecting this field will fail    |
| BREAKING   |            |                                          |                                             |
| [X]        | Pet        | Field added: Pet.category (string)       | Adding a required field may break existing  |
| BREAKING   |            |                                          | producers/consumers                         |
| [!]        | Pet        | Enum values changed: Pet.status          | Enum values added: archived; strict         |
| WARNING    |            |                                          | consumers may not handle new values         |
+-------------------------------------------------------------------------------------------------------------------+

BREAKING CHANGES DETECTED: 2 breaking change(s)
```

## Architecture

```
Data Sources ──> Collectors ──> Normalizer ──> Snapshot Store
                                                     │
                                              Diff Engine
                                                     │
                                             Policy Engine
                                                     │
                                         Reporters / CI Gate
```

| Layer | Responsibility |
|---|---|
| **CLI** | User commands: `init`, `snapshot`, `diff`, `check`, `report` |
| **Config** | YAML-based source and policy configuration |
| **Collectors** | Extract schema from Postgres, OpenAPI, JSON, CSV, Parquet |
| **Schema** | Normalize all sources into a common internal model |
| **Diff Engine** | Compare two snapshots, produce semantic change events |
| **Policy Engine** | Classify each change as breaking / warning / info |
| **Reporters** | Output as terminal table, JSON, Markdown, or HTML |

## Risk Classification

| Change | Risk Level | Reason |
|---|---|---|
| Field removed | `breaking` | Consumers expecting this field will fail |
| Required field added | `breaking` | Producer/consumer validation may break |
| Column renamed | `breaking` | Effectively a remove + add |
| Type string -> integer | `breaking` | Parse and validation behavior changes |
| Type integer -> number | `warning` | May be acceptable but carries risk |
| Nullable false -> true | `warning` | Consumers without null handling may fail |
| Enum value added | `warning` | Strict enum consumers may break |
| Optional field added | `info` | Backward compatible |

## Supported Sources

| Source | Status |
|---|---|
| PostgreSQL | Supported |
| OpenAPI / JSON Schema | Supported |
| JSON payload | Supported |
| CSV / Parquet | Supported |
| MongoDB | Planned |
| Kafka / Avro | Planned |

## CI Integration (GitHub Actions)

```yaml
- name: Install DriftGuard
  run: pip install driftguard

- name: Check for drift
  run: driftguard check --baseline baseline --current current

- name: Generate report
  if: always()
  run: driftguard report -b baseline -c current -f markdown -o drift-report.md
```

## Development

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests (152 tests)
pytest

# Run a single test
pytest tests/unit/test_diff_engine.py::TestDiffEngineFields::test_type_changed -v

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/
```

## Documentation

- [Architecture](docs/architecture.md) - System design and module responsibilities
- [CLI Usage](docs/cli-usage.md) - Detailed command reference
- [Policy Rules](docs/policy-rules.md) - Risk classification rules and overrides
- [Writing Adapters](docs/adapters.md) - Guide to adding new source collectors

## Tech Stack

- **Python 3.11+** with modern typing
- **Typer** + **Rich** for CLI
- **Pydantic v2** for validation
- **SQLAlchemy** + **psycopg** for DB introspection
- **pytest** for testing
- **ruff** + **mypy** for code quality
- **GitHub Actions** for CI

## Versioning

DriftGuard follows [Semantic Versioning](https://semver.org/):

- **MAJOR** (1.0.0) — incompatible API or config changes
- **MINOR** (0.2.0) — new features, collectors, or reporters (backward compatible)
- **PATCH** (0.1.1) — bug fixes, docs, and polish (no behavior change)

See [CHANGELOG.md](CHANGELOG.md) for release history and [ROADMAP.md](ROADMAP.md) for the full plan.

## Roadmap

### v0.1.0 — Scope Completed
- Core diff engine with semantic change detection
- Policy engine with risk classification (breaking / warning / info)
- CLI with init, snapshot, diff, check, report commands
- Collectors: PostgreSQL, OpenAPI, JSON Schema, CSV
- Reporters: Terminal, JSON, Markdown, HTML
- 152 tests passing across Python 3.11 / 3.12 / 3.13
- GitHub Actions CI with lint, type-check, and test matrix

### v0.2.0 (Planned)
- MongoDB schema inference adapter
- Kafka / Avro / Schema Registry support
- S3 snapshot store backend
- Policy override and allowlist system
- PR comment reporter

### v1.0.0 (Future)
- Slack / webhook alerting
- Trend reporting
- Web dashboard

## Contributing

1. Fork the repo
2. Create a feature branch
3. Add tests for new functionality
4. Run `pytest` and `ruff check`
5. Submit a PR

See [Writing Adapters](docs/adapters.md) for adding new source collectors.

## License

MIT
