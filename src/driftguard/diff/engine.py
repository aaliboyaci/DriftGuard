"""Semantic diff engine.

Compares two ContractSnapshots and produces a list of DiffEvents
describing every meaningful schema change between them.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from driftguard.diff.events import (
    ConstraintChanged,
    DefaultValueChanged,
    DiffEvent,
    DiffResult,
    EnumValuesChanged,
    FieldAdded,
    FieldRemoved,
    FieldRenamed,
    ForeignKeyChanged,
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

    # Default value changed
    if baseline.default != current.default:
        events.append(
            DefaultValueChanged(
                resource_name=resource_name,
                description=f"Default changed: {resource_name}.{fname} ({baseline.default} -> {current.default})",
                field_name=fname,
                old_default=str(baseline.default) if baseline.default is not None else None,
                new_default=str(current.default) if current.default is not None else None,
            )
        )

    # Constraint changes
    events.extend(_diff_constraints(resource_name, fname, baseline, current))

    return events


def _diff_constraints(resource_name: str, fname: str, baseline: FieldDef, current: FieldDef) -> list[DiffEvent]:
    """Compare constraint metadata between two field versions."""
    events: list[DiffEvent] = []
    bc = baseline.constraints
    cc = current.constraints

    if bc is None and cc is None:
        return events

    # PK changed
    b_pk = bc.primary_key if bc else False
    c_pk = cc.primary_key if cc else False
    if b_pk != c_pk:
        events.append(
            ConstraintChanged(
                resource_name=resource_name,
                description=f"Primary key changed: {resource_name}.{fname} ({b_pk} -> {c_pk})",
                field_name=fname,
                constraint_type="primary_key",
                old_value=str(b_pk),
                new_value=str(c_pk),
            )
        )

    # Unique changed
    b_unique = bc.unique if bc else False
    c_unique = cc.unique if cc else False
    if b_unique != c_unique:
        events.append(
            ConstraintChanged(
                resource_name=resource_name,
                description=f"Unique constraint changed: {resource_name}.{fname} ({b_unique} -> {c_unique})",
                field_name=fname,
                constraint_type="unique",
                old_value=str(b_unique),
                new_value=str(c_unique),
            )
        )

    # FK changed
    b_fk = bc.foreign_key if bc else None
    c_fk = cc.foreign_key if cc else None
    if b_fk != c_fk:
        events.append(
            ForeignKeyChanged(
                resource_name=resource_name,
                description=f"Foreign key changed: {resource_name}.{fname} ({b_fk} -> {c_fk})",
                field_name=fname,
                old_reference=b_fk,
                new_reference=c_fk,
            )
        )

    # Max length changed
    b_maxlen = bc.max_length if bc else None
    c_maxlen = cc.max_length if cc else None
    if b_maxlen != c_maxlen:
        events.append(
            ConstraintChanged(
                resource_name=resource_name,
                description=f"Max length changed: {resource_name}.{fname} ({b_maxlen} -> {c_maxlen})",
                field_name=fname,
                constraint_type="max_length",
                old_value=str(b_maxlen) if b_maxlen is not None else None,
                new_value=str(c_maxlen) if c_maxlen is not None else None,
            )
        )

    # Min value changed
    b_min = bc.min_value if bc else None
    c_min = cc.min_value if cc else None
    if b_min != c_min:
        events.append(
            ConstraintChanged(
                resource_name=resource_name,
                description=f"Min value changed: {resource_name}.{fname} ({b_min} -> {c_min})",
                field_name=fname,
                constraint_type="min_value",
                old_value=str(b_min) if b_min is not None else None,
                new_value=str(c_min) if c_min is not None else None,
            )
        )

    # Max value changed
    b_max = bc.max_value if bc else None
    c_max = cc.max_value if cc else None
    if b_max != c_max:
        events.append(
            ConstraintChanged(
                resource_name=resource_name,
                description=f"Max value changed: {resource_name}.{fname} ({b_max} -> {c_max})",
                field_name=fname,
                constraint_type="max_value",
                old_value=str(b_max) if b_max is not None else None,
                new_value=str(c_max) if c_max is not None else None,
            )
        )

    # Pattern changed
    b_pat = bc.pattern if bc else None
    c_pat = cc.pattern if cc else None
    if b_pat != c_pat:
        events.append(
            ConstraintChanged(
                resource_name=resource_name,
                description=f"Pattern changed: {resource_name}.{fname}",
                field_name=fname,
                constraint_type="pattern",
                old_value=b_pat,
                new_value=c_pat,
            )
        )

    return events
