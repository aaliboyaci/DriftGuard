# Releasing DriftGuard

## Version Bump Process

1. Update version in two places:
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `src/driftguard/__init__.py` → `__version__ = "X.Y.Z"`

2. Update `CHANGELOG.md`:
   - Change `[Unreleased]` header to `[X.Y.Z] - YYYY-MM-DD`
   - Summarize changes under Added/Changed/Fixed sections

3. Update `README.md`:
   - Test count badge if tests changed
   - Coverage badge if coverage changed

## Release Checklist

```
[ ] Version bumped in pyproject.toml and __init__.py
[ ] CHANGELOG.md updated with release date
[ ] All tests pass: pytest tests/
[ ] Lint clean: ruff check src/ tests/
[ ] Type check clean: mypy src/
[ ] Build succeeds: python -m build
[ ] Package valid: twine check dist/*
[ ] Commit and push
[ ] Create git tag: git tag vX.Y.Z
[ ] Push tag: git push origin vX.Y.Z
[ ] Create GitHub release (triggers PyPI publish workflow)
[ ] Verify package on PyPI
[ ] Verify install: pip install driftguard==X.Y.Z && driftguard demo
```

## Semantic Versioning

- **Patch** (0.0.X): Bug fixes, documentation, test improvements
- **Minor** (0.X.0): New features, new collectors, CLI enhancements
- **Major** (X.0.0): Breaking API changes, config format changes

## GitHub Trusted Publishing

The `publish.yml` workflow uses PyPI trusted publishing (OIDC).
No API tokens needed — configure at:
- PyPI: https://pypi.org/manage/project/driftguard/settings/publishing/
- TestPyPI: https://test.pypi.org/manage/project/driftguard/settings/publishing/

Add the GitHub repository as a trusted publisher with:
- Owner: `aaliboyaci`
- Repository: `DriftGuard`
- Workflow: `publish.yml`
- Environment: `pypi` (or `testpypi`)
