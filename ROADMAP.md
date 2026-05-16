# DriftGuard Roadmap

## v0.1.0 — MVP (Released)

- Semantic diff engine with field-level change detection
- Policy engine with breaking / warning / info classification
- CLI: `init`, `snapshot`, `diff`, `check`, `report`
- Collectors: PostgreSQL, OpenAPI, JSON Schema, CSV
- Reporters: Terminal (Rich), JSON, Markdown, HTML
- Local JSON snapshot store
- GitHub Actions CI (Python 3.11 / 3.12 / 3.13)

## v0.2.x — Platform Hardening (Released)

- Config v2: project metadata, environment, notification settings, schema migration
- Snapshot v2: git SHA, branch, tags, description — backward compatible
- Snapshot store: checksum, gzip export/import, cleanup, info
- CLI: `config validate/print`, `snapshots list/show/delete`, `diff --only-breaking --resource`
- Diff engine: fuzzy rename detection, constraint/FK/PK/default value change events
- Policy modes: strict, lenient, backward-compatible, forward-compatible
- Collectors: MySQL, SQLite, YAML
- Demo command with `--format` and `--output`
- 85% test coverage, 234 tests
- PyPI publish workflow, docs, case studies

## v0.3.x — OpenAPI Deep Diff & PR Experience (Released)

- OpenAPI deep diff: path, method, parameter, request body, response body, status code
- 10 OpenAPI-specific event types with correct request vs response semantics
- `driftguard openapi diff` command
- PR comment reporter (`--format pr`) with truncation and collapsible sections
- GitHub Actions PR workflow example
- Swagger 2.x backward compatibility
- 322 tests

## Future

- Avro, Protobuf, Kafka Schema Registry collectors
- AsyncAPI and CloudEvents support
- SARIF reporter for GitHub Code Scanning
- `driftguard approve` for breaking change waivers
- Remote snapshot stores (S3, GCS)
- OpenTelemetry observability integration
