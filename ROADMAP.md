# DriftGuard Roadmap

## v0.1.0 — MVP (Completed)

- Semantic diff engine with field-level change detection
- Policy engine with breaking / warning / info classification
- CLI: `init`, `snapshot`, `diff`, `check`, `report`
- Collectors: PostgreSQL, OpenAPI, JSON Schema, CSV
- Reporters: Terminal (Rich), JSON, Markdown, HTML
- Local JSON snapshot store
- GitHub Actions CI (Python 3.11 / 3.12 / 3.13)
- 152 tests passing

## v0.1.1 — Stabilization (In Progress)

- README polish: "Why DriftGuard?", real CLI output, scope clarification
- Community files: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, ROADMAP
- GitHub issue templates
- CHANGELOG format improvements

## v0.2.0 — Config & Snapshot v2

- Config schema versioning and migration
- `driftguard config validate` and `driftguard config print` commands
- Snapshot metadata: `git_commit_sha`, `branch_name`, `created_by`, `tags`
- Snapshot backward compatibility guarantees

## v0.3.0 — Diff & Policy Engine Enhancements

- Fuzzy field rename detection
- Nested object and array schema diff
- Default value, constraint, index, FK, PK change events
- Policy modes: strict, lenient, backward-compatible, forward-compatible
- Resource-level and field-level policy overrides
- Configurable type widening rules

## v0.4.0 — New Collectors

- MongoDB schema inference
- MySQL / MariaDB / SQLite / SQL Server
- BigQuery / Snowflake / Redshift / DuckDB
- Parquet full support, Excel, NDJSON, XML, YAML

## v0.5.0 — Event & Streaming Support

- Avro schema collector
- Protobuf collector
- Kafka Schema Registry integration
- AsyncAPI and CloudEvents support
- Event key/value schema separation

## v0.6.0 — API Contract Deep Diff

- OpenAPI request/response body diff
- Path, method, query parameter, header contract changes
- Status code removal detection
- Deprecated endpoint detection

## v0.7.0 — Storage & CLI UX

- S3, Azure Blob, GCS snapshot backends
- Snapshot compression, checksum, retention policies
- `driftguard doctor`, `sources list`, `snapshots list/show/delete`
- `driftguard diff --only-breaking`, `--resource`, `--field` filters
- `driftguard policy explain` command

## v0.8.0 — Reporters & CI/CD

- SARIF, JUnit XML, Slack, Teams, webhook reporters
- GitHub PR comment reporter with inline annotations
- GitLab CI, Bitbucket Pipelines, Azure DevOps integrations
- `driftguard approve` command for exception management

## v0.9.0 — Performance & Security

- Parallel collection, incremental diff, large snapshot handling
- Snapshot encryption, RBAC model, audit logging
- OpenTelemetry tracing and Prometheus metrics

## v1.0.0 — Enterprise Governance

- Multi-project governance dashboard
- Cross-project dependency tracking
- SLA compliance rules and automated escalation
- Enterprise deployment guide
