# JSONB / Nested Contract Security

This document covers security considerations when using DriftGuard's nested contract diff feature with JSONB columns, event payloads, and other semi-structured data sources.

## PII Safety: Shape Only, Never Values

DriftGuard's inference engine is designed to analyze the **shape** of JSON data without retaining raw values. The contract schema stores:

- Field paths (`user.email`, `order.items[].sku`)
- Field types (`string`, `integer`, `boolean`)
- Occurrence statistics (confidence scores)
- Enum candidates (only for low-cardinality fields)
- Format hints (`uuid`, `email`, `date`)

It does **not** store:

- Actual field values from your data
- Sample rows or records
- Connection strings or credentials
- Query results beyond structural metadata

### The `examples_redacted` flag

Every `NestedField` in a contract schema carries an `examples_redacted` flag, which defaults to `true`. This flag indicates that raw example values have been stripped from the output. The inference engine never persists raw values in the contract file regardless of this flag -- it exists as a declarative guarantee for compliance audits.

```json
{
  "path": "user.email",
  "field_type": "string",
  "format_hint": "email",
  "examples_redacted": true,
  "confidence": 1.0
}
```

### Enum candidates and PII

Enum candidate detection only activates for low-cardinality string fields (default: <= 20 distinct values). Fields like email addresses, names, or free-text will never be captured as enum candidates because their cardinality exceeds the threshold.

If you have a low-cardinality field that contains sensitive values (e.g., internal team codes), increase `max_enum_values` to 0 or exclude that field from analysis.

## Read-Only Database User

When sampling JSONB columns directly from a database, always use a dedicated read-only user. This ensures DriftGuard cannot accidentally modify data, even if a bug or misconfiguration occurs.

### PostgreSQL setup

```sql
-- Create a dedicated read-only user for DriftGuard
CREATE USER driftguard_reader WITH PASSWORD 'a-strong-random-password';

-- Grant connection access to the database
GRANT CONNECT ON DATABASE your_database TO driftguard_reader;

-- Grant usage on the schema
GRANT USAGE ON SCHEMA public TO driftguard_reader;

-- Grant SELECT only on specific tables with JSONB columns
GRANT SELECT ON orders TO driftguard_reader;
GRANT SELECT ON events TO driftguard_reader;

-- Or grant SELECT on all tables in the schema (broader)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO driftguard_reader;

-- Ensure future tables also get SELECT granted
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO driftguard_reader;
```

### MySQL setup

```sql
-- Create a read-only user
CREATE USER 'driftguard_reader'@'%' IDENTIFIED BY 'a-strong-random-password';

-- Grant SELECT only
GRANT SELECT ON your_database.orders TO 'driftguard_reader'@'%';
GRANT SELECT ON your_database.events TO 'driftguard_reader'@'%';

FLUSH PRIVILEGES;
```

### Principle of least privilege

- Grant SELECT only on the specific tables containing JSONB columns you need to analyze
- Do not grant CREATE, INSERT, UPDATE, DELETE, or DDL permissions
- Use a separate user from your application's database credentials
- Rotate the password on a schedule consistent with your security policy

## Sampling: Limited Row Access

The JSON sample collector is designed to work with a limited number of rows, not full table scans.

### How sampling works

- The `max_samples` parameter (default: 10,000) caps how many JSON objects are analyzed
- When exporting from a database, use `LIMIT` in your query to restrict the result set
- The collector processes samples sequentially and stops at the configured limit

### Recommended extraction pattern

```sql
-- Sample recent rows only, with a hard LIMIT
SELECT payload
FROM orders
WHERE created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC
LIMIT 500;
```

### Why limiting matters

- Reduces exposure: fewer rows queried means less data in transit
- Reduces risk: even if samples are temporarily held in memory, the window is small
- Sufficient for inference: 200-500 diverse samples typically produce reliable confidence scores
- Performance: avoids slow full-table scans on production databases

### Never query unbounded

Avoid queries without `LIMIT` or `WHERE` constraints:

```sql
-- BAD: Full table scan, all rows
SELECT payload FROM orders;

-- GOOD: Bounded, recent data only
SELECT payload FROM orders
WHERE created_at >= NOW() - INTERVAL '7 days'
LIMIT 500;
```

## Network Security

### Use SSL/TLS connections

Always connect to databases over encrypted connections, especially in cloud environments:

```bash
# PostgreSQL with SSL
postgresql://driftguard_reader:password@host:5432/db?sslmode=require

# MySQL with SSL
mysql://driftguard_reader:password@host:3306/db?ssl-mode=REQUIRED
```

### Connection string best practices

| Practice | Reason |
|----------|--------|
| Use `sslmode=require` or `sslmode=verify-full` | Prevents plaintext transmission |
| Use environment variables for credentials | Avoids hardcoding in config files |
| Use secrets management (Vault, AWS SSM) | Centralized credential rotation |
| Restrict network access (security groups, firewalls) | Limits who can reach the database |

### Example with environment variables

```bash
export DRIFTGUARD_DB_URL="postgresql://driftguard_reader:${DB_PASSWORD}@db-host:5432/mydb?sslmode=verify-full"
```

In `driftguard.yaml`:

```yaml
sources:
  - name: orders_jsonb
    type: postgres
    connection: ${DRIFTGUARD_DB_URL}
```

## Snapshot Storage: No Sensitive Values

The nested contract JSON files produced by `driftguard nested infer` contain only structural metadata. They are safe to:

- Commit to version control (Git)
- Store in CI artifacts
- Share across teams
- Upload to dashboards or monitoring systems

### What a contract file contains

```json
{
  "name": "orders_payload",
  "resources": [
    {
      "name": "orders_payload",
      "source": "orders_samples.ndjson",
      "fields": [
        {
          "path": "order_id",
          "field_type": "string",
          "nullable": false,
          "required": true,
          "occurrence_count": 500,
          "sample_count": 500,
          "confidence": 1.0,
          "enum_candidates": null,
          "format_hint": "uuid",
          "examples_redacted": true
        },
        {
          "path": "status",
          "field_type": "string",
          "nullable": false,
          "required": true,
          "occurrence_count": 500,
          "sample_count": 500,
          "confidence": 1.0,
          "enum_candidates": ["cancelled", "delivered", "pending", "shipped"],
          "format_hint": null,
          "examples_redacted": true
        }
      ],
      "sample_count": 500,
      "max_depth": 3
    }
  ]
}
```

### What is NOT in a contract file

- No raw field values (emails, names, addresses, tokens)
- No database connection strings
- No row identifiers or primary key values
- No timestamps of individual records
- No query results or sample data

## Security Checklist

- [ ] Use a dedicated read-only database user for JSONB sampling
- [ ] Grant SELECT only on required tables
- [ ] Use SSL/TLS for all database connections
- [ ] Store credentials in environment variables or secrets management, not in config files
- [ ] Limit sample queries with `WHERE` and `LIMIT` clauses
- [ ] Verify that `examples_redacted: true` is present in contract output
- [ ] Review enum candidates for any fields that might contain sensitive low-cardinality data
- [ ] Do not commit database credentials or connection strings to version control
- [ ] Restrict CI runner network access to only required database endpoints
- [ ] Rotate the `driftguard_reader` password on a regular schedule
