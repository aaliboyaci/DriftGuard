# File Schema Demo

Demonstrates DriftGuard detecting changes in CSV file schemas.

## Changes between baseline and current

| Change | Type |
|--------|------|
| `name` column removed | Breaking |
| `full_name` column added | Info (optional) |
| `active` column removed | Breaking |
| `status` column added | Info (optional) |
| `amount` type changed (integer -> number) | Warning |
| `email` became nullable (row 3 empty) | Warning |

## Usage

```bash
# From project root
cd examples/file-schema-demo
python setup_demo.py
driftguard diff --baseline baseline --current current --config driftguard.yaml
```
