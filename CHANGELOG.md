# Changelog

All notable changes to DriftGuard will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- "Why DriftGuard?" and "Not a linter" sections in README
- Real CLI output from OpenAPI demo in README
- v0.1.0 scope completed milestone in roadmap

### Changed
- CHANGELOG format tightened to release-based structure

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
