# Supported Sources

## Stable

| Source | Collector | Config Type | Notes |
|--------|-----------|-------------|-------|
| PostgreSQL | `PostgresCollector` | `postgres` | SQLAlchemy introspection, PK/FK/unique constraints |
| MySQL | `MysqlCollector` | `mysql` | SQLAlchemy introspection (requires mysqlclient or pymysql) |
| SQLite | `SqliteCollector` | `sqlite` | SQLAlchemy introspection, fully tested offline |
| OpenAPI 3.x | `OpenApiCollector` | `openapi` | Component schema extraction from YAML/JSON specs |
| Swagger 2.0 | `OpenApiCollector` | `openapi` | Backward compatible with 2.0 definitions |
| JSON Schema | `JsonSchemaCollector` | `json_schema` | Type, nullable, enum, default, required extraction |
| JSON Payload | `JsonSchemaCollector` | `json_payload` | Schema inferred from sample JSON data |
| CSV | `CsvCollector` | `csv` | Header + sample-based type inference, delimiter auto-detection |

## Beta

| Source | Collector | Config Type | Notes |
|--------|-----------|-------------|-------|
| YAML | `YamlCollector` | `yaml` | Data file structure inference from YAML documents |
| Sequelize | `SequelizeCollector` | `sequelize` | Static JS/TS model parsing, type mapping, constraints, associations |
| Prisma | `PrismaCollector` | `prisma` | schema.prisma parser with model/field/relation/enum extraction |

## Experimental

| Source | Collector | Config Type | Notes |
|--------|-----------|-------------|-------|
| Cross-service registry | `ContractRegistry` | — | Publish/pull/list with semantic versioning, impact analysis |

## Planned

| Source | Status | Notes |
|--------|--------|-------|
| Parquet | Planned | Arrow-based schema extraction (enum defined, collector not yet implemented) |
| MongoDB | Planned | Sample-based schema inference |
| Kafka / Avro / Protobuf | Planned | Schema Registry integration |
| BigQuery / Snowflake / Redshift | Planned | Cloud data warehouse support |
| Excel | Planned | Spreadsheet schema inference |

## Stability Matrix

| Module | Status | Notes |
|--------|--------|-------|
| OpenAPI deep diff | **Stable** | Path/method/parameter/body/status diff, 69 tests |
| PostgreSQL schema diff | **Stable** | SQLAlchemy introspection, PK/FK/unique constraints |
| MySQL schema diff | **Stable** | SQLAlchemy introspection (requires mysqlclient or pymysql) |
| SQLite schema diff | **Stable** | Full offline testing, 5 tests |
| CSV collector | **Stable** | Header + sample-based type inference, delimiter auto-detection |
| JSON Schema / JSON Payload | **Stable** | Type/nullable/enum/default/required extraction |
| JSONB nested diff | **Stable** | Confidence-aware severity, PII-safe shape inference, 67 tests |
| Diff engine | **Stable** | Semantic comparison, rename detection, constraint diffing |
| Policy engine | **Stable** | Risk classification, 4 policy modes, suppression integration |
| Reporters (terminal/JSON/MD/HTML/PR) | **Stable** | All formats tested, PR comment truncation |
| Snapshot store (local) | **Stable** | Versioned JSON, checksum, export/import, retention |
| YAML collector | **Beta** | Data file structure inference |
| Sequelize collector | **Beta** | Regex-based JS/TS model parsing, 37 tests |
| Prisma collector | **Beta** | schema.prisma parser, 8 tests |
| Suppression / Waiver | **Beta** | .driftguardignore + YAML waiver CRUD, expiry, 40 tests |
| S3 snapshot backend | **Beta** | Lazy boto3, custom endpoint (MinIO), 31 backend tests |
| Cross-service registry | **Experimental** | Publish/pull/list, impact analysis, filesystem-backed |

## Config Example

```yaml
sources:
  - name: api
    type: openapi
    path: specs/openapi.yaml

  - name: users-db
    type: postgres
    connection: postgresql://user:pass@localhost:5432/mydb
    options:
      schema: public

  - name: export
    type: csv
    path: data/export.csv

  - name: config-data
    type: yaml
    path: config/data.yaml
```
