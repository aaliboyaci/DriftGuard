"""Registry domain models for cross-service contract management."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ServiceMetadata(BaseModel):
    """Metadata describing a service that publishes or consumes contracts."""

    service_name: str
    service_version: str = ""
    role: str = "producer"  # "producer" or "consumer"
    description: str = ""
    owner: str = ""


class ServiceDependency(BaseModel):
    """A dependency declaration: which contract fields a consumer relies on."""

    service_name: str
    contract_name: str  # which contract this service consumes
    required_fields: list[str] = Field(default_factory=list)  # paths consumer depends on


class RegistryConfig(BaseModel):
    """Configuration for a service's registry participation."""

    service: ServiceMetadata
    dependencies: list[ServiceDependency] = Field(default_factory=list)
