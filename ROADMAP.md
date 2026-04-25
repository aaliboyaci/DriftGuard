# DriftGuard Roadmap

## v0.1.0 — MVP (Released)

- Semantic diff engine with field-level change detection
- Policy engine with breaking / warning / info classification
- CLI: `init`, `snapshot`, `diff`, `check`, `report`
- Collectors: PostgreSQL, OpenAPI, JSON Schema, CSV
- Reporters: Terminal (Rich), JSON, Markdown, HTML
- Local JSON snapshot store
- GitHub Actions CI (Python 3.11 / 3.12 / 3.13)

## v0.2.0 — Platform Hardening (Released)

- Config v2: project metadata, environment, notification settings, schema migration
- Snapshot v2: git SHA, branch, tags, description — backward compatible
- Snapshot store: checksum, gzip export/import, cleanup, info
- CLI: `config validate/print`, `snapshots list/show/delete`, `diff --only-breaking --resource`
- Diff engine: fuzzy rename detection, constraint/FK/PK/default value change events
- Policy modes: strict, lenient, backward-compatible, forward-compatible
- Collectors: MySQL, SQLite, YAML

## v0.3.0 — Event & API Contracts (Next)

- Avro schema collector
- Protobuf schema collector
- Kafka Schema Registry integration
- AsyncAPI and CloudEvents support
- OpenAPI request/response body deep diff
- Path/method/header/status code change detection

## v0.4.0 — Reporters & CI/CD

- SARIF, JUnit XML, CSV reporters
- GitHub PR comment reporter
- GitLab CI, Bitbucket Pipelines examples
- `driftguard approve` for breaking change exceptions

## v0.5.0 — Performance, Security & Observability

- Parallel collector execution
- Large snapshot benchmarks
- Secret masking in reports
- Structured logging, OpenTelemetry interface

## v1.0.0 — Enterprise Governance

- Team ownership and approval workflows
- Breaking change waiver mechanism
- Audit log and policy violation history
- Compliance mode and enterprise deployment guide
