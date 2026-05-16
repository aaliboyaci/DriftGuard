# GitHub Actions Integration

## PR Comment Workflow

DriftGuard can post schema drift reports as PR comments. See `.github/workflows/driftguard-pr.yml` for a working example.

### Setup

1. Install DriftGuard in your CI:
   ```yaml
   - run: pip install driftguard-contracts
   ```

2. Get baseline (from main branch or artifact):
   ```yaml
   - run: git show origin/main:openapi.yaml > /tmp/baseline.yaml
   ```

3. Run diff:
   ```yaml
   - run: driftguard openapi diff /tmp/baseline.yaml openapi.yaml --format markdown --output report.md
   ```

4. Post comment:
   ```yaml
   - uses: marocchino/sticky-pull-request-comment@v2
     with:
       path: report.md
   ```

### Permissions

PR comment requires `pull-requests: write` permission:

```yaml
permissions:
  contents: read
  pull-requests: write
```

### GitHub Actions Step Summary

Write report to `$GITHUB_STEP_SUMMARY` for the Actions UI:

```yaml
- run: cat report.md >> "$GITHUB_STEP_SUMMARY"
```

### Baseline Strategies

| Strategy | When to use |
|----------|-------------|
| `git show origin/main:spec.yaml` | Spec checked into repo |
| Download artifact from previous run | Snapshot stored as CI artifact |
| Download from S3/GCS | Snapshot stored externally |

#### Artifact Download Example

```yaml
- uses: actions/download-artifact@v4
  with:
    name: baseline-snapshot
    path: /tmp/baseline/
    github-token: ${{ secrets.GITHUB_TOKEN }}
    run-id: ${{ github.event.pull_request.base.sha }}
```

#### Artifact Upload Example

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: current-snapshot
    path: drift-report.md
    retention-days: 30
```

### Input Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `baseline` | Path to baseline spec | required |
| `current` | Path to current spec | required |
| `--format` | Output format: terminal, json, markdown, html | terminal |
| `--output` | Save to file | stdout |
| `--only-breaking` | Show only breaking changes | false |

### Report Formats

| Format | Use Case |
|--------|----------|
| `markdown` | PR comments, step summary |
| `json` | Custom processing, dashboards |
| `html` | Standalone artifact |
| `terminal` | Local debugging |

### Annotations

DriftGuard JSON output can be converted to GitHub annotations using `jq`:

```yaml
- name: Annotate breaking changes
  run: |
    driftguard openapi diff baseline.yaml current.yaml --format json | \
      jq -r '.changes[] | select(.severity == "breaking") | "::error ::\(.description)"'
```

### SARIF Integration

For GitHub Code Scanning, convert DriftGuard output to SARIF:

```yaml
- name: Generate SARIF
  run: |
    driftguard openapi diff baseline.yaml current.yaml --format json | \
      python scripts/to_sarif.py > results.sarif

- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: results.sarif
```
