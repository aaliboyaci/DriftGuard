# DriftGuard

Catch breaking data contract changes before production.

[![CI](https://github.com/aaliboyaci/DriftGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/aaliboyaci/DriftGuard/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![PyPI](https://img.shields.io/pypi/v/driftguard-contracts.svg)](https://pypi.org/project/driftguard-contracts/)
[![Tests](https://img.shields.io/badge/tests-576%20passed-brightgreen.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-89%25-brightgreen.svg)](#testing)

DriftGuard snapshots your schemas, compares them semantically, classifies each change by risk, and fails CI when something breaks. Supports APIs, databases, files, and nested JSON payloads — with event stream support planned.

```
1. Detect breaking contract changes
2. Explain why they are risky
3. Show them in CI / PR comments
4. Allow controlled exceptions (suppression / waiver)
5. Support APIs, databases, JSONB, files, and ORM models
```

---

## Try It Now

```bash
pip install driftguard-contracts
driftguard demo
```

No config, no database needed. You'll see a simulated API schema change with breaking changes detected.

## How It Works

```
driftguard snapshot --name baseline      # take baseline
# ... make schema changes ...
driftguard snapshot --name current       # take current
driftguard check -b baseline -c current  # exit 1 on breaking
driftguard report -b baseline -c current -f markdown
```

## Example Output

```
$ driftguard demo

Schema Drift Report: baseline -> current
Changes: 5 | Breaking: 2 | Warnings: 2 | Info: 1

  BREAKING   Pet        Field removed: Pet.tag (string)
  BREAKING   Pet        Field added: Pet.category (string, required)
  WARNING    Owner      Type changed: Owner.id (integer -> string)
  WARNING    Pet        Enum values changed: Pet.status (+archived)
  INFO       Owner      Field added: Owner.address (string, optional)

BREAKING CHANGES DETECTED: 2 breaking change(s)
CI check would fail (exit code 1)
```

## Key Capabilities

### OpenAPI Deep Diff

```bash
driftguard openapi diff baseline.yaml current.yaml
driftguard openapi diff baseline.yaml current.yaml -f pr -o comment.md
```

Detects path/method removals, parameter changes, request/response body changes, status code changes, and deprecated endpoints. See [docs/cli-usage.md](docs/cli-usage.md).

### JSONB / Nested Contract Diff

```bash
driftguard nested infer samples.json --output baseline.json
driftguard nested infer new-samples.json --output current.json
driftguard nested diff baseline.json current.json
```

Confidence-aware severity: high confidence removals = breaking, low confidence = warning. No raw values stored. See [docs/jsonb-nested-diff.md](docs/jsonb-nested-diff.md).

### Snapshot Management

```bash
driftguard snapshots list
driftguard snapshots export -n v1 -o backup.json.gz --compress
driftguard snapshots import backup.json.gz
driftguard snapshots cleanup --keep 5
```

## Installation

```bash
pip install driftguard-contracts        # pip
uv pip install driftguard-contracts     # uv
poetry add driftguard-contracts         # poetry
```

## Supported Sources

**Stable:** PostgreSQL, MySQL, SQLite, OpenAPI 3.x/Swagger 2.x, JSON Schema, CSV, JSONB nested diff
**Beta:** YAML, Sequelize, Prisma, S3 backend, Suppression/Waiver
**Experimental:** Cross-service registry
**Planned:** Parquet, MongoDB, Kafka/Avro/Protobuf

See [docs/supported-sources.md](docs/supported-sources.md) for stability matrix.

## Risk Classification

| Change | Risk |
|---|---|
| Field removed / renamed | `breaking` |
| Required field added | `breaking` |
| Type narrowing (string -> integer) | `breaking` |
| Type widening (integer -> number) | `warning` |
| Enum value added | `warning` |
| Optional field added | `info` |

**Policy modes:** `strict`, `lenient`, `backward_compatible`, `forward_compatible`. Full rules: [docs/policy-rules.md](docs/policy-rules.md).

## CI Integration

```yaml
# .github/workflows/drift-check.yml
- run: pip install driftguard-contracts
- run: driftguard check --baseline baseline --current current
- run: driftguard report -b baseline -c current -f pr -o comment.md
  if: always()
```

PR comment format, step summary, annotations: [docs/github-actions.md](docs/github-actions.md).

## Why DriftGuard?

Most schema tools focus on **one layer**. DriftGuard works **across layers** — a Postgres column rename breaks a downstream CSV export, an API field removal crashes a mobile app.

It is a **contract drift detector**: snapshot, compare, classify, gate.

**Not** a linter, migration tool, or runtime monitor.

## Testing

```
576 tests | 89% coverage | Python 3.11 / 3.12 / 3.13
```

```bash
pytest                        # run all
pytest --cov=driftguard       # with coverage
```

## Development

```bash
pip install -e ".[dev]"
pytest && ruff check src/ tests/ && mypy src/
```

## Documentation

- [Quick Start](docs/quickstart.md) — 5-minute setup
- [CLI Usage](docs/cli-usage.md) — Command reference
- [Supported Sources](docs/supported-sources.md) — Collectors, stability matrix
- [Policy Rules](docs/policy-rules.md) — Risk classification and overrides
- [JSONB/Nested Diff](docs/jsonb-nested-diff.md) — Nested contract diffing
- [GitHub Actions](docs/github-actions.md) — PR comments, annotations
- [CI Gate](docs/ci-gate.md) — CI/CD integration
- [Architecture](docs/architecture.md) — System design
- [Writing Adapters](docs/adapters.md) — Custom collectors
- [Verification Report](docs/verification.md) — Real CLI outputs
- [FAQ](docs/faq.md) | [Troubleshooting](docs/troubleshooting.md) | [CHANGELOG](CHANGELOG.md) | [ROADMAP](ROADMAP.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
