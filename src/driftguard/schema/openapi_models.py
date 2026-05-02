"""OpenAPI deep diff models.

Structured representation of OpenAPI specs at the path, method,
parameter, request body, response, and status code level.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from driftguard.schema.models import FieldDef


class OpenApiParameter(BaseModel):
    """A single query, path, or header parameter."""

    name: str
    location: str = Field(description="Parameter location: query, path, header, cookie")
    required: bool = False
    param_type: str = "string"
    description: str | None = None
    enum_values: list[str] | None = None
    default: Any = None


class OpenApiRequestBody(BaseModel):
    """Request body schema for an operation."""

    content_type: str = "application/json"
    required: bool = False
    fields: list[FieldDef] = Field(default_factory=list)


class OpenApiResponse(BaseModel):
    """Response schema for a specific status code."""

    status_code: str = Field(description="HTTP status code: 200, 404, default, etc.")
    description: str | None = None
    fields: list[FieldDef] = Field(default_factory=list)


class OpenApiOperation(BaseModel):
    """A single HTTP method on a path (e.g., GET /pets)."""

    method: str = Field(description="HTTP method: get, post, put, patch, delete")
    operation_id: str | None = None
    summary: str | None = None
    deprecated: bool = False
    parameters: list[OpenApiParameter] = Field(default_factory=list)
    request_body: OpenApiRequestBody | None = None
    responses: list[OpenApiResponse] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class OpenApiPath(BaseModel):
    """A single API path with all its operations."""

    path: str = Field(description="URL path, e.g. /pets, /pets/{petId}")
    operations: list[OpenApiOperation] = Field(default_factory=list)
    parameters: list[OpenApiParameter] = Field(
        default_factory=list,
        description="Path-level parameters inherited by all operations",
    )


class OpenApiContract(BaseModel):
    """Complete structured representation of an OpenAPI spec."""

    title: str = ""
    version: str = ""
    paths: list[OpenApiPath] = Field(default_factory=list)

    def get_path(self, path: str) -> OpenApiPath | None:
        for p in self.paths:
            if p.path == path:
                return p
        return None

    def get_operation(self, path: str, method: str) -> OpenApiOperation | None:
        p = self.get_path(path)
        if p is None:
            return None
        method_lower = method.lower()
        for op in p.operations:
            if op.method == method_lower:
                return op
        return None

    @property
    def path_names(self) -> list[str]:
        return [p.path for p in self.paths]

    @property
    def operation_count(self) -> int:
        return sum(len(p.operations) for p in self.paths)
