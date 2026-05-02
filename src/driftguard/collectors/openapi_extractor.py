"""OpenAPI deep extractor.

Parses an OpenAPI 3.x or Swagger 2.x spec into structured
OpenApiContract with path, method, parameter, request body,
response, and status code detail.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from driftguard.collectors.json_collector import _extract_fields_from_schema
from driftguard.schema.models import FieldDef
from driftguard.schema.openapi_models import (
    OpenApiContract,
    OpenApiOperation,
    OpenApiParameter,
    OpenApiPath,
    OpenApiRequestBody,
    OpenApiResponse,
)


def extract_openapi_contract(file_path: str | Path) -> OpenApiContract:
    """Parse an OpenAPI spec file into an OpenApiContract."""
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    if path.suffix in (".yaml", ".yml"):
        spec = yaml.safe_load(text)
    else:
        spec = json.loads(text)
    return extract_from_dict(spec)


def extract_from_dict(spec: dict[str, Any]) -> OpenApiContract:
    """Extract OpenApiContract from a parsed spec dictionary."""
    info = spec.get("info", {})
    title = info.get("title", "")
    version = info.get("version", "")

    paths = _extract_paths(spec)

    return OpenApiContract(
        title=title,
        version=version,
        paths=paths,
    )


def _extract_paths(spec: dict[str, Any]) -> list[OpenApiPath]:
    """Extract all paths from the spec."""
    raw_paths = spec.get("paths", {})
    result: list[OpenApiPath] = []

    for path_str, path_def in sorted(raw_paths.items()):
        if not isinstance(path_def, dict):
            continue

        # Path-level parameters
        path_params = _extract_parameters(path_def.get("parameters", []), spec)

        operations = _extract_operations(path_def, spec, path_params)

        result.append(
            OpenApiPath(
                path=path_str,
                operations=operations,
                parameters=path_params,
            )
        )

    return result


def _extract_operations(
    path_def: dict[str, Any],
    spec: dict[str, Any],
    path_params: list[OpenApiParameter],
) -> list[OpenApiOperation]:
    """Extract all HTTP method operations from a path definition."""
    http_methods = ("get", "post", "put", "patch", "delete", "head", "options")
    operations: list[OpenApiOperation] = []

    for method in http_methods:
        op_def = path_def.get(method)
        if op_def is None or not isinstance(op_def, dict):
            continue

        # Merge path-level + operation-level parameters
        op_params = _extract_parameters(op_def.get("parameters", []), spec)
        merged_params = _merge_parameters(path_params, op_params)

        request_body = _extract_request_body(op_def, spec)
        responses = _extract_responses(op_def, spec)

        operations.append(
            OpenApiOperation(
                method=method,
                operation_id=op_def.get("operationId"),
                summary=op_def.get("summary"),
                deprecated=op_def.get("deprecated", False),
                parameters=merged_params,
                request_body=request_body,
                responses=responses,
                tags=op_def.get("tags", []),
            )
        )

    return operations


def _extract_parameters(
    params_list: list[dict[str, Any]],
    spec: dict[str, Any],
) -> list[OpenApiParameter]:
    """Extract parameter definitions, resolving $ref."""
    result: list[OpenApiParameter] = []

    for param_def in params_list:
        resolved = _resolve_ref(param_def, spec)
        if not isinstance(resolved, dict):
            continue

        # Determine type from schema (OpenAPI 3.x) or type (Swagger 2.x)
        schema = resolved.get("schema", {})
        param_type = schema.get("type", resolved.get("type", "string"))
        enum_values = schema.get("enum", resolved.get("enum"))

        result.append(
            OpenApiParameter(
                name=resolved.get("name", ""),
                location=resolved.get("in", "query"),
                required=resolved.get("required", False),
                param_type=param_type,
                description=resolved.get("description"),
                enum_values=[str(v) for v in enum_values] if enum_values else None,
                default=schema.get("default", resolved.get("default")),
            )
        )

    return result


def _merge_parameters(
    path_params: list[OpenApiParameter],
    op_params: list[OpenApiParameter],
) -> list[OpenApiParameter]:
    """Merge path-level and operation-level parameters.

    Operation-level parameters override path-level ones with same name+location.
    """
    merged: dict[tuple[str, str], OpenApiParameter] = {}
    for p in path_params:
        merged[(p.name, p.location)] = p
    for p in op_params:
        merged[(p.name, p.location)] = p
    return list(merged.values())


def _extract_request_body(
    op_def: dict[str, Any],
    spec: dict[str, Any],
) -> OpenApiRequestBody | None:
    """Extract request body from an operation.

    Handles OpenAPI 3.x requestBody and Swagger 2.x body parameters.
    """
    # OpenAPI 3.x
    rb = op_def.get("requestBody")
    if rb is not None:
        resolved = _resolve_ref(rb, spec)
        required = resolved.get("required", False)
        content = resolved.get("content", {})

        # Prefer application/json
        for ct in ("application/json", "application/xml", "multipart/form-data"):
            if ct in content:
                schema = _resolve_ref(content[ct].get("schema", {}), spec)
                fields = _extract_fields_from_schema(schema)
                return OpenApiRequestBody(
                    content_type=ct,
                    required=required,
                    fields=fields,
                )

        # Fallback: first content type
        if content:
            first_ct = next(iter(content))
            schema = _resolve_ref(content[first_ct].get("schema", {}), spec)
            fields = _extract_fields_from_schema(schema)
            return OpenApiRequestBody(
                content_type=first_ct,
                required=required,
                fields=fields,
            )

    # Swagger 2.x: body parameter
    for param in op_def.get("parameters", []):
        resolved = _resolve_ref(param, spec)
        if resolved.get("in") == "body":
            schema = _resolve_ref(resolved.get("schema", {}), spec)
            fields = _extract_fields_from_schema(schema)
            return OpenApiRequestBody(
                content_type="application/json",
                required=resolved.get("required", False),
                fields=fields,
            )

    return None


def _extract_responses(
    op_def: dict[str, Any],
    spec: dict[str, Any],
) -> list[OpenApiResponse]:
    """Extract all response definitions from an operation."""
    raw_responses = op_def.get("responses", {})
    result: list[OpenApiResponse] = []

    for status_code, resp_def in sorted(raw_responses.items(), key=lambda x: str(x[0])):
        resolved = _resolve_ref(resp_def, spec)
        description = resolved.get("description")
        fields = _extract_response_fields(resolved, spec)

        result.append(
            OpenApiResponse(
                status_code=str(status_code),
                description=description,
                fields=fields,
            )
        )

    return result


def _extract_response_fields(
    resp_def: dict[str, Any],
    spec: dict[str, Any],
) -> list[FieldDef]:
    """Extract fields from a response definition.

    Handles OpenAPI 3.x content and Swagger 2.x schema.
    """
    # OpenAPI 3.x
    content = resp_def.get("content", {})
    for ct in ("application/json", "application/xml"):
        if ct in content:
            schema = _resolve_ref(content[ct].get("schema", {}), spec)
            # Handle array responses
            if schema.get("type") == "array":
                items = _resolve_ref(schema.get("items", {}), spec)
                return _extract_fields_from_schema(items)
            return _extract_fields_from_schema(schema)

    # Swagger 2.x
    schema = resp_def.get("schema")
    if schema is not None:
        resolved = _resolve_ref(schema, spec)
        if resolved.get("type") == "array":
            items = _resolve_ref(resolved.get("items", {}), spec)
            return _extract_fields_from_schema(items)
        return _extract_fields_from_schema(resolved)

    return []


def _resolve_ref(obj: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Resolve a $ref pointer to its target definition."""
    ref = obj.get("$ref")
    if ref is None:
        return obj

    # Handle #/components/schemas/X or #/definitions/X format
    parts = ref.lstrip("#/").split("/")
    target: Any = spec
    for part in parts:
        if isinstance(target, dict):
            target = target.get(part, {})
        else:
            return obj

    if isinstance(target, dict):
        return target
    return obj
