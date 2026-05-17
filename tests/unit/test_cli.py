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


class TestDemoCommand:
    def test_demo_default_terminal(self) -> None:
        result = runner.invoke(app, ["demo"])
        assert result.exit_code == 0
        assert "DriftGuard Demo" in result.stdout
        assert "BREAKING CHANGES DETECTED" in result.stdout
        assert "CI check would fail" in result.stdout
        assert "Summary:" in result.stdout

    def test_demo_format_json(self) -> None:
        result = runner.invoke(app, ["demo", "--format", "json"])
        assert result.exit_code == 0
        assert '"breaking": 2' in result.stdout
        assert '"total_changes": 5' in result.stdout
        assert '"severity"' in result.stdout

    def test_demo_format_markdown(self) -> None:
        result = runner.invoke(app, ["demo", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Schema Drift Report" in result.stdout
        assert "BREAKING" in result.stdout

    def test_demo_format_html(self) -> None:
        result = runner.invoke(app, ["demo", "--format", "html"])
        assert result.exit_code == 0
        assert "<html" in result.stdout
        assert "DriftGuard Report" in result.stdout

    def test_demo_output_to_file(self, tmp_path: Path) -> None:
        output = tmp_path / "demo.html"
        result = runner.invoke(app, ["demo", "--format", "html", "--output", str(output)])
        assert result.exit_code == 0
        assert "Report saved" in result.stdout
        content = output.read_text(encoding="utf-8")
        assert "<html" in content

    def test_demo_summary_counts(self) -> None:
        result = runner.invoke(app, ["demo"])
        assert result.exit_code == 0
        assert "2 breaking" in result.stdout
        assert "2 warning" in result.stdout
        assert "1 info" in result.stdout


class TestCLIEdgeCases:
    def test_diff_missing_config(self) -> None:
        result = runner.invoke(app, ["diff", "-b", "a", "-c", "b", "--config", "/nonexistent.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "Config" in result.stdout

    def test_check_missing_config(self) -> None:
        result = runner.invoke(app, ["check", "-b", "a", "--config", "/nonexistent.yaml"])
        assert result.exit_code == 1

    def test_report_missing_config(self) -> None:
        result = runner.invoke(app, ["report", "-b", "a", "-c", "b", "--config", "/nonexistent.yaml"])
        assert result.exit_code == 1

    def test_diff_missing_snapshot(self, tmp_path: Path) -> None:
        config = DriftGuardConfig(snapshot_dir=str(tmp_path / "snaps"))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        result = runner.invoke(app, ["diff", "-b", "missing", "-c", "also-missing", "--config", str(config_path)])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_snapshots_list_empty(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snaps"
        snap_dir.mkdir()
        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        result = runner.invoke(app, ["snapshots", "list", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "No snapshots" in result.stdout

    def test_snapshots_delete_missing(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snaps"
        snap_dir.mkdir()
        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        result = runner.invoke(app, ["snapshots", "delete", "-n", "nonexistent", "--config", str(config_path)])
        assert result.exit_code == 1

    def test_config_validate_missing(self) -> None:
        result = runner.invoke(app, ["config", "validate", "--config", "/nonexistent.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_config_validate_valid(self, tmp_path: Path) -> None:
        config = DriftGuardConfig()
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        result = runner.invoke(app, ["config", "validate", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    def test_report_terminal_format(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snaps"
        store = LocalStore(snap_dir)
        base = ContractSnapshot(
            name="b",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer"), FieldDef(name="x", field_type="string")],
                )
            ],
        )
        curr = ContractSnapshot(
            name="c",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer")],
                )
            ],
        )
        store.save(base)
        store.save(curr)
        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        result = runner.invoke(app, ["report", "-b", "b", "-c", "c", "-f", "terminal", "--config", str(config_path)])
        assert result.exit_code == 0


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


class TestOpenApiDiffCommand:
    def test_openapi_diff_terminal(self) -> None:
        result = runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(FIXTURE_DIR / "openapi_baseline.yaml"),
                str(FIXTURE_DIR / "openapi_breaking_current.yaml"),
            ],
        )
        assert result.exit_code == 1  # has breaking changes
        assert "BREAKING CHANGES DETECTED" in result.stdout
        assert "Path removed" in result.stdout

    def test_openapi_diff_json(self) -> None:
        result = runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(FIXTURE_DIR / "openapi_baseline.yaml"),
                str(FIXTURE_DIR / "openapi_breaking_current.yaml"),
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 1
        assert '"openapi_path_removed"' in result.stdout

    def test_openapi_diff_markdown(self) -> None:
        result = runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(FIXTURE_DIR / "openapi_baseline.yaml"),
                str(FIXTURE_DIR / "openapi_breaking_current.yaml"),
                "--format",
                "markdown",
            ],
        )
        assert result.exit_code == 1
        assert "# Schema Drift Report" in result.stdout
        assert "BREAKING" in result.stdout

    def test_openapi_diff_output_to_file(self, tmp_path: Path) -> None:
        output = tmp_path / "report.md"
        result = runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(FIXTURE_DIR / "openapi_baseline.yaml"),
                str(FIXTURE_DIR / "openapi_breaking_current.yaml"),
                "--format",
                "markdown",
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 1
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "BREAKING" in content

    def test_openapi_diff_only_breaking(self) -> None:
        result = runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(FIXTURE_DIR / "openapi_baseline.yaml"),
                str(FIXTURE_DIR / "openapi_breaking_current.yaml"),
                "--only-breaking",
            ],
        )
        assert result.exit_code == 1
        assert "BREAKING" in result.stdout

    def test_openapi_diff_missing_baseline(self) -> None:
        result = runner.invoke(app, ["openapi", "diff", "/nonexistent.yaml", "whatever.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    def test_openapi_diff_identical_specs(self) -> None:
        spec = str(FIXTURE_DIR / "openapi_baseline.yaml")
        result = runner.invoke(app, ["openapi", "diff", spec, spec])
        assert result.exit_code == 0
        assert "safe" in result.stdout.lower() or "No breaking" in result.stdout


class TestSnapshotsExportCommand:
    def _setup(self, tmp_path: Path) -> tuple[Path, str]:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)
        snap = ContractSnapshot(
            name="test-snap",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer")],
                )
            ],
        )
        store.save(snap)
        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        return config_path, "test-snap"

    def test_export_json(self, tmp_path: Path) -> None:
        config_path, name = self._setup(tmp_path)
        output = tmp_path / "exported.json"
        result = runner.invoke(
            app, ["snapshots", "export", "-n", name, "-o", str(output), "--config", str(config_path)]
        )
        assert result.exit_code == 0
        assert "Exported" in result.stdout
        assert output.exists()
        import json

        data = json.loads(output.read_text(encoding="utf-8"))
        assert data["name"] == "test-snap"

    def test_export_compressed(self, tmp_path: Path) -> None:
        config_path, name = self._setup(tmp_path)
        output = tmp_path / "exported.json.gz"
        result = runner.invoke(
            app, ["snapshots", "export", "-n", name, "-o", str(output), "--compress", "--config", str(config_path)]
        )
        assert result.exit_code == 0
        assert output.exists()
        import gzip

        content = gzip.decompress(output.read_bytes())
        assert b"test-snap" in content

    def test_export_missing_snapshot(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snapshots"
        snap_dir.mkdir()
        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        result = runner.invoke(
            app, ["snapshots", "export", "-n", "nonexistent", "-o", str(tmp_path / "out.json"), "--config", str(config_path)]
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestSnapshotsImportCommand:
    def test_import_json(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)
        # Create and export a snapshot manually
        snap = ContractSnapshot(
            name="imported",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer")],
                )
            ],
        )
        export_file = tmp_path / "snap.json"
        export_file.write_text(snap.model_dump_json(indent=2), encoding="utf-8")

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)

        result = runner.invoke(app, ["snapshots", "import", str(export_file), "--config", str(config_path)])
        assert result.exit_code == 0
        assert "Imported" in result.stdout
        assert "imported" in result.stdout
        # Verify actually saved
        assert store.exists("imported")

    def test_import_compressed(self, tmp_path: Path) -> None:
        import gzip

        snap_dir = tmp_path / "snapshots"
        snap = ContractSnapshot(
            name="gz-snap",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer")],
                )
            ],
        )
        gz_file = tmp_path / "snap.json.gz"
        gz_file.write_bytes(gzip.compress(snap.model_dump_json().encode("utf-8")))

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)

        result = runner.invoke(app, ["snapshots", "import", str(gz_file), "--config", str(config_path)])
        assert result.exit_code == 0
        assert "gz-snap" in result.stdout

    def test_import_missing_file(self, tmp_path: Path) -> None:
        config = DriftGuardConfig(snapshot_dir=str(tmp_path / "snaps"))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)
        result = runner.invoke(app, ["snapshots", "import", "/nonexistent.json", "--config", str(config_path)])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestSnapshotsCleanupCommand:
    def test_cleanup_removes_old(self, tmp_path: Path) -> None:
        import time

        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)
        # Create 4 snapshots with slight time gaps
        for i in range(4):
            snap = ContractSnapshot(
                name=f"snap-{i}",
                resources=[
                    ResourceSchema(
                        name="t",
                        source_type=SourceType.POSTGRES,
                        fields=[FieldDef(name="id", field_type="integer")],
                    )
                ],
            )
            store.save(snap)
            time.sleep(0.05)

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)

        result = runner.invoke(app, ["snapshots", "cleanup", "--keep", "2", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "Removed 2" in result.stdout
        # Only 2 remain
        assert len(store.list_snapshots()) == 2

    def test_cleanup_nothing_to_remove(self, tmp_path: Path) -> None:
        snap_dir = tmp_path / "snapshots"
        store = LocalStore(snap_dir)
        snap = ContractSnapshot(
            name="only-one",
            resources=[
                ResourceSchema(
                    name="t",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer")],
                )
            ],
        )
        store.save(snap)

        config = DriftGuardConfig(snapshot_dir=str(snap_dir))
        config_path = tmp_path / "driftguard.yaml"
        save_config(config, config_path)

        result = runner.invoke(app, ["snapshots", "cleanup", "--keep", "5", "--config", str(config_path)])
        assert result.exit_code == 0
        assert "No snapshots to remove" in result.stdout
