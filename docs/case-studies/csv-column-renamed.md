# Case Study: CSV Export Column Renamed

## Scenario

A data team renames `user_email` to `email` in a daily CSV export to match the new naming convention. A partner's ETL pipeline reads the column by name.

## Baseline

```csv
user_id,user_email,created_at
1,alice@example.com,2024-01-15
2,bob@example.com,2024-01-16
```

## Current

```csv
user_id,email,created_at
1,alice@example.com,2024-01-15
2,bob@example.com,2024-01-16
```

## DriftGuard Output

```
Severity   | Resource | Change                              | Reason
-----------+----------+-------------------------------------+----------------------------------
[X]        | export   | Field removed: export.user_email    | Consumers expecting this field
BREAKING   |          | (string)                            | will fail
 INFO      | export   | Field added: export.email (string)  | Adding an optional field is
           |          |                                     | backward compatible
```

## Why This Breaks Production

- The partner's ETL reads `row["user_email"]` by name
- After the rename, `KeyError: 'user_email'` crashes the import job
- The partner doesn't know until their daily batch fails at 3 AM
- Hours of data are delayed while the issue is debugged

## How DriftGuard Catches It

```bash
driftguard snapshot --name yesterday   # baseline CSV schema
driftguard snapshot --name today       # after rename
driftguard check -b yesterday -c today
# BREAKING CHANGE: Field removed: export.user_email
```

The rename is flagged as a breaking change (remove + add) before the export goes live.
