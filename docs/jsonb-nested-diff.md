# JSONB / Nested Contract Diff

## Overview

DriftGuard's nested contract diff feature detects schema drift inside unstructured or semi-structured data: JSONB columns in PostgreSQL, JSON event payloads, configuration documents, and API response bodies. Rather than treating these as opaque blobs, DriftGuard infers their internal shape from sample data and tracks field-level changes over time.

Traditional schema monitoring stops at the column level -- it sees a `payload JSONB` column but has no visibility into what lives inside. The nested diff engine closes that gap by inferring, snapshotting, and diffing the internal structure of these payloads.

## When to Use

- **JSONB/JSON columns** -- PostgreSQL, MySQL JSON columns storing event data, user preferences, or form submissions
- **Event payloads** -- Kafka, RabbitMQ, or webhook payloads with evolving structures
- **Configuration documents** -- Application config stored as JSON in databases or files
- **API response bodies** -- REST or GraphQL responses where the schema is not formally specified
- **Log structured data** -- JSON-formatted log entries where field additions/removals indicate instrumentation changes

## CLI Commands

### `driftguard nested infer`

Infers the nested schema shape from one or more JSON/NDJSON sample files.

```bash
driftguard nested infer samples.json --name orders_payload --output baseline.json
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `files` | One or more JSON or NDJSON sample files (positional) |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--name`, `-n` | `payload` | Resource name for the inferred schema |
| `--output`, `-o` | stdout | Output file path |
| `--max-depth` | `10` | Maximum nesting depth to traverse |
| `--sample-limit` | `10000` | Maximum number of samples to process |

**Input formats:**

- Single JSON file containing one object
- Single JSON file containing an array of objects
- NDJSON file (one JSON object per line)
- Multiple file paths combined into one sample set

**Example:**

```bash
# Infer from an array of event payloads
driftguard nested infer events_2024_q1.json --name webhook_events --output baseline.json

# Infer from multiple NDJSON log files
driftguard nested infer logs_jan.ndjson logs_feb.ndjson --name app_logs --output baseline.json

# Limit depth for deeply nested documents
driftguard nested infer config_samples.json --name app_config --max-depth 5 --output baseline.json
```

### `driftguard nested diff`

Compares two nested contract schemas and produces semantic diff events.

```bash
driftguard nested diff baseline.json current.json
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `baseline` | Path to baseline nested schema JSON |
| `current` | Path to current nested schema JSON |

**Options:**

| Option | Default | Description |
|--------|---------|-------------|
| `--format`, `-f` | `terminal` | Output format: `terminal`, `json`, `markdown`, `html`, `pr` |
| `--output`, `-o` | stdout | Output file path |
| `--only-breaking` | `false` | Show only breaking changes |

**Example:**

```bash
# Terminal output with color
driftguard nested diff baseline.json current.json

# Generate a markdown report for CI
driftguard nested diff baseline.json current.json --format markdown --output report.md

# Only show breaking changes
driftguard nested diff baseline.json current.json --only-breaking

# Generate JSON for machine processing
driftguard nested diff baseline.json current.json --format json --output drift.json
```

## Path Notation

DriftGuard uses a dot-path notation to identify fields within nested structures. This notation supports objects, arrays, and map-style keys.

### Object fields

Dot-separated for nested object keys:

```
user.email          → { "user": { "email": "..." } }
order.billing.zip   → { "order": { "billing": { "zip": "..." } } }
```

### Array items

Bracket notation `[]` for array element fields:

```
items[].sku         → { "items": [ { "sku": "..." }, ... ] }
items[].tags[]      → { "items": [ { "tags": ["...", ...] }, ... ] }
```

### Map/wildcard keys

Asterisk `*` for dynamic map keys:

```
metadata.*          → { "metadata": { "<any_key>": "..." } }
headers.*           → { "headers": { "Content-Type": "...", ... } }
```

### Depth examples

| Path | Depth | Description |
|------|-------|-------------|
| `id` | 1 | Root-level field |
| `user.name` | 2 | One level of nesting |
| `order.items[].sku` | 3 | Object > array > field |
| `payload.data.nested.deep` | 4 | Multiple object levels |

## Confidence Scoring

Every field in a nested contract carries a **confidence score** between 0.0 and 1.0, calculated as:

```
confidence = occurrence_count / sample_count
```

- **1.0** -- Field was present in every sample (treated as required)
- **0.8** -- Field was present in 80% of samples
- **0.0** -- Field was never observed (should not appear)

### How confidence affects policy decisions

The policy engine uses confidence to modulate severity:

| Confidence | Field Removed | Required Field Added |
|------------|---------------|---------------------|
| >= 0.8 | Breaking | Breaking |
| < 0.8 | Warning | Warning |

A field that only appeared in 30% of samples and then disappears is less likely to indicate a true breaking change -- it may be an optional or intermittent field.

### Improving confidence

- Increase sample size with `--sample-limit`
- Provide more sample files (multiple NDJSON files)
- Ensure samples cover different code paths and edge cases

## Enum Candidate Detection

When a string field has low cardinality (few distinct values), the inference engine automatically marks it as an enum candidate. This enables drift detection when allowed values change.

### Detection criteria

1. The field must be of type `string`
2. The number of distinct values must be <= `max_enum_values` (default: 20)
3. Values must repeat sufficiently (controlled by `enum_min_repetition_ratio`)
4. At least 2 samples must contain string values for the field

### Example

Given 100 samples where `order.status` contains only `["pending", "shipped", "delivered", "cancelled"]`:

```json
{
  "path": "order.status",
  "field_type": "string",
  "enum_candidates": ["cancelled", "delivered", "pending", "shipped"],
  "confidence": 1.0
}
```

If a new version introduces `"refunded"`, the diff engine emits a `NestedEnumValuesChanged` event.

## Format Hints

The inference engine detects common string formats by pattern-matching sampled values. Format hints provide additional context for understanding field semantics without storing raw values.

| Format | Pattern | Example |
|--------|---------|---------|
| `uuid` | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | `550e8400-e29b-41d4-a716-446655440000` |
| `email` | `user@domain.tld` | `jane@example.com` |
| `datetime` | `YYYY-MM-DDThh:mm...` | `2024-03-15T10:30:00Z` |
| `date` | `YYYY-MM-DD` | `2024-03-15` |

Format hints are informational -- they appear in the schema output but do not currently trigger diff events when a format changes.

## Example Workflow

A complete workflow for tracking drift in a JSONB column:

### Step 1: Collect baseline samples

Export sample JSON data from your source (database query, API recording, log extraction):

```bash
# Example: export JSONB samples from PostgreSQL
psql -c "SELECT payload FROM orders LIMIT 500" --csv | \
  python -c "import csv,json,sys; [print(json.dumps(json.loads(r[0]))) for r in csv.reader(sys.stdin) if r]" \
  > baseline_samples.ndjson
