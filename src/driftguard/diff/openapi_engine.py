"""OpenAPI deep diff engine.

Compares two OpenApiContracts and produces DiffEvents describing
path, method, parameter, request body, response body, and status
code changes.
"""

from __future__ import annotations

from driftguard.diff.engine import _diff_field
from driftguard.diff.events import (
    DiffEvent,
    DiffResult,
    FieldAdded,
    FieldRemoved,
    OpenApiEndpointDeprecated,
    OpenApiMethodAdded,
    OpenApiMethodRemoved,
    OpenApiParameterAdded,
    OpenApiParameterChanged,
    OpenApiParameterRemoved,
    OpenApiPathAdded,
    OpenApiPathRemoved,
    OpenApiResponseStatusAdded,
    OpenApiResponseStatusRemoved,
)
from driftguard.schema.openapi_models import (
    OpenApiContract,
    OpenApiOperation,
    OpenApiParameter,
    OpenApiResponse,
)


def compute_openapi_diff(
    baseline: OpenApiContract,
    current: OpenApiContract,
) -> DiffResult:
    """Compare two OpenAPI contracts and return all semantic diff events."""
    events: list[DiffEvent] = []

    b_paths = {p.path: p for p in baseline.paths}
    c_paths = {p.path: p for p in current.paths}

    b_names = set(b_paths.keys())
    c_names = set(c_paths.keys())

    # Removed paths
    for path in sorted(b_names - c_names):
        events.append(
            OpenApiPathRemoved(
                resource_name=path,
                description=f"Path removed: {path}",
                path=path,
            )
        )

    # Added paths
    for path in sorted(c_names - b_names):
        events.append(
            OpenApiPathAdded(
                resource_name=path,
                description=f"Path added: {path}",
                path=path,
            )
        )

    # Common paths — diff methods
    for path in sorted(b_names & c_names):
        b_ops = {op.method: op for op in b_paths[path].operations}
        c_ops = {op.method: op for op in c_paths[path].operations}
        events.extend(_diff_methods(path, b_ops, c_ops))

    baseline_label = f"{baseline.title} {baseline.version}".strip() or "baseline"
    current_label = f"{current.title} {current.version}".strip() or "current"

    return DiffResult(
        baseline_name=baseline_label,
        current_name=current_label,
        events=events,
    )


def _diff_methods(
    path: str,
    baseline: dict[str, OpenApiOperation],
    current: dict[str, OpenApiOperation],
) -> list[DiffEvent]:
    """Diff HTTP methods on a common path."""
    events: list[DiffEvent] = []

    b_methods = set(baseline.keys())
    c_methods = set(current.keys())

    for method in sorted(b_methods - c_methods):
        events.append(
            OpenApiMethodRemoved(
                resource_name=f"{method.upper()} {path}",
                description=f"Method removed: {method.upper()} {path}",
                path=path,
                method=method,
            )
        )

    for method in sorted(c_methods - b_methods):
        events.append(
            OpenApiMethodAdded(
                resource_name=f"{method.upper()} {path}",
                description=f"Method added: {method.upper()} {path}",
                path=path,
                method=method,
            )
        )

    for method in sorted(b_methods & c_methods):
        b_op = baseline[method]
        c_op = current[method]
        events.extend(_diff_operation(path, method, b_op, c_op))

    return events


def _diff_operation(
    path: str,
    method: str,
    baseline: OpenApiOperation,
    current: OpenApiOperation,
) -> list[DiffEvent]:
    """Diff a single operation (same path + method)."""
    events: list[DiffEvent] = []
    label = f"{method.upper()} {path}"

    # Deprecated detection
    if not baseline.deprecated and current.deprecated:
        events.append(
            OpenApiEndpointDeprecated(
                resource_name=label,
                description=f"Endpoint deprecated: {label}",
                path=path,
                method=method,
            )
        )

    # Parameter diff
    events.extend(_diff_parameters(path, method, baseline.parameters, current.parameters))

    # Request body diff
    events.extend(_diff_request_body(path, method, baseline, current))

    # Response diff
    events.extend(_diff_responses(path, method, baseline.responses, current.responses))

    return events


