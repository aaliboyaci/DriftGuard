"""Configuration models for DriftGuard.

Parsed from driftguard.yaml in the project root. Defines which sources
to monitor and any policy overrides.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from driftguard.schema.models import SourceType


class SourceConfig(BaseModel):
    """Configuration for a single data source."""

    name: str
    type: SourceType
    connection: str | None = Field(default=None, description="Connection string for databases")
    path: str | None = Field(default=None, description="File path for file-based sources")
    options: dict[str, Any] = Field(default_factory=dict)


class PolicyOverride(BaseModel):
    """Override default risk level for specific change patterns."""

    resource: str | None = Field(default=None, description="Resource name pattern (supports *)")
    field: str | None = Field(default=None, description="Field name pattern (supports *)")
    category: str | None = Field(default=None, description="Change category to match")
    severity: str = Field(description="Override severity: breaking, warning, info, ignore")


class NotificationConfig(BaseModel):
    """Notification settings for drift alerts."""

    enabled: bool = False
    channels: list[str] = Field(default_factory=list, description="Notification channels: slack, email, webhook")
    webhook_url: str | None = Field(default=None, description="Webhook URL for notifications")
    on_breaking: bool = True
    on_warning: bool = False


class DriftGuardConfig(BaseModel):
    """Top-level DriftGuard configuration."""

    version: str = "1"
    schema_version: int = Field(default=1, description="Config schema version for migration support")
    project_name: str | None = Field(default=None, description="Project name for reports and snapshots")
    environment: str | None = Field(default=None, description="Environment: dev, staging, production")
    owner_team: str | None = Field(default=None, description="Team owning this project's contracts")
    snapshot_dir: str = ".driftguard/snapshots"
    sources: list[SourceConfig] = Field(default_factory=list)
    policy_overrides: list[PolicyOverride] = Field(default_factory=list)
    report_formats: list[str] = Field(default_factory=lambda: ["terminal"])
    notification: NotificationConfig = Field(default_factory=NotificationConfig)


CURRENT_SCHEMA_VERSION = 1


def _migrate_config(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate config data from older schema versions to current.

    Each migration step transforms the data dict in-place and bumps
    the schema_version. Add new migrations as elif branches.
    """
    schema_ver = data.get("schema_version", 0)

    if schema_ver < 1:
        # v0 -> v1: ensure new fields have defaults
        data.setdefault("schema_version", 1)
        data.setdefault("project_name", None)
        data.setdefault("environment", None)
        data.setdefault("owner_team", None)
        data.setdefault("notification", {})

    data["schema_version"] = CURRENT_SCHEMA_VERSION
    return data


def load_config(path: str | Path = "driftguard.yaml") -> DriftGuardConfig:
    """Load configuration from a YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    text = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return DriftGuardConfig()
    data = _migrate_config(data)
    return DriftGuardConfig.model_validate(data)


def default_config() -> DriftGuardConfig:
    """Return a default configuration for `driftguard init`."""
    return DriftGuardConfig(
        sources=[
            SourceConfig(
                name="example-api",
                type=SourceType.OPENAPI,
                path="openapi.yaml",
            ),
        ],
        report_formats=["terminal", "markdown"],
    )


def save_config(config: DriftGuardConfig, path: str | Path = "driftguard.yaml") -> Path:
    """Save configuration to a YAML file."""
    config_path = Path(path)
    data = config.model_dump(mode="json", exclude_none=True)
    text = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    config_path.write_text(text, encoding="utf-8")
    return config_path
