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
