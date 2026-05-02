# DriftGuard

Catch breaking data contract changes before production.

[![CI](https://github.com/aaliboyaci/DriftGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/aaliboyaci/DriftGuard/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-201%20passed-brightgreen.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-78%25-yellow.svg)](#testing)

DriftGuard is a Python CLI for detecting schema drift and breaking contract changes across APIs, databases, files, and event streams.

**Use it in CI to block unsafe schema changes before they break downstream systems.**

---

## Try It Now

```bash
pip install driftguard
driftguard demo
```

This runs a self-contained demo — no config, no database, no files needed. You'll see a simulated API schema change with breaking changes detected.

## How It Works

```
1. Take a baseline snapshot    →  driftguard snapshot --name baseline
2. Make schema changes         →  (alter table, update API spec, edit CSV...)
3. Take current snapshot       →  driftguard snapshot --name current
4. Compare                     →  driftguard diff -b baseline -c current
5. CI gate                     →  driftguard check -b baseline -c current  # exit 1 on breaking
6. Report                      →  driftguard report -b baseline -c current -f markdown
```

## Example Output

```
$ driftguard demo

DriftGuard Demo
Simulating a Pet Store API schema change...

1. Creating baseline snapshot (v1.0)...
2. Creating current snapshot (v1.1) with schema changes...
   - Pet.tag removed
   - Pet.category added (required)
   - Pet.status enum: +archived
   - Owner.id type: integer -> string
   - Owner.address added (optional)

3. Running semantic diff...

Schema Drift Report: baseline -> current
Changes: 5 | Breaking: 2 | Warnings: 2 | Info: 1

  Severity   | Resource   | Change                              | Reason
 ------------+------------+-------------------------------------+-------------------------------
  INFO       | Owner      | Field added: Owner.address (string) | Adding an optional field is
             |            |                                     | backward compatible
  [!]        | Owner      | Type changed: Owner.id              | Type widened from integer to
  WARNING    |            | (integer -> string)                 | string; some consumers may
             |            |                                     | accept this
  [X]        | Pet        | Field removed: Pet.tag (string)     | Consumers expecting this
  BREAKING   |            |                                     | field will fail
  [X]        | Pet        | Field added: Pet.category (string)  | Adding a required field may
  BREAKING   |            |                                     | break existing producers
  [!]        | Pet        | Enum values changed: Pet.status     | Enum values added: archived;
  WARNING    |            |                                     | strict consumers may not
             |            |                                     | handle new values

Summary: 5 changes | 2 breaking | 2 warning | 1 info

BREAKING CHANGES DETECTED: 2 breaking change(s)
CI check would fail (exit code 1)
```

## Installation

```bash
pip install driftguard        # pip
uv pip install driftguard     # uv
poetry add driftguard         # poetry
```

## Quick Start

```bash
# Initialize config
driftguard init

# Take baseline snapshot
driftguard snapshot --name baseline

# ... make schema changes ...

# Compare and gate
driftguard snapshot --name current
driftguard check --baseline baseline --current current
```

## Why DriftGuard?

Most schema tools focus on **one layer**: a migration linter checks SQL, an API linter checks OpenAPI specs. But real drift happens **across layers** — a Postgres column rename breaks a downstream CSV export, an API field removal crashes a partner's mobile app.

DriftGuard takes **snapshots** of your contracts at different points in time and **compares them semantically**. It understands that renaming a field is a breaking change, that widening `integer` to `number` is a warning, and that adding an optional field is safe.

**DriftGuard is not:**
- A **linter** — it doesn't check style or best practices on a single schema
- A **migration tool** — it doesn't generate ALTER TABLE or manage state
- A **runtime monitor** — it runs at build time, in CI, or on demand

It is a **contract drift detector**: snapshot, compare, classify, gate.

## Supported Sources

| Source | Status | Notes |
|---|---|---|
| PostgreSQL | **Stable** | SQLAlchemy introspection with PK/FK/unique constraints |
| OpenAPI 3.x / Swagger 2.x | **Stable** | Component schema extraction |
| JSON Schema | **Stable** | File-based type/nullable/enum/default parsing |
| CSV | **Stable** | Header + sample-based type inference |
| SQLite | **Stable** | SQLAlchemy introspection, fully tested |
| MySQL | **Stable** | SQLAlchemy introspection (requires mysqlclient/pymysql) |
| YAML | **Beta** | Data file structure inference |
| MongoDB | Planned | Sample-based schema inference |
| Kafka / Avro / Protobuf | Planned | Schema Registry integration |

## Risk Classification

| Change | Risk | Reason |
|---|---|---|
| Field removed | `breaking` | Consumers expecting this field will fail |
| Required field added | `breaking` | Validation may break existing producers |
| Column renamed | `breaking` | Effectively a remove + add |
| Type string -> integer | `breaking` | Parse behavior changes |
| FK/PK changed | `breaking` | Referential integrity affected |
| Type integer -> number | `warning` | Widening; may be acceptable |
| Nullable false -> true | `warning` | Null handling required |
| Enum value added | `warning` | Strict consumers may break |
| Constraint changed | `warning` | Validation behavior changes |
| Optional field added | `info` | Backward compatible |
| Default value changed | `info` | New records only |

**Policy modes:** `strict` (warnings become breaking), `lenient` (breaking demoted to warning), `backward_compatible`, `forward_compatible`.

## CI Integration

```yaml
# .github/workflows/drift-check.yml
- name: Install DriftGuard
  run: pip install driftguard

- name: Check for drift
  run: driftguard check --baseline baseline --current current

- name: Generate report
  if: always()
  run: driftguard report -b baseline -c current -f markdown -o drift-report.md

- name: Upload report
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: drift-report
    path: drift-report.md
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
| **Collectors** | Extract schema from Postgres, MySQL, SQLite, OpenAPI, JSON, CSV, YAML |
| **Schema** | Normalize all sources into `ContractSnapshot` → `ResourceSchema` → `FieldDef` |
| **Diff Engine** | Semantic comparison: rename detection, type/nullable/enum/constraint changes |
| **Policy Engine** | Classify each change as breaking / warning / info with configurable modes |
| **Reporters** | Terminal (Rich), JSON, Markdown, HTML |
| **CLI** | `init`, `snapshot`, `diff`, `check`, `report`, `config`, `snapshots` |

## Testing

```
201 tests | 78% coverage | Python 3.11 / 3.12 / 3.13
```

| Suite | Count | What it covers |
|---|---|---|
| Diff engine | 29 | Field add/remove/rename, type/nullable/enum/constraint changes |
| Policy engine | 25 | Risk classification, policy modes (strict/lenient/backward/forward) |
| Schema models | 22 | Pydantic models, serialization roundtrips, backward compat |
| Config | 17 | Load/save/validate, migration, notification settings |
| Store | 17 | Save/load/delete, checksum, export/import, cleanup |
| Reporters | 7 | Terminal, JSON, Markdown, HTML output |
| CLI | 17 | All commands including demo, exit codes, file outputs |
| Collectors | 18 | PostgreSQL, OpenAPI, JSON Schema, CSV, SQLite |
| Golden tests | 22 | Snapshot pairs with expected breaking/warning/info counts |

```bash
pytest                                    # run all
pytest tests/unit/test_diff_engine.py -v  # single file
pytest --cov=driftguard                   # with coverage
```

## Development

```bash
pip install -e ".[dev]"       # install in dev mode
pytest                        # 201 tests
ruff check src/ tests/        # lint
ruff format src/ tests/       # format
mypy src/                     # type check
```

## Documentation

- [Architecture](docs/architecture.md) — System design and module responsibilities
- [CLI Usage](docs/cli-usage.md) — Detailed command reference
- [Policy Rules](docs/policy-rules.md) — Risk classification rules and overrides
- [Writing Adapters](docs/adapters.md) — Guide to adding new source collectors
- [CHANGELOG](CHANGELOG.md) — Release history
- [ROADMAP](ROADMAP.md) — Planned features

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, testing, and PR guidelines.

## License

MIT
