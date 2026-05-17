# Migration Guide

## v0.x → v1.0.0

### Package Name
The PyPI package is `driftguard-contracts`. The CLI command is `driftguard`.

```bash
pip install driftguard-contracts
```

### Snapshot Format
v1.0.0 reads snapshots from all previous versions. No migration needed.

### Config Format
Config `schema_version: "2"` is current. v1 configs are auto-migrated.

### Breaking Changes from v0.x
None. v1.0.0 stabilizes the existing API without breaking changes.

## Upgrading Between Minor Versions

### v0.3.x → v0.4.x
- New commands: `driftguard nested infer`, `driftguard nested diff`
- New models: `NestedContract`, `NestedResource`, `NestedField`
- No breaking changes to existing commands

### v0.4.x → v0.6.0
- New: Sequelize/Prisma collectors, suppression system, waiver system
- New SourceTypes: `sequelize`, `prisma`
- No breaking changes

### v0.6.0 → v0.8.0
- New: `SnapshotBackend` interface, S3Backend, ContractRegistry
- `LocalStore` now implements `SnapshotBackend` (backward compatible)
- New optional dep: `pip install driftguard-contracts[s3]`

### v0.8.0 → v1.0.0
- Public API frozen (see docs/public-api.md)
- No breaking changes
