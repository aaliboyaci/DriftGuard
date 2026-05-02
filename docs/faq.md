# FAQ

## Is DriftGuard a migration tool?

No. DriftGuard does not generate `ALTER TABLE` statements or manage database state. It **detects** schema changes by comparing snapshots — it doesn't **apply** them.

Use DriftGuard alongside your migration tool (Alembic, Flyway, Liquibase) to verify that migrations don't introduce breaking contract changes.

## Can it block CI?

Yes. The `driftguard check` command exits with code 1 when breaking changes are detected. Add it to your CI pipeline to block merges:

```yaml
- name: Check for drift
  run: driftguard check --baseline baseline --current current
```

See [CI Gate](ci-gate.md) for full examples.

## Does it need a database connection?

Only if you're monitoring database schemas. For OpenAPI specs, JSON Schema, CSV, YAML, and other file-based sources, DriftGuard works entirely offline.

## How is it different from a linter?

A linter checks a **single schema** for style and best practices. DriftGuard compares **two versions** of a schema and classifies the changes by risk. A linter might say "this field name should be camelCase." DriftGuard says "this field was removed — that's a breaking change."

## What does "breaking" mean?

A change is classified as **breaking** if it could cause downstream consumers to fail. Examples:
- Field removed (consumers expect it)
- Required field added (existing producers don't send it)
- Type narrowed (string → integer: parse fails)
- Primary key changed (joins break)

See [Policy Rules](policy-rules.md) for the full classification table.

## Can I override the risk classification?

Yes. Use `policy_overrides` in `driftguard.yaml`:

```yaml
policy_overrides:
  - resource: users
    field: legacy_field
    severity: info    # demote from breaking to info
```

Or use policy modes: `strict`, `lenient`, `backward_compatible`, `forward_compatible`.

## What sources are supported?

PostgreSQL, MySQL, SQLite, OpenAPI, JSON Schema, CSV, YAML, and more. See [Supported Sources](supported-sources.md).

## Does it support runtime monitoring?

No. DriftGuard runs at build time, in CI, or on demand. It's not a runtime agent or sidecar. It compares point-in-time snapshots.
