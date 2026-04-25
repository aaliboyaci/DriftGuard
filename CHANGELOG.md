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

### Fixed
- pyproject.toml build-backend corrected from `hatchling.backends` to `hatchling.build`
