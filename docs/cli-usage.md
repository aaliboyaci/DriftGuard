# CLI Usage

## Installation

```bash
pip install driftguard-contracts
```

## Commands

### `driftguard init`

Create a `driftguard.yaml` configuration file.

```bash
driftguard init                    # Creates driftguard.yaml
driftguard init -c custom.yaml     # Custom path
driftguard init --force            # Overwrite existing
```

### `driftguard snapshot`

Take a snapshot of current schemas from configured sources.

```bash
driftguard snapshot --name baseline
driftguard snapshot --name v1.2.0
driftguard snapshot -n current -c custom.yaml
```

### `driftguard diff`

Compare two snapshots and show semantic differences.

```bash
driftguard diff --baseline baseline --current current
driftguard diff -b v1.0 -c v1.1
```

### `driftguard check`

CI gate command. Exits with code 1 if breaking changes are detected.

```bash
# Compare two existing snapshots
driftguard check --baseline baseline --current current

# Take fresh snapshot from sources and compare against baseline
driftguard check --baseline baseline
```

**Exit codes:**
- `0` - No breaking changes
- `1` - Breaking changes detected

### `driftguard report`

Generate a drift report in the specified format.

```bash
# Markdown report to file
driftguard report -b baseline -c current --format markdown --output report.md

# JSON report to stdout
driftguard report -b baseline -c current --format json

# HTML report
driftguard report -b baseline -c current --format html --output report.html
```

**Formats:** `terminal`, `json`, `markdown` (or `md`), `html`

### Global Options

```bash
driftguard --version       # Show version
driftguard --help           # Show help
```

## Configuration File

`driftguard.yaml`:

```yaml
version: "1"
snapshot_dir: .driftguard/snapshots

sources:
  - name: main-db
    type: postgres
    connection: postgresql://user:pass@localhost:5432/mydb
    options:
      schema: public

  - name: api-spec
    type: openapi
    path: openapi.yaml

  - name: events
    type: json_schema
    path: schemas/event.json

  - name: export
    type: csv
    path: data/export.csv

policy_overrides:
  - resource: "legacy_*"
    category: field_removed
    severity: warning

report_formats:
  - terminal
  - markdown
```

## CI Usage (GitHub Actions)

```yaml
- name: Install DriftGuard
  run: pip install driftguard-contracts

- name: Check for breaking changes
  run: driftguard check --baseline baseline --current current

- name: Generate report
  if: always()
  run: driftguard report -b baseline -c current -f markdown -o drift-report.md
```
