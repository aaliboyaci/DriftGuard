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
