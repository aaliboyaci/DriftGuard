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

## v0.2.0 — Platform Hardening (Completed)

- **Config v2:** `project_name`, `environment`, `owner_team`, `notification`, schema versioning with auto-migration
- **Config CLI:** `driftguard config validate`, `driftguard config print`
- **Snapshot v2:** `created_by`, `git_commit_sha`, `branch_name`, `source_hash`, `collector_version`, `environment`, `tags`, `description` — backward compatible
- **Snapshot store:** SHA-256 checksum, gzip export/import, retention-based cleanup, snapshot info
- **Snapshot CLI:** `driftguard snapshots list`, `snapshots show`, `snapshots delete`
- **Diff engine:** fuzzy field rename detection (SequenceMatcher)
- **Diff events:** `DefaultValueChanged`, `ConstraintChanged`, `IndexChanged`, `ForeignKeyChanged`, `PrimaryKeyChanged`
- **Diff engine:** constraint diffing — PK, unique, FK, max_length, min_value, max_value, pattern
- **Diff CLI:** `--only-breaking` and `--resource` filter flags
- **Policy modes:** `strict`, `lenient`, `backward_compatible`, `forward_compatible`
- **Collectors:** MySQL (SQLAlchemy), SQLite (SQLAlchemy), YAML data file inference
- Community files: CONTRIBUTING, CODE_OF_CONDUCT, SECURITY, ROADMAP
- GitHub issue templates, release notes template, enterprise config example
- README: "Why DriftGuard?", installation options, real CLI output, versioning section
- PyPI metadata, keywords, and classifiers improved
- 190 tests passing

## v0.3.0 — Event & Streaming (Planned)

- Avro schema collector
- Protobuf collector
- Kafka Schema Registry integration
- AsyncAPI and CloudEvents support
- Event key/value schema separation
- Event compatibility mode

## v0.4.0 — API Contract Deep Diff (Planned)

- OpenAPI request/response body diff
- Path, method, query parameter, header contract changes
- Status code removal detection
- Deprecated endpoint detection
- Breaking API change report

## v0.5.0 — Reporters & CI/CD (Planned)

- SARIF, JUnit XML, CSV reporters
- GitHub PR comment reporter with inline annotations
- GitLab CI, Bitbucket Pipelines, Azure DevOps examples
- `driftguard approve` command for breaking change exceptions
- GitHub Actions summary output

## v0.6.0 — Performance & Observability (Planned)

- Parallel collector execution with timeout and retry
- Hash-based incremental diff optimization
- Large snapshot benchmarks (10k, 100k fields)
- Structured logging with JSON mode
- `--verbose` and `--quiet` mode improvements
- OpenTelemetry tracing interface

## v0.7.0 — Security & Compliance (Planned)

- Secret masking in reports and logs
- DB connection string redaction
- Environment variable based secret loading
- Dependency vulnerability scanning (Bandit)
- SBOM generation
- Supply chain security documentation

## v1.0.0 — Enterprise Governance (Planned)

- Ownership metadata and team-based approval
- Breaking change waiver mechanism with expiry
- Audit log and policy violation history
- Risk trend reporting
- Compliance mode documentation
- Enterprise deployment guide
