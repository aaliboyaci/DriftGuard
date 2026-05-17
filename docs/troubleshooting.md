# Troubleshooting

## Common Issues

### `driftguard: command not found`

Package not in PATH. Fix:
```bash
pip install driftguard-contracts
# or ensure ~/.local/bin is in PATH
```

### `Config not found: driftguard.yaml`

Run `driftguard init` first, or pass `--config path/to/config.yaml`.

### `Snapshot not found: baseline`

Take a snapshot first:
```bash
driftguard snapshot --name baseline
```

### OpenAPI spec parse error

Ensure file is valid YAML/JSON. Test with:
```bash
python -c "import yaml; yaml.safe_load(open('spec.yaml'))"
```

### `$ref` not resolved

DriftGuard resolves local `$ref` (e.g., `#/components/schemas/Pet`). External file references (`./other.yaml`) are not supported yet.

### Empty diff output

- Verify baseline and current are different files/snapshots
- Check resource names match between baseline and current
- For OpenAPI: ensure paths exist (not just component schemas)

### CI workflow fails with permission error

PR comment requires `pull-requests: write`:
```yaml
permissions:
  contents: read
  pull-requests: write
```

## Nested / JSONB

### Too many enum candidates

If the inference engine detects too many distinct values for a field, it stops treating it as an enum. If you know a field is legitimately an enum with many values:

```bash
# Increase the enum threshold (default is 20)
# Use InferenceConfig with a higher max_enum_values
driftguard nested infer samples.json --name payload --output schema.json
```

Currently `max_enum_values` is configured at the code level via `InferenceConfig(max_enum_values=50)`. If you are seeing enum candidates you do not expect, the field may have more distinct values than anticipated. Consider whether the field is truly an enum or a free-form string.

### Low confidence warning for a field I know exists

Low confidence means the field was not present in all samples. This is usually a sampling problem:

```bash
# Increase the sample limit to get more representative data
driftguard nested infer samples.json --name payload --sample-limit 50000 --output schema.json
```

Other causes:
- The field was introduced recently and older samples do not contain it
- The field is conditionally present (e.g., only on certain event types)
- Your sample file contains a mix of different payload schemas

Solution: provide more samples, filter samples to a single schema type, or accept that the field is genuinely optional.

### Nested schema too deep

If deeply nested structures are being truncated or not appearing in the output:

```bash
# Increase max depth (default is 10)
driftguard nested infer samples.json --name payload --max-depth 15 --output schema.json
```

Note: Very deep nesting (> 15 levels) may indicate a data modeling issue. Consider whether the payload structure can be simplified.

### JSONB column returns empty schema

If `driftguard nested infer` produces a schema with zero fields:

1. **Check for NULL values** -- If most rows have `NULL` in the JSONB column, the exported samples will be empty. Add a `WHERE column IS NOT NULL` filter to your extraction query.

2. **Check the WHERE clause** -- Ensure your date range or filter conditions match rows that actually contain data.

3. **Verify file format** -- The file must contain valid JSON objects or NDJSON. Check with:
   ```bash
   head -1 samples.ndjson | python -m json.tool
   ```

4. **Check for empty objects** -- If the column contains `{}` (empty objects), there are no fields to infer. Ensure you are sampling rows with populated payloads.

5. **File encoding** -- The collector expects UTF-8 encoding. Non-UTF-8 files may fail silently or produce empty results.

## Known Limitations

- **External $ref**: Only local `#/...` references resolved. No external file refs.
- **allOf/oneOf/anyOf**: Not fully expanded in schema extraction.
- **Circular references**: May cause infinite loop. Avoid circular $ref in specs.
- **Large specs**: Specs with 1000+ paths may be slow on first parse.
- **Database collectors**: PostgreSQL, MySQL require live connection. No offline mode.
- **Parquet**: Requires pyarrow. Not included in minimal install.

## Debug Mode

```bash
driftguard openapi diff baseline.yaml current.yaml --format json 2>&1 | python -m json.tool
```

## Getting Help

- [GitHub Issues](https://github.com/aaliboyaci/DriftGuard/issues)
- [FAQ](faq.md)
