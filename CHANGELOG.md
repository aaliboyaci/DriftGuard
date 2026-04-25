# Changelog

All notable changes to DriftGuard will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- pyproject.toml with hatchling build, all core + dev dependencies
- .pre-commit-config.yaml with ruff and mypy hooks
- MIT LICENSE
- ruff (lint/format) and mypy (strict type-check) configuration in pyproject.toml
- pytest configuration with testpaths and verbose output
- CLI entrypoint: `driftguard` command via `driftguard.cli.app:app`
- Full package structure: src/driftguard/ with cli, config, collectors, schema, diff, policy, reporters, store, integrations subpackages
- Test directories: tests/unit, tests/integration, tests/golden
- Example directories: postgres-demo, openapi-demo, file-schema-demo
- py.typed marker for PEP 561 type stub support
- README.md with problem statement, features, quick start, architecture, risk classification table
- Core schema models: `ContractSnapshot`, `ResourceSchema`, `FieldDef`, `FieldConstraint`, `SourceType`
- Diff event models: `FieldAdded`, `FieldRemoved`, `FieldRenamed`, `TypeChanged`, `NullableChanged`, `RequiredChanged`, `EnumValuesChanged`, `ResourceAdded`, `ResourceRemoved`
- `DiffResult` container with filtering by category and resource
- Policy models: `PolicyDecision`, `PolicyResult`, `Severity` with CI exit code support
- 42 unit tests covering all core models (schema, diff events, policy)
- Semantic diff engine: compares two snapshots producing field/resource-level DiffEvents
- Policy engine: evaluates DiffEvents with risk rules (widening transitions, nullable, enum, required)
- Golden test fixtures: baseline + breaking + clean snapshot pairs
- 95 total tests: diff engine (18), policy engine (18), golden tests (17), model tests (42)
- `LocalStore`: JSON-based snapshot read/write with versioning, list, delete
- `DriftGuardConfig`: YAML-based config with source definitions and policy overrides
- `load_config` / `save_config` / `default_config` utilities
- 116 total tests passing
- `BaseCollector` abstract interface for all source adapters
- `JsonSchemaCollector`: extracts fields from JSON Schema files (type, nullable, enum, default)
- `OpenApiCollector`: extracts component schemas from OpenAPI 3.x / Swagger 2.x specs
- `CsvCollector`: infers field types from CSV headers and sample data
- `PostgresCollector`: SQLAlchemy-based introspection with PK, FK, unique constraint detection
- Test fixtures: sample JSON Schema, OpenAPI YAML, CSV files
- 134 total tests passing
- Typer CLI with commands: `init`, `snapshot`, `diff`, `check`, `report`
- `--version` flag and auto source collector dispatch
- CI gate: `check` command exits non-zero on breaking changes
- Terminal reporter: Rich-based colored table output
- JSON reporter: machine-readable structured output
- Markdown reporter: CI artifact / PR comment format
- HTML reporter: standalone styled report page
- 152 total tests passing (11 CLI + 7 reporter tests added)

### Fixed
- pyproject.toml build-backend corrected from `hatchling.backends` to `hatchling.build`
