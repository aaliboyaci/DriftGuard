"""MySQL schema collector.

Uses SQLAlchemy's inspect to extract table schemas from a MySQL database.
Requires the `mysqlclient` or `pymysql` driver to be installed.
"""

from __future__ import annotations

from sqlalchemy import create_engine, inspect

from driftguard.collectors.base import BaseCollector
from driftguard.schema.models import FieldConstraint, FieldDef, ResourceSchema, SourceType

MYSQL_TYPE_MAP: dict[str, str] = {
    "INT": "integer",
    "INTEGER": "integer",
    "TINYINT": "integer",
    "SMALLINT": "integer",
    "MEDIUMINT": "integer",
    "BIGINT": "integer",
    "FLOAT": "number",
    "DOUBLE": "number",
    "DECIMAL": "number",
    "NUMERIC": "number",
    "VARCHAR": "string",
    "CHAR": "string",
    "TEXT": "string",
    "TINYTEXT": "string",
    "MEDIUMTEXT": "string",
    "LONGTEXT": "string",
    "BLOB": "string",
    "ENUM": "string",
    "SET": "string",
    "DATE": "string",
    "DATETIME": "string",
    "TIMESTAMP": "string",
    "TIME": "string",
    "YEAR": "integer",
    "BOOLEAN": "boolean",
    "BOOL": "boolean",
    "JSON": "object",
    "BINARY": "string",
    "VARBINARY": "string",
}


class MysqlCollector(BaseCollector):
    """Collects schema from a MySQL database via SQLAlchemy inspect."""

    def __init__(self, connection_string: str, schema: str = "") -> None:
        self._connection_string = connection_string
        self._schema = schema or None

    @property
    def name(self) -> str:
        return "mysql"

    def collect(self) -> list[ResourceSchema]:
        engine = create_engine(self._connection_string)
        insp = inspect(engine)
        resources: list[ResourceSchema] = []

        for table_name in insp.get_table_names(schema=self._schema):
            columns = insp.get_columns(table_name, schema=self._schema)
            pk_cols = insp.get_pk_constraint(table_name, schema=self._schema)
            pk_names: set[str] = set(pk_cols.get("constrained_columns", []))

            unique_cols: set[str] = set()
            for uc in insp.get_unique_constraints(table_name, schema=self._schema):
                unique_cols.update(uc.get("column_names", []))

            fk_map: dict[str, str] = {}
            for fk in insp.get_foreign_keys(table_name, schema=self._schema):
                ref = f"{fk['referred_table']}.{fk['referred_columns'][0]}" if fk.get("referred_columns") else None
                for col in fk.get("constrained_columns", []):
                    if ref:
                        fk_map[col] = ref

            fields: list[FieldDef] = []
            for col in columns:
                col_name = col["name"]
                type_str = str(col.get("type", "VARCHAR")).upper().split("(")[0].strip()
                normalized = MYSQL_TYPE_MAP.get(type_str, "string")
                nullable = col.get("nullable", True)

                constraint = FieldConstraint(
                    primary_key=col_name in pk_names,
                    unique=col_name in unique_cols,
                    foreign_key=fk_map.get(col_name),
                )

                fields.append(
                    FieldDef(
                        name=col_name,
                        field_type=normalized,
                        nullable=nullable,
                        required=not nullable,
                        default=str(col["default"]) if col.get("default") is not None else None,
                        constraints=constraint,
                    )
                )

            resources.append(
                ResourceSchema(
                    name=table_name,
                    source_type=SourceType.MYSQL,
                    fields=fields,
                )
            )

        engine.dispose()
        return resources
