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


class DriftGuardConfig(BaseModel):
    """Top-level DriftGuard configuration."""

    version: str = "1"
    snapshot_dir: str = ".driftguard/snapshots"
    sources: list[SourceConfig] = Field(default_factory=list)
    policy_overrides: list[PolicyOverride] = Field(default_factory=list)
    report_formats: list[str] = Field(default_factory=lambda: ["terminal"])


def load_config(path: str | Path = "driftguard.yaml") -> DriftGuardConfig:
    """Load configuration from a YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    text = config_path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return DriftGuardConfig()
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
