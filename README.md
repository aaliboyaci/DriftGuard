# DriftGuard

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

## Features

- **Semantic diff** - Not just text diff: detects field removed, type narrowed, nullable changed, enum expanded
- **Risk classification** - Every change is classified as `breaking`, `warning`, or `info`
- **Multiple sources** - PostgreSQL, OpenAPI/JSON Schema, JSON payloads, CSV/Parquet files
- **CI gate** - Fails pipeline on breaking changes; reports warnings
- **Multiple report formats** - Terminal (Rich), JSON, Markdown, HTML
- **Versioned snapshots** - Baseline and current snapshots stored and compared

## Quick Start

```bash
# Install
pip install driftguard

# Initialize config in your project
driftguard init

# Take a baseline snapshot
driftguard snapshot --name baseline

# ... make schema changes ...

# Take current snapshot and compare
driftguard snapshot --name current
driftguard diff --baseline baseline --current current

# CI gate: exits non-zero on breaking changes
driftguard check --baseline baseline
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
| Type string → integer | `breaking` | Parse and validation behavior changes |
| Type integer → number | `warning` | May be acceptable but carries risk |
| Nullable false → true | `warning` | Consumers without null handling may fail |
| Enum value added | `warning` | Strict enum consumers may break |
| Optional field added | `info` | Backward compatible |

## Supported Sources

| Source | Status |
|---|---|
| PostgreSQL | MVP |
| OpenAPI / JSON Schema | MVP |
| JSON payload | MVP |
| CSV / Parquet | MVP |
| MongoDB | Planned |
| Kafka / Avro | Planned |

## Development

```bash
# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint & format
ruff check src/ tests/
ruff format src/ tests/

# Type check
mypy src/
```

## Tech Stack

- **Python 3.11+** with modern typing
- **Typer** + **Rich** for CLI
- **Pydantic v2** for validation
- **SQLAlchemy** + **psycopg** for DB introspection
- **pytest** for testing
- **ruff** + **mypy** for code quality

## License

MIT
