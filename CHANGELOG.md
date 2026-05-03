# Changelog

All notable changes to DriftGuard will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — v0.3.0

### Added
- **OpenAPI deep diff models:** `OpenApiContract`, `OpenApiPath`, `OpenApiOperation`, `OpenApiParameter`, `OpenApiRequestBody`, `OpenApiResponse`
- **OpenAPI deep extractor:** path-level, method-level, query/path/header parameter, request body, response body, status code extraction
- $ref resolution for request/response schemas
- Path-level parameter inheritance with operation-level override
- Swagger 2.x backward compatibility (body params, response schema)
- 46 OpenAPI extractor tests
- Rich test fixture: `tests/fixtures/petstore_full.yaml`
- **OpenAPI diff events:** PathRemoved, PathAdded, MethodRemoved, MethodAdded, ResponseStatusRemoved, ResponseStatusAdded, ParameterRemoved, ParameterAdded, ParameterChanged, EndpointDeprecated
- **OpenAPI diff engine:** path diff, method diff, parameter diff, request body field diff, response body field diff, status code diff, deprecated detection — reuses existing field diff for body comparison
- **OpenAPI policy rules:** path/method/status removed = breaking, required param added = breaking, param became required = breaking, deprecated = warning, param removed = warning, path/method/status added = info
- **Request/response field semantics:** required request field added = breaking, response field removed = breaking, optional response field added = info
- 23 OpenAPI golden tests with baseline + breaking-current fixture pair
- Tests: 280 → 303

## [0.2.5] - 2026-05-03

### Changed
- **Package renamed:** `driftguard` → `driftguard-contracts` (PyPI name `driftguard` was taken by unrelated project)
- All docs, CI examples, and install commands updated to `pip install driftguard-contracts`
- CLI command remains `driftguard` (unchanged)

## [0.2.4] - 2026-05-03

### Added
- Case studies: OpenAPI field removed, PostgreSQL type changed, CSV column renamed
- `docs/quickstart.md` — 5-minute getting started guide
- `docs/ci-gate.md` — CI/CD integration for GitHub Actions and GitLab CI
- `docs/supported-sources.md` — stable/beta/planned source table
- `docs/faq.md` — common questions: migration tool, CI blocking, runtime, overrides
- Policy modes table in `docs/policy-rules.md`
- Case study links in README Documentation section

## [0.2.3] - 2026-05-03

### Added
- YAML collector tests (16 tests, 0% → 100% coverage)
- Policy engine edge case tests: DEFAULT_VALUE_CHANGED, CONSTRAINT_CHANGED, FK, PK, INDEX events
- Policy mode edge case tests: strict info→warning, backward-compat warning→breaking, forward-compat field added
- CLI edge case tests: missing config, missing snapshot, empty snapshot list, config validate
- CLI report terminal format test

### Changed
- Coverage: 79% → 85% (target achieved)
- Tests: 201 → 234

## [0.2.2] - 2026-05-03

### Added
- PyPI publish workflow with GitHub trusted publishing (OIDC)
- `docs/releasing.md` with version bump process and release checklist
- PyPI version badge in README

### Changed
- Package builds verified: wheel, sdist, twine check all pass

## [0.2.1] - 2026-05-03

### Added
- `driftguard demo --format` option: terminal (default), json, markdown, html
- `driftguard demo --output` option: save report to file
- Demo summary line: breaking/warning/info counts in all formats
- Clear CI verdict message at end of demo output
- `make demo-html` Makefile target for HTML report generation
- `examples/demo/` directory with baseline/current JSON, Markdown, and HTML sample reports
- Demo CLI tests (6 tests) and demo golden tests (5 tests)
- README Example Output updated with actual `driftguard demo` output

### Changed
- Tests increased from 190 to 201

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
