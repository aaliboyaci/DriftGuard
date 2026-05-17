"""Core schema models for DriftGuard.

These models represent the normalized internal representation of schemas
from any source (database, API, file). All collectors must produce these models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Type of data source a schema was collected from."""

    POSTGRES = "postgres"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    OPENAPI = "openapi"
    JSON_SCHEMA = "json_schema"
    JSON_PAYLOAD = "json_payload"
    CSV = "csv"
    PARQUET = "parquet"
    SEQUELIZE = "sequelize"
    PRISMA = "prisma"


class FieldConstraint(BaseModel):
    """Constraint metadata for a field."""

    primary_key: bool = False
    unique: bool = False
    foreign_key: str | None = None
    check: str | None = None
    max_length: int | None = None
    min_value: float | None = None
    max_value: float | None = None
    pattern: str | None = None


class FieldDef(BaseModel):
    """Definition of a single field/column in a resource schema.

    This is the atomic unit of schema comparison. The diff engine
    compares FieldDefs between baseline and current snapshots.
    """

    name: str
    field_type: str = Field(description="Normalized type: string, integer, number, boolean, array, object, null")
    nullable: bool = False
    required: bool = True
    default: Any = None
    description: str | None = None
    enum_values: list[str] | None = None
    constraints: FieldConstraint | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceSchema(BaseModel):
    """Schema of a single resource (table, endpoint, topic, file).

    A resource is the unit of ownership: one table, one API endpoint,
    one event topic, or one file format.
    """

    name: str = Field(description="Resource identifier: table name, endpoint path, topic name, file path")
    source_type: SourceType
    fields: list[FieldDef] = Field(default_factory=list)
    version: str | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_field(self, field_name: str) -> FieldDef | None:
        """Look up a field by name."""
        for f in self.fields:
            if f.name == field_name:
                return f
        return None

    @property
    def field_names(self) -> set[str]:
        """Return all field names in this resource."""
        return {f.name for f in self.fields}


class ContractSnapshot(BaseModel):
    """Point-in-time snapshot of all resource schemas.

    This is the top-level model that gets serialized to the snapshot store.
    Diff engine compares two ContractSnapshots to produce DiffEvents.
    """

    name: str = Field(description="Snapshot identifier, e.g. 'baseline', 'v1.2.0', '2025-04-25'")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    schema_version: int = Field(default=1, description="Snapshot schema version for backward compat")
    created_by: str | None = Field(default=None, description="User or system that created this snapshot")
    git_commit_sha: str | None = Field(default=None, description="Git commit SHA at snapshot time")
    branch_name: str | None = Field(default=None, description="Git branch name at snapshot time")
    source_hash: str | None = Field(default=None, description="Hash of source data for change detection")
    collector_version: str | None = Field(default=None, description="Version of collector used")
    environment: str | None = Field(default=None, description="Environment: dev, staging, production")
    tags: list[str] = Field(default_factory=list, description="Free-form tags for filtering/grouping")
    description: str | None = Field(default=None, description="Human-readable description of this snapshot")
    resources: list[ResourceSchema] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def get_resource(self, resource_name: str) -> ResourceSchema | None:
        """Look up a resource by name."""
        for r in self.resources:
            if r.name == resource_name:
                return r
        return None

    @property
    def resource_names(self) -> set[str]:
        """Return all resource names in this snapshot."""
        return {r.name for r in self.resources}
