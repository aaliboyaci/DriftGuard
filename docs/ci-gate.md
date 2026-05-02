# CI Gate

DriftGuard is designed to run in CI pipelines. The `check` command exits with code 1 when breaking changes are detected.

## GitHub Actions

```yaml
name: Schema Drift Check
on: [pull_request]

jobs:
  drift-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install DriftGuard
        run: pip install driftguard-contracts

      - name: Check for breaking changes
        run: driftguard check --baseline baseline --current current

      - name: Generate report
        if: always()
        run: driftguard report -b baseline -c current -f markdown -o drift-report.md

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: drift-report
          path: drift-report.md
```

## GitLab CI

```yaml
drift-check:
  image: python:3.13
  script:
    - pip install driftguard-contracts
    - driftguard check --baseline baseline --current current
  artifacts:
    paths:
      - drift-report.md
    when: always
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No breaking changes |
| 1 | Breaking changes detected |

## Pre-merge vs Nightly

- **Pre-merge:** Run on every PR to block breaking changes before merge
- **Nightly:** Run scheduled scans to detect drift from external sources (DB migrations, partner API changes)

## Report Formats

Use `--format` to choose the output:

| Format | Use Case |
|--------|----------|
| `terminal` | Interactive review |
| `markdown` | PR comments, CI artifacts |
| `html` | Standalone reports |
| `json` | Machine processing, dashboards |
