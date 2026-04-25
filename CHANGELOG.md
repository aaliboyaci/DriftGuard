# Changelog

All notable changes to DriftGuard will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] - 2025-04-25

### Added

#### Core
- Pydantic v2 schema models: `ContractSnapshot`, `ResourceSchema`, `FieldDef`, `FieldConstraint`, `SourceType`
- Semantic diff engine: compares snapshots producing field/resource-level `DiffEvent`s
- Policy engine: classifies changes as breaking/warning/info with type widening detection
- Diff event types: `FieldAdded`, `FieldRemoved`, `FieldRenamed`, `TypeChanged`, `NullableChanged`, `RequiredChanged`, `EnumValuesChanged`, `ResourceAdded`, `ResourceRemoved`

#### CLI
- Typer-based CLI with commands: `init`, `snapshot`, `diff`, `check`, `report`
- CI gate: `check` command exits non-zero on breaking changes
- `--version` flag and auto source collector dispatch

#### Collectors
- `BaseCollector` abstract interface for pluggable adapters
- `PostgresCollector`: SQLAlchemy-based introspection with PK, FK, unique constraints
- `OpenApiCollector`: OpenAPI 3.x / Swagger 2.x component schema extraction
- `JsonSchemaCollector`: JSON Schema file parsing with type/nullable/enum/default
- `CsvCollector`: CSV header + sample data type inference

#### Reporters
- Terminal reporter: Rich-based colored table output
- JSON reporter: machine-readable structured output
- Markdown reporter: CI artifact / PR comment format
- HTML reporter: standalone styled report page

#### Infrastructure
- `LocalStore`: versioned JSON snapshot read/write/list/delete
- `DriftGuardConfig`: YAML config with source definitions and policy overrides
- GitHub Actions CI: lint + type-check + test across Python 3.11/3.12/3.13
- Self-check demo workflow for PRs with artifact upload
- 152 tests passing (unit, golden, CLI, reporter)

#### Documentation
- Architecture guide with pipeline overview and extension points
- CLI usage reference with all commands and options
- Policy rules documentation with severity levels and overrides
- Adapter development guide for adding new source collectors
- README with badges, example output, roadmap, contributing guide

#### Examples
- openapi-demo: Pet Store API baseline vs current with breaking changes
- file-schema-demo: CSV schema drift detection demo
