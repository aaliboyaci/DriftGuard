"""Tests for configuration models."""

import pytest
import yaml

from driftguard.config import (
    DriftGuardConfig,
    NotificationConfig,
    PolicyOverride,
    SourceConfig,
    default_config,
    load_config,
    save_config,
)
from driftguard.schema.models import SourceType


class TestDriftGuardConfig:
    def test_defaults(self) -> None:
        c = DriftGuardConfig()
        assert c.version == "1"
        assert c.project_name is None
        assert c.snapshot_dir == ".driftguard/snapshots"
        assert c.sources == []
        assert c.report_formats == ["terminal"]

    def test_project_name(self) -> None:
        c = DriftGuardConfig(project_name="my-service")
        assert c.project_name == "my-service"

    def test_environment(self) -> None:
        c = DriftGuardConfig(environment="production")
        assert c.environment == "production"

    def test_owner_team(self) -> None:
        c = DriftGuardConfig(owner_team="platform-eng")
        assert c.owner_team == "platform-eng"

    def test_schema_version(self) -> None:
        c = DriftGuardConfig()
        assert c.schema_version == 1

    def test_notification_defaults(self) -> None:
        c = DriftGuardConfig()
        assert c.notification.enabled is False
        assert c.notification.channels == []
        assert c.notification.on_breaking is True
        assert c.notification.on_warning is False

    def test_notification_config(self) -> None:
        n = NotificationConfig(enabled=True, channels=["slack"], webhook_url="https://hooks.example.com/drift")
        c = DriftGuardConfig(notification=n)
        assert c.notification.enabled is True
        assert c.notification.webhook_url == "https://hooks.example.com/drift"

    def test_with_sources(self) -> None:
        c = DriftGuardConfig(
            sources=[
                SourceConfig(name="db", type=SourceType.POSTGRES, connection="postgresql://localhost/test"),
                SourceConfig(name="api", type=SourceType.OPENAPI, path="openapi.yaml"),
            ]
        )
        assert len(c.sources) == 2
        assert c.sources[0].connection == "postgresql://localhost/test"
        assert c.sources[1].path == "openapi.yaml"

    def test_with_policy_overrides(self) -> None:
        c = DriftGuardConfig(
            policy_overrides=[
                PolicyOverride(resource="legacy_*", category="field_removed", severity="warning"),
            ]
        )
        assert len(c.policy_overrides) == 1
        assert c.policy_overrides[0].severity == "warning"


class TestLoadConfig:
    def test_load_valid(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        config_data = {
            "version": "1",
            "snapshot_dir": ".driftguard/snapshots",
            "sources": [
                {"name": "mydb", "type": "postgres", "connection": "postgresql://localhost/mydb"},
                {"name": "api", "type": "openapi", "path": "spec.yaml"},
            ],
            "report_formats": ["terminal", "markdown", "json"],
        }
        path = tmp_path / "driftguard.yaml"
        path.write_text(yaml.dump(config_data), encoding="utf-8")
        config = load_config(path)
        assert len(config.sources) == 2
        assert config.report_formats == ["terminal", "markdown", "json"]

    def test_load_minimal(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        path = tmp_path / "driftguard.yaml"
        path.write_text("version: '1'\n", encoding="utf-8")
        config = load_config(path)
        assert config.version == "1"

    def test_load_empty_file(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        path = tmp_path / "driftguard.yaml"
        path.write_text("", encoding="utf-8")
        config = load_config(path)
        assert config.version == "1"

    def test_load_not_found(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nope.yaml")

    def test_load_invalid_source_type(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        config_data = {"sources": [{"name": "x", "type": "invalid_db"}]}
        path = tmp_path / "driftguard.yaml"
        path.write_text(yaml.dump(config_data), encoding="utf-8")
        with pytest.raises(ValueError):
            load_config(path)


class TestConfigMigration:
    def test_v0_config_migrates_to_v1(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        """A config without schema_version (v0) should migrate cleanly."""
        old_config = {
            "version": "1",
            "sources": [{"name": "api", "type": "openapi", "path": "spec.yaml"}],
        }
        path = tmp_path / "driftguard.yaml"
        path.write_text(yaml.dump(old_config), encoding="utf-8")
        config = load_config(path)
        assert config.schema_version == 1
        assert config.project_name is None
        assert config.environment is None
        assert config.notification.enabled is False


class TestSaveConfig:
    def test_save_and_reload(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        config = DriftGuardConfig(
            sources=[SourceConfig(name="db", type=SourceType.POSTGRES, connection="pg://localhost/test")],
            report_formats=["terminal", "json"],
        )
        path = tmp_path / "driftguard.yaml"
        save_config(config, path)
        loaded = load_config(path)
        assert loaded.sources[0].name == "db"
        assert loaded.report_formats == ["terminal", "json"]

    def test_default_config(self) -> None:
        config = default_config()
        assert len(config.sources) == 1
        assert config.sources[0].type == SourceType.OPENAPI
        assert "markdown" in config.report_formats
