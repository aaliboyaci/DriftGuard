"""Semantic diff engine.

Compares two ContractSnapshots and produces a list of DiffEvents
describing every meaningful schema change between them.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from driftguard.diff.events import (
    DiffEvent,
    DiffResult,
    EnumValuesChanged,
    FieldAdded,
    FieldRemoved,
    FieldRenamed,
    NullableChanged,
    RequiredChanged,
    ResourceAdded,
    ResourceRemoved,
    TypeChanged,
)
from driftguard.schema.models import ContractSnapshot, FieldDef, ResourceSchema

RENAME_SIMILARITY_THRESHOLD = 0.5


def compute_diff(baseline: ContractSnapshot, current: ContractSnapshot) -> DiffResult:
    """Compare baseline and current snapshots, return all semantic diff events."""
    events: list[DiffEvent] = []

    baseline_names = baseline.resource_names
    current_names = current.resource_names

    # Removed resources
    for name in sorted(baseline_names - current_names):
        events.append(ResourceRemoved(resource_name=name, description=f"Resource removed: {name}"))

    # Added resources
    for name in sorted(current_names - baseline_names):
        events.append(ResourceAdded(resource_name=name, description=f"Resource added: {name}"))

    # Changed resources
    for name in sorted(baseline_names & current_names):
        b_resource = baseline.get_resource(name)
        c_resource = current.get_resource(name)
        assert b_resource is not None
        assert c_resource is not None
        events.extend(_diff_resource(b_resource, c_resource))

    return DiffResult(
        baseline_name=baseline.name,
        current_name=current.name,
        events=events,
    )


def _detect_renames(
    removed: dict[str, FieldDef], added: dict[str, FieldDef], resource_name: str
) -> list[tuple[str, str, FieldDef]]:
    """Detect probable renames among removed/added fields using fuzzy name matching.

    Returns list of (old_name, new_name, new_field) tuples for matches.
    Only matches fields with the same type and similarity above threshold.
    """
    renames: list[tuple[str, str, FieldDef]] = []
    matched_added: set[str] = set()

    for old_name, old_field in removed.items():
        best_score = 0.0
        best_match: str | None = None
        for new_name, new_field in added.items():
            if new_name in matched_added:
                continue
            if old_field.field_type != new_field.field_type:
                continue
            score = SequenceMatcher(None, old_name, new_name).ratio()
            if score > best_score and score >= RENAME_SIMILARITY_THRESHOLD:
                best_score = score
                best_match = new_name
        if best_match is not None:
            renames.append((old_name, best_match, added[best_match]))
            matched_added.add(best_match)

    return renames


def _diff_resource(baseline: ResourceSchema, current: ResourceSchema) -> list[DiffEvent]:
    """Compare two versions of the same resource and return field-level events."""
    events: list[DiffEvent] = []
    resource_name = baseline.name

    b_fields = {f.name: f for f in baseline.fields}
    c_fields = {f.name: f for f in current.fields}

    b_names = set(b_fields.keys())
    c_names = set(c_fields.keys())

    removed_fields = {n: b_fields[n] for n in sorted(b_names - c_names)}
    added_fields = {n: c_fields[n] for n in sorted(c_names - b_names)}

    # Detect renames from removed+added pairs
    renames = _detect_renames(removed_fields, added_fields, resource_name)
    renamed_old = {old for old, _, _ in renames}
    renamed_new = {new for _, new, _ in renames}

    for old_name, new_name, new_field in renames:
        events.append(
            FieldRenamed(
                resource_name=resource_name,
                description=f"Field renamed: {resource_name}.{old_name} -> {new_name}",
                old_name=old_name,
                new_name=new_name,
                field_type=new_field.field_type,
            )
        )

    # Removed fields (excluding renames)
    for fname in sorted(b_names - c_names):
        if fname in renamed_old:
            continue
        bf = b_fields[fname]
        events.append(
            FieldRemoved(
                resource_name=resource_name,
                description=f"Field removed: {resource_name}.{fname} ({bf.field_type})",
                field_name=fname,
                field_type=bf.field_type,
            )
        )

    # Added fields (excluding renames)
    for fname in sorted(c_names - b_names):
        if fname in renamed_new:
            continue
        cf = c_fields[fname]
        events.append(
            FieldAdded(
                resource_name=resource_name,
                description=f"Field added: {resource_name}.{fname} ({cf.field_type})",
                field_name=fname,
                field_type=cf.field_type,
                required=cf.required,
                nullable=cf.nullable,
            )
        )

    # Changed fields
    for fname in sorted(b_names & c_names):
        bf = b_fields[fname]
        cf = c_fields[fname]
        events.extend(_diff_field(resource_name, bf, cf))

    return events


def _diff_field(resource_name: str, baseline: FieldDef, current: FieldDef) -> list[DiffEvent]:
    """Compare two versions of the same field and return change events."""
    events: list[DiffEvent] = []
    fname = baseline.name

    # Type changed
    if baseline.field_type != current.field_type:
        events.append(
            TypeChanged(
                resource_name=resource_name,
                description=f"Type changed: {resource_name}.{fname} ({baseline.field_type} -> {current.field_type})",
                field_name=fname,
                old_type=baseline.field_type,
                new_type=current.field_type,
            )
        )

    # Nullable changed
    if baseline.nullable != current.nullable:
        events.append(
            NullableChanged(
                resource_name=resource_name,
                description=f"Nullable changed: {resource_name}.{fname} ({baseline.nullable} -> {current.nullable})",
                field_name=fname,
                old_nullable=baseline.nullable,
                new_nullable=current.nullable,
            )
        )

    # Required changed
    if baseline.required != current.required:
        events.append(
            RequiredChanged(
                resource_name=resource_name,
                description=f"Required changed: {resource_name}.{fname} ({baseline.required} -> {current.required})",
                field_name=fname,
                old_required=baseline.required,
                new_required=current.required,
            )
        )

    # Enum values changed
    if baseline.enum_values is not None or current.enum_values is not None:
        b_enums = set(baseline.enum_values or [])
        c_enums = set(current.enum_values or [])
        added = sorted(c_enums - b_enums)
        removed = sorted(b_enums - c_enums)
        if added or removed:
            events.append(
                EnumValuesChanged(
                    resource_name=resource_name,
                    description=f"Enum values changed: {resource_name}.{fname}",
                    field_name=fname,
                    added_values=added,
                    removed_values=removed,
                )
            )

    return events
