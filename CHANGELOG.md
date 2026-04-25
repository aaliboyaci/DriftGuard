# Changelog

All notable changes to DriftGuard will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Config v2:** `project_name`, `environment`, `owner_team`, `notification` settings, `schema_version` for migration
- **Config CLI:** `driftguard config validate` and `driftguard config print` subcommands
- **Config migration:** automatic v0 -> v1 config schema migration on load
- **Snapshot v2:** `created_by`, `git_commit_sha`, `branch_name`, `source_hash`, `collector_version`, `environment`, `tags`, `description` metadata fields
- **Diff engine:** fuzzy field rename detection (SequenceMatcher, threshold 0.5)
- **Diff events:** `DefaultValueChanged`, `ConstraintChanged`, `IndexChanged`, `ForeignKeyChanged`, `PrimaryKeyChanged`
- **Diff engine:** constraint diffing (PK, unique, FK, max_length, pattern changes)
- **Policy modes:** `strict`, `lenient`, `backward_compatible`, `forward_compatible` evaluation modes
- **Policy rules:** default value, constraint, FK, PK, and index change classification
- Enterprise config template with all available options
- Community files: CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md, ROADMAP.md
- GitHub issue templates, release notes template, v0.1.1 milestone
- README: "Why DriftGuard?", installation options, real CLI output, versioning section

### Changed
- CHANGELOG format tightened to release-based structure
- Package description and keywords improved for PyPI discoverability
- Config validation errors now include file path context
- Tests increased from 152 to 179

## [0.1.0] - 2025-04-25

First public release. Full MVP with semantic diff engine, policy engine, CLI, and multi-source collectors.

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
