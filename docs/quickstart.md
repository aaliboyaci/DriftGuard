# Quick Start

## 1. Install

```bash
pip install driftguard-contracts
```

## 2. Try the Demo

```bash
driftguard demo
```

No config needed. Shows a simulated API schema change with breaking changes detected.

## 3. Initialize Config

```bash
driftguard init
```

Creates `driftguard.yaml` with default settings. Edit to add your sources:

```yaml
schema_version: "2"
sources:
  - name: api
    type: openapi
    path: openapi.yaml
  - name: users
    type: postgres
    connection: postgresql://user:pass@localhost:5432/mydb
```

## 4. Take a Baseline Snapshot

```bash
driftguard snapshot --name baseline
```

## 5. Make Changes

Edit your API spec, alter a table, modify a CSV export — whatever you need.

## 6. Compare

```bash
driftguard snapshot --name current
driftguard diff --baseline baseline --current current
```

## 7. CI Gate

```bash
driftguard check --baseline baseline --current current
# Exit code 0 = safe, 1 = breaking changes detected
```

## 8. Generate Reports

```bash
driftguard report -b baseline -c current -f markdown -o report.md
driftguard report -b baseline -c current -f html -o report.html
driftguard report -b baseline -c current -f json -o report.json
```

## Next Steps

- [CLI Usage](cli-usage.md) — Full command reference
- [Policy Rules](policy-rules.md) — Risk classification and overrides
- [CI Gate](ci-gate.md) — CI/CD integration
- [Case Studies](case-studies/) — Real-world examples
