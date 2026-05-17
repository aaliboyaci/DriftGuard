# Security Review Checklist

## Snapshot Safety
- [x] No raw PII values stored in nested schemas (only shape)
- [x] `examples_redacted` flag defaults to True
- [x] DB connection strings not stored in snapshots
- [x] Secret masking in reporter output

## Network
- [x] S3 backend supports custom endpoint_url (MinIO, private)
- [x] PostgreSQL collector uses SQLAlchemy (supports SSL)
- [x] No outbound network calls in diff/policy engine

## Access Control
- [x] Read-only DB user documented for JSONB sampling
- [x] Suppression requires `owner` field
- [x] Waiver requires `reason` + `owner`
- [x] Expired suppressions emit warnings

## Dependencies
- [x] Minimal required deps (typer, rich, pydantic, pyyaml, sqlalchemy)
- [x] Optional heavy deps behind extras ([s3], [dev])
- [x] No eval/exec in any collector or parser
- [x] Regex-based ORM parsing (no code execution)

## CI/CD
- [x] GitHub Actions workflow uses OIDC (no API tokens)
- [x] PR comment workflow requires explicit permissions
- [x] No secrets in example configs

## Known Risks
- External $ref not resolved (avoids remote code inclusion)
- Large JSONB sampling bounded by sample_limit
- Regex ORM parsers may miss edge cases (not a security risk, accuracy risk)