def _diff_parameters(
    path: str,
    method: str,
    baseline: list[OpenApiParameter],
    current: list[OpenApiParameter],
) -> list[DiffEvent]:
    """Diff parameters between two operations."""
    events: list[DiffEvent] = []
    label = f"{method.upper()} {path}"

    b_params = {(p.name, p.location): p for p in baseline}
    c_params = {(p.name, p.location): p for p in current}

    b_keys = set(b_params.keys())
    c_keys = set(c_params.keys())

    for name, loc in sorted(b_keys - c_keys):
        events.append(
            OpenApiParameterRemoved(
                resource_name=label,
                description=f"Parameter removed: {label} {loc} param '{name}'",
                path=path,
                method=method,
                param_name=name,
                location=loc,
            )
        )

    for name, loc in sorted(c_keys - b_keys):
        cp = c_params[(name, loc)]
        events.append(
            OpenApiParameterAdded(
                resource_name=label,
                description=f"Parameter added: {label} {loc} param '{name}'" + (" (required)" if cp.required else ""),
                path=path,
                method=method,
                param_name=name,
                location=loc,
                required=cp.required,
            )
        )

    # Changed parameters
    for key in sorted(b_keys & c_keys):
        bp = b_params[key]
        cp = c_params[key]
        name, loc = key

        changes: list[str] = []
        if bp.required != cp.required:
            changes.append(f"required: {bp.required} -> {cp.required}")
        if bp.param_type != cp.param_type:
            changes.append(f"type: {bp.param_type} -> {cp.param_type}")

        if changes:
            detail = "; ".join(changes)
            events.append(
                OpenApiParameterChanged(
                    resource_name=label,
                    description=f"Parameter changed: {label} {loc} param '{name}' ({detail})",
                    path=path,
                    method=method,
                    param_name=name,
                    location=loc,
                    change_detail=detail,
                )
            )

    return events


def _diff_request_body(
    path: str,
    method: str,
    baseline: OpenApiOperation,
    current: OpenApiOperation,
) -> list[DiffEvent]:
    """Diff request body fields between two operations.

    Uses existing field diff logic with OpenAPI-aware resource names.
    Request field added (required) = breaking for consumers/clients.
    Request field removed = info/warning (relaxes contract).
    """
    events: list[DiffEvent] = []
    label = f"{method.upper()} {path}"
    ctx = f"{label} request"

    b_fields = baseline.request_body.fields if baseline.request_body else []
    c_fields = current.request_body.fields if current.request_body else []

    if not b_fields and not c_fields:
        return events

    b_map = {f.name: f for f in b_fields}
    c_map = {f.name: f for f in c_fields}

    # Added request fields
    for name in sorted(set(c_map) - set(b_map)):
        cf = c_map[name]
        events.append(
            FieldAdded(
                resource_name=ctx,
                description=f"Request field added: {label} body '{name}' ({cf.field_type})"
                + (" (required)" if cf.required else ""),
                field_name=name,
                field_type=cf.field_type,
                required=cf.required,
            )
        )

    # Removed request fields
    for name in sorted(set(b_map) - set(c_map)):
        bf = b_map[name]
        events.append(
            FieldRemoved(
                resource_name=ctx,
                description=f"Request field removed: {label} body '{name}' ({bf.field_type})",
                field_name=name,
                field_type=bf.field_type,
            )
        )

    # Changed request fields
    for name in sorted(set(b_map) & set(c_map)):
        events.extend(_diff_field(ctx, b_map[name], c_map[name]))

    return events


def _diff_responses(
    path: str,
    method: str,
    baseline: list[OpenApiResponse],
    current: list[OpenApiResponse],
) -> list[DiffEvent]:
    """Diff response status codes and body fields."""
    events: list[DiffEvent] = []
    label = f"{method.upper()} {path}"

    b_resps = {r.status_code: r for r in baseline}
    c_resps = {r.status_code: r for r in current}

    b_codes = set(b_resps.keys())
    c_codes = set(c_resps.keys())

    # Removed status codes
    for code in sorted(b_codes - c_codes):
        events.append(
            OpenApiResponseStatusRemoved(
                resource_name=label,
                description=f"Response status removed: {label} {code}",
                path=path,
                method=method,
                status_code=code,
            )
        )

    # Added status codes
    for code in sorted(c_codes - b_codes):
        events.append(
            OpenApiResponseStatusAdded(
                resource_name=label,
                description=f"Response status added: {label} {code}",
                path=path,
                method=method,
                status_code=code,
            )
        )

    # Common status codes — diff response body fields
    for code in sorted(b_codes & c_codes):
        ctx = f"{label} {code} response"
        b_fields = {f.name: f for f in b_resps[code].fields}
        c_fields = {f.name: f for f in c_resps[code].fields}

        # Removed response fields
        for name in sorted(set(b_fields) - set(c_fields)):
            bf = b_fields[name]
            events.append(
                FieldRemoved(
                    resource_name=ctx,
                    description=f"Response field removed: {label} {code} '{name}' ({bf.field_type})",
                    field_name=name,
                    field_type=bf.field_type,
                )
            )

        # Added response fields
        for name in sorted(set(c_fields) - set(b_fields)):
            cf = c_fields[name]
            events.append(
                FieldAdded(
                    resource_name=ctx,
                    description=f"Response field added: {label} {code} '{name}' ({cf.field_type})",
                    field_name=name,
                    field_type=cf.field_type,
                    required=cf.required,
                )
            )

        # Changed response fields
        for name in sorted(set(b_fields) & set(c_fields)):
            events.extend(_diff_field(ctx, b_fields[name], c_fields[name]))

    return events
