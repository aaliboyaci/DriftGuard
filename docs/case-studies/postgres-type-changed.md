# Case Study: PostgreSQL Column Type Changed

## Scenario

A data engineer changes the `users.id` column from `integer` to `uuid` to support multi-region sharding. The analytics pipeline casts `id` to integer for aggregation.

## Baseline

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP
);
```

## Current

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    created_at TIMESTAMP
);
```

## DriftGuard Output

```
Severity   | Resource | Change                              | Reason
-----------+----------+-------------------------------------+----------------------------------
[X]        | users    | Type changed: users.id              | Type changed from integer to
BREAKING   |          | (integer -> uuid)                   | uuid; parse and validation
           |          |                                     | behavior changes
```

## Why This Breaks Production

- The analytics pipeline runs `SELECT CAST(id AS INTEGER)` for grouping
- After migration, this query fails: `ERROR: cannot cast type uuid to integer`
- ETL jobs fail silently or produce empty reports
- Downstream dashboards show stale or missing data

## How DriftGuard Catches It

```bash
# In CI, before applying the migration:
driftguard snapshot --name pre-migration
# After migration on staging:
driftguard snapshot --name post-migration
driftguard check -b pre-migration -c post-migration
# Exit code 1 — pipeline blocked
```