```

### Step 2: Infer baseline schema

```bash
driftguard nested infer baseline_samples.ndjson \
  --name orders_payload \
  --output baseline.json
```

### Step 3: After payload changes, collect current samples

```bash
# Same query, new data (after a code deploy or migration)
psql -c "SELECT payload FROM orders WHERE created_at > '2024-03-01' LIMIT 500" --csv | \
  python -c "import csv,json,sys; [print(json.dumps(json.loads(r[0]))) for r in csv.reader(sys.stdin) if r]" \
  > current_samples.ndjson
```

### Step 4: Infer current schema

```bash
driftguard nested infer current_samples.ndjson \
  --name orders_payload \
  --output current.json
```

### Step 5: Diff and assess risk

```bash
driftguard nested diff baseline.json current.json
```

Example output:

```
BREAKING  Nested field removed: orders_payload.shipping.tracking_number (string)
WARNING   Nested enum values changed: orders_payload.status (+refunded)
INFO      Optional nested field added: orders_payload.discount_code (string)

Summary: 3 changes | 1 breaking | 1 warning | 1 info
BREAKING CHANGES DETECTED: 1 breaking change(s)
```

### Step 6: Update baseline after approved changes

Once the breaking change is reviewed and approved:

```bash
cp current.json baseline.json
```

## Risk Classification for Nested Events

| Change | Default Severity | Condition |
|--------|-----------------|-----------|
| Nested field removed | Breaking | confidence >= 0.8 |
| Nested field removed | Warning | confidence < 0.8 |
| Required nested field added | Breaking | confidence >= 0.8 |
| Required nested field added | Warning | confidence < 0.8 |
| Optional nested field added | Info | -- |
| Nested field type changed (narrowing) | Breaking | e.g., string -> integer |
| Nested field type changed (widening) | Warning | e.g., integer -> number |
| Nested field required: optional -> required | Breaking | -- |
| Nested field required: required -> optional | Info | -- |
| Nested field nullable changed | Warning | -- |
| Nested enum values removed | Breaking | -- |
| Nested enum values added | Warning | -- |

### Widening transitions (Warning instead of Breaking)

These type changes are treated as warnings because they expand the value space:

```
integer → number
integer → string
number  → string
boolean → string
```

Any other type change (e.g., `string → integer`, `object → array`) is treated as breaking.

## Configuration Options

### InferenceConfig parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_depth` | `10` | Maximum nesting depth to traverse. Paths deeper than this are ignored. |
| `max_samples` | `10000` | Maximum number of JSON samples to process. Additional samples are discarded. |
| `max_enum_values` | `20` | Maximum distinct values before a field stops being treated as an enum candidate. |
| `enum_min_repetition_ratio` | `0.2` | Minimum average frequency for enum detection. Lower values are more permissive. |

### CLI-level configuration

Pass these as CLI options to `driftguard nested infer`:

```bash
# Deep documents: increase depth
driftguard nested infer samples.json --max-depth 15 --output schema.json

# Large dataset: process more samples for better confidence
driftguard nested infer events.ndjson --sample-limit 50000 --output schema.json
```

### File size limits

The JSON sample collector enforces a maximum file size of 50 MB per file by default. This prevents accidental processing of very large exports.

## Integration with CI

### GitHub Actions example

```yaml
name: Nested Contract Drift Check
on: [pull_request]

jobs:
  nested-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install DriftGuard
        run: pip install driftguard-contracts

      - name: Infer current nested schema
        run: |
          driftguard nested infer tests/fixtures/current_payload.ndjson \
            --name orders_payload \
            --output current.json

      - name: Diff against baseline
        run: |
          driftguard nested diff contracts/baseline.json current.json \
            --format markdown --output nested-report.md

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: nested-drift-report
          path: nested-report.md
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | No breaking changes in nested contracts |
| 1 | Breaking changes detected (CI fails) |

### Storing baselines in version control

Commit the baseline nested schema JSON file to your repository:

```
contracts/
  baseline.json           # Flat schema baseline
  nested/
    orders_payload.json   # Nested baseline for orders.payload
    events_payload.json   # Nested baseline for event payloads
```

Update baselines through a deliberate process (PR review) rather than automatically overwriting them.
