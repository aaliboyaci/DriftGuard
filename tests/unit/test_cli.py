"""Tests for CLI commands."""

from pathlib import Path

from typer.testing import CliRunner

from driftguard.cli.app import app
from driftguard.config.models import DriftGuardConfig, save_config
from driftguard.schema.models import (
    ContractSnapshot,
    FieldDef,
    ResourceSchema,
    SourceType,
)
from driftguard.store.local import LocalStore

runner = CliRunner()


class TestInitCommand:
    def test_init_creates_config(self, tmp_path: Path) -> None:
        config_path = tmp_path / "driftguard.yaml"
        result = runner.invoke(app, ["init", "--config", str(config_path)])
        assert result.exit_code == 0
        assert config_path.exists()
        assert "Created config" in result.stdout

    def test_init_refuses_overwrite(self, tmp_path: Path) -> None:
        config_path = tmp_path / "driftguard.yaml"
        config_path.write_text("version: '1'", encoding="utf-8")
        result = runner.invoke(app, ["init", "--config", str(config_path)])
        assert result.exit_code == 1
        assert "already exists" in result.stdout

    def test_init_force_overwrites(self, tmp_path: Path) -> None:
        config_path = tmp_path / "driftguard.yaml"
        config_path.write_text("old content", encoding="utf-8")
        result = runner.invoke(app, ["init", "--config", str(config_path), "--force"])
        assert result.exit_code == 0


class TestVersionFlag:
    def test_version(self) -> None:
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "driftguard" in result.stdout


class TestDiffCommand:
    def _setup_snapshots(self, tmp_path: Path) -> Path:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)

        baseline = ContractSnapshot(
            name="baseline",
            resources=[
                ResourceSchema(
                    name="users",
                    source_type=SourceType.POSTGRES,
                    fields=[
                        FieldDef(name="id", field_type="integer"),
                        FieldDef(name="email", field_type="string"),
                    ],
                )
            ],
        )
        current = ContractSnapshot(
            name="current",
            resources=[
                ResourceSchema(
                    name="users",
                    source_type=SourceType.POSTGRES,
                    fields=[
                        FieldDef(name="id", field_type="integer"),
                        # email removed
                    ],
                )
            ],
        )
        store.save(baseline)
        store.save(current)

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        return config_path

    def test_diff_shows_changes(self, tmp_path: Path) -> None:
        config_path = self._setup_snapshots(tmp_path)
        result = runner.invoke(
            app,
            [
                "diff",
                "--baseline",
                "baseline",
                "--current",
                "current",
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        assert "email" in result.stdout

    def test_diff_no_changes(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)
        snap = ContractSnapshot(
            name="v1",
            resources=[
                ResourceSchema(
                    name="t", source_type=SourceType.POSTGRES, fields=[FieldDef(name="id", field_type="integer")]
                )
            ],
        )
        store.save(snap)
        # Save same as "v2"
        snap2 = snap.model_copy(update={"name": "v2"})
        store.save(snap2)

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)

        result = runner.invoke(
            app,
            [
                "diff",
                "--baseline",
                "v1",
                "--current",
                "v2",
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        assert "No schema changes" in result.stdout


class TestCheckCommand:
    def test_check_fails_on_breaking(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)

        baseline = ContractSnapshot(
            name="baseline",
            resources=[
                ResourceSchema(
                    name="users",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer"), FieldDef(name="email", field_type="string")],
                )
            ],
        )
        current = ContractSnapshot(
            name="current",
            resources=[
                ResourceSchema(
                    name="users",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer")],
                )
            ],
        )
        store.save(baseline)
        store.save(current)

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)

        result = runner.invoke(
            app,
            [
                "check",
                "--baseline",
                "baseline",
                "--current",
                "current",
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code == 1
        assert "BREAKING" in result.stdout

    def test_check_passes_no_breaking(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)

        snap = ContractSnapshot(
            name="v1",
            resources=[
                ResourceSchema(
                    name="t", source_type=SourceType.POSTGRES, fields=[FieldDef(name="id", field_type="integer")]
                )
            ],
        )
        store.save(snap)
        snap2 = snap.model_copy(update={"name": "v2"})
        store.save(snap2)

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)

        result = runner.invoke(
            app,
            [
                "check",
                "--baseline",
                "v1",
                "--current",
                "v2",
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        assert "passed" in result.stdout.lower() or "No schema changes" in result.stdout


class TestReportCommand:
    def _setup(self, tmp_path: Path) -> Path:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)

        baseline = ContractSnapshot(
            name="baseline",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[
                        FieldDef(name="id", field_type="integer"),
                        FieldDef(name="email", field_type="string"),
                    ],
                )
            ],
        )
        current = ContractSnapshot(
            name="current",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[
                        FieldDef(name="id", field_type="integer"),
                    ],
                )
            ],
        )
        store.save(baseline)
        store.save(current)

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        return config_path

    def test_report_markdown_to_file(self, tmp_path: Path) -> None:
        config_path = self._setup(tmp_path)
        output = tmp_path / "report.md"
        result = runner.invoke(
            app,
            [
                "report",
                "--baseline",
                "baseline",
                "--current",
                "current",
                "--format",
                "markdown",
                "--output",
                str(output),
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        content = output.read_text(encoding="utf-8")
        assert "Schema Drift Report" in content
        assert "BREAKING" in content

    def test_report_json_to_file(self, tmp_path: Path) -> None:
        config_path = self._setup(tmp_path)
        output = tmp_path / "report.json"
        result = runner.invoke(
            app,
            [
                "report",
                "--baseline",
                "baseline",
                "--current",
                "current",
                "--format",
                "json",
                "--output",
                str(output),
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        import json

        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["summary"]["breaking"] == 1

    def test_report_html_to_file(self, tmp_path: Path) -> None:
        config_path = self._setup(tmp_path)
        output = tmp_path / "report.html"
        result = runner.invoke(
            app,
            [
                "report",
                "--baseline",
                "baseline",
                "--current",
                "current",
                "--format",
                "html",
                "--output",
                str(output),
                "--config",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        content = output.read_text(encoding="utf-8")
        assert "<html" in content
        assert "DriftGuard Report" in content
