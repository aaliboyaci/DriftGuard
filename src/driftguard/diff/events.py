"""Semantic diff event models.

Each event represents a specific kind of schema change detected between
a baseline and current snapshot. The policy engine uses these events
to determine risk severity.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ChangeCategory(str, Enum):
    """High-level category of a schema change."""

    RESOURCE_ADDED = "resource_added"
    RESOURCE_REMOVED = "resource_removed"
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    FIELD_RENAMED = "field_renamed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_CHANGED = "nullable_changed"
    REQUIRED_CHANGED = "required_changed"
    ENUM_VALUES_CHANGED = "enum_values_changed"


class DiffEvent(BaseModel):
    """Base class for all semantic diff events."""

    category: ChangeCategory
    resource_name: str = Field(description="Name of the affected resource (table, endpoint, etc.)")
    description: str = Field(description="Human-readable description of the change")


class ResourceAdded(DiffEvent):
    """A new resource appeared in the current snapshot."""

    category: ChangeCategory = ChangeCategory.RESOURCE_ADDED


class ResourceRemoved(DiffEvent):
    """A resource was removed from the current snapshot."""

    category: ChangeCategory = ChangeCategory.RESOURCE_REMOVED


class FieldAdded(DiffEvent):
    """A new field was added to a resource."""

    category: ChangeCategory = ChangeCategory.FIELD_ADDED
    field_name: str
    field_type: str
    required: bool = False
    nullable: bool = False


class FieldRemoved(DiffEvent):
    """A field was removed from a resource."""

    category: ChangeCategory = ChangeCategory.FIELD_REMOVED
    field_name: str
    field_type: str


class FieldRenamed(DiffEvent):
    """A field was renamed (detected as remove + add with same type)."""

    category: ChangeCategory = ChangeCategory.FIELD_RENAMED
    old_name: str
    new_name: str
    field_type: str


class TypeChanged(DiffEvent):
    """A field's data type was changed."""

    category: ChangeCategory = ChangeCategory.TYPE_CHANGED
    field_name: str
    old_type: str
    new_type: str


class NullableChanged(DiffEvent):
    """A field's nullable property was changed."""

    category: ChangeCategory = ChangeCategory.NULLABLE_CHANGED
    field_name: str
    old_nullable: bool
    new_nullable: bool


class RequiredChanged(DiffEvent):
    """A field's required property was changed."""

    category: ChangeCategory = ChangeCategory.REQUIRED_CHANGED
    field_name: str
    old_required: bool
    new_required: bool


class EnumValuesChanged(DiffEvent):
    """A field's allowed enum values were changed."""

    category: ChangeCategory = ChangeCategory.ENUM_VALUES_CHANGED
    field_name: str
    added_values: list[str] = Field(default_factory=list)
    removed_values: list[str] = Field(default_factory=list)


class DiffResult(BaseModel):
    """Complete result of comparing two snapshots."""

    baseline_name: str
    current_name: str
    events: list[DiffEvent] = Field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return len(self.events) > 0

    @property
    def event_count(self) -> int:
        return len(self.events)

    def events_by_category(self, category: ChangeCategory) -> list[DiffEvent]:
        return [e for e in self.events if e.category == category]

    def events_for_resource(self, resource_name: str) -> list[DiffEvent]:
        return [e for e in self.events if e.resource_name == resource_name]
