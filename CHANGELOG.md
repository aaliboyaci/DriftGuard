# Changelog

All notable changes to DriftGuard will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v0.2.1

### Added
- `driftguard demo --format` option: terminal (default), json, markdown, html
- `driftguard demo --output` option: save report to file
- Demo summary line: breaking/warning/info counts in all formats
- Clear CI verdict message at end of demo output
- `make demo-html` Makefile target for HTML report generation

## [0.2.0] - 2025-04-25

Config v2, Snapshot v2, new collectors, diff engine and policy engine enhancements, CLI UX improvements.

### Added
- **Config v2:** `project_name`, `environment`, `owner_team`, `notification` settings, `schema_version` with auto-migration
- **Config CLI:** `driftguard config validate` and `driftguard config print` subcommands
- **Snapshot v2:** `created_by`, `git_commit_sha`, `branch_name`, `source_hash`, `collector_version`, `environment`, `tags`, `description` metadata — backward compatible with v1 snapshots
- **Snapshot store:** SHA-256 checksum, gzip export/import, retention-based cleanup, snapshot info
- **Snapshot CLI:** `driftguard snapshots list`, `snapshots show`, `snapshots delete` subcommands
- **Diff engine:** fuzzy field rename detection via SequenceMatcher (threshold 0.5)
- **Diff events:** `DefaultValueChanged`, `ConstraintChanged`, `IndexChanged`, `ForeignKeyChanged`, `PrimaryKeyChanged`
- **Diff engine:** constraint diffing — PK, unique, FK, max_length, min_value, max_value, pattern
- **Diff CLI:** `--only-breaking` and `--resource` filter flags on `driftguard diff`
- **Policy modes:** `strict`, `lenient`, `backward_compatible`, `forward_compatible` evaluation modes
- **Policy rules:** default value, constraint, FK, PK, index, and numeric range change classification
- **Collectors:** MySQL (SQLAlchemy), SQLite (SQLAlchemy), YAML data file inference
- Community files: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, ROADMAP.md
- GitHub issue templates (bug report, feature request), release notes template
- Enterprise config template (`examples/enterprise-config.yaml`)
- README: "Why DriftGuard?", "Not a linter", installation options (pip/uv/poetry), real CLI output, versioning section

### Changed
- CHANGELOG restructured into release-based format
- Package description, keywords, and classifiers expanded for PyPI discoverability
- Config validation errors now include file path context
- Tests increased from 152 to 190 (78% coverage)

## [0.1.0] - 2025-04-25

First public release. Full MVP: semantic diff engine, policy engine, CLI, and multi-source collectors.

### Added
- **Core:** Pydantic v2 schema models, semantic diff engine, policy engine with risk classification
- **CLI:** Typer-based commands (`init`, `snapshot`, `diff`, `check`, `report`) with CI gate
- **Collectors:** PostgreSQL (SQLAlchemy), OpenAPI 3.x / Swagger 2.x, JSON Schema, CSV
- **Reporters:** Terminal (Rich), JSON, Markdown, HTML
- **Store:** Versioned local JSON snapshot storage
- **Config:** YAML-based source definitions and policy overrides
- **CI:** GitHub Actions matrix across Python 3.11 / 3.12 / 3.13
- **Docs:** Architecture, CLI usage, policy rules, adapter development guides
- **Examples:** OpenAPI demo, CSV file schema demo
- **Tests:** 152 tests (unit, golden, CLI, reporter)
