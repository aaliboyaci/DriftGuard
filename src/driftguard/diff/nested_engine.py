"""Nested / JSONB diff engine.

Compares two NestedContracts and produces DiffEvents describing
field path additions, removals, type changes, required/nullable
changes, and enum candidate changes.
"""

from __future__ import annotations

from driftguard.diff.events import (
    DiffEvent,
    DiffResult,
    NestedEnumValuesChanged,
    NestedFieldAdded,
    NestedFieldNullableChanged,
    NestedFieldRemoved,
    NestedFieldRequiredChanged,
    NestedFieldTypeChanged,
)
from driftguard.schema.nested_models import NestedContract, NestedResource


def compute_nested_diff(
    baseline: NestedContract,
    current: NestedContract,
) -> DiffResult:
    """Compare two nested contracts and return all semantic diff events."""
    events: list[DiffEvent] = []

    b_resources = {r.name: r for r in baseline.resources}
    c_resources = {r.name: r for r in current.resources}

    # Only diff common resources (resource add/remove handled elsewhere)
    common_names = set(b_resources.keys()) & set(c_resources.keys())

    for name in sorted(common_names):
        events.extend(_diff_nested_resource(name, b_resources[name], c_resources[name]))

    return DiffResult(
        baseline_name=baseline.name,
        current_name=current.name,
        events=events,
    )


def _diff_nested_resource(
    resource_name: str,
    baseline: NestedResource,
    current: NestedResource,
) -> list[DiffEvent]:
    """Diff fields within a single nested resource."""
    events: list[DiffEvent] = []

    b_paths = baseline.field_paths
    c_paths = current.field_paths

    # Removed paths
    for path in sorted(b_paths - c_paths):
        b_field = baseline.get_field(path)
        assert b_field is not None
        events.append(
            NestedFieldRemoved(
                resource_name=resource_name,
                description=f"Nested field removed: {resource_name}.{path} ({b_field.field_type.value})",
                path=path,
                field_type=b_field.field_type.value,
                confidence=b_field.confidence,
            )
        )

    # Added paths
    for path in sorted(c_paths - b_paths):
        c_field = current.get_field(path)
        assert c_field is not None
        events.append(
            NestedFieldAdded(
                resource_name=resource_name,
                description=f"Nested field added: {resource_name}.{path} ({c_field.field_type.value})"
                + (" (required)" if c_field.required else ""),
                path=path,
                field_type=c_field.field_type.value,
                required=c_field.required,
                confidence=c_field.confidence,
            )
        )

    # Common paths — check for changes
    for path in sorted(b_paths & c_paths):
        b_field = baseline.get_field(path)
        c_field = current.get_field(path)
        assert b_field is not None
        assert c_field is not None

        # Type changed
        if b_field.field_type != c_field.field_type:
            events.append(
                NestedFieldTypeChanged(
                    resource_name=resource_name,
                    description=(
                        f"Nested field type changed: {resource_name}.{path} "
                        f"({b_field.field_type.value} -> {c_field.field_type.value})"
                    ),
                    path=path,
                    old_type=b_field.field_type.value,
                    new_type=c_field.field_type.value,
                    confidence=c_field.confidence,
                )
            )

        # Required changed
        if b_field.required != c_field.required:
            events.append(
                NestedFieldRequiredChanged(
                    resource_name=resource_name,
                    description=(
                        f"Nested field required changed: {resource_name}.{path} "
                        f"({b_field.required} -> {c_field.required})"
                    ),
                    path=path,
                    old_required=b_field.required,
                    new_required=c_field.required,
                    confidence=c_field.confidence,
                )
            )

        # Nullable changed
        if b_field.nullable != c_field.nullable:
            events.append(
                NestedFieldNullableChanged(
                    resource_name=resource_name,
                    description=(
                        f"Nested field nullable changed: {resource_name}.{path} "
                        f"({b_field.nullable} -> {c_field.nullable})"
                    ),
                    path=path,
                    old_nullable=b_field.nullable,
                    new_nullable=c_field.nullable,
                    confidence=c_field.confidence,
                )
            )

        # Enum values changed
        b_enums = set(b_field.enum_candidates) if b_field.enum_candidates else set()
        c_enums = set(c_field.enum_candidates) if c_field.enum_candidates else set()

        if b_enums != c_enums:
            added = sorted(c_enums - b_enums)
            removed = sorted(b_enums - c_enums)
            events.append(
                NestedEnumValuesChanged(
                    resource_name=resource_name,
                    description=(f"Nested enum values changed: {resource_name}.{path} (+{added}, -{removed})"),
                    path=path,
                    added_values=added,
                    removed_values=removed,
                    confidence=c_field.confidence,
                )
            )

    return events
