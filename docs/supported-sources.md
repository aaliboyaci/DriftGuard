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
| Parquet | `CsvCollector` | `parquet` | Arrow-based schema extraction |

## Planned

| Source | Status | Notes |
|--------|--------|-------|
| MongoDB | Planned | Sample-based schema inference |
| Kafka / Avro / Protobuf | Planned | Schema Registry integration |
| BigQuery / Snowflake / Redshift | Planned | Cloud data warehouse support |
| Excel | Planned | Spreadsheet schema inference |

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
