"""DriftGuard CLI application.

Provides commands: init, snapshot, diff, check, report.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console

from driftguard import __version__
from driftguard.config.models import (
    DriftGuardConfig,
    default_config,
    load_config,
    save_config,
)
from driftguard.diff.engine import compute_diff
from driftguard.policy.engine import evaluate
from driftguard.schema.models import ContractSnapshot, SourceType
from driftguard.store.local import LocalStore

app = typer.Typer(
    name="driftguard",
    help="Enterprise Data Contract & Schema Drift Monitor",
    no_args_is_help=True,
)
config_app = typer.Typer(name="config", help="Configuration management commands", no_args_is_help=True)
snapshots_app = typer.Typer(name="snapshots", help="Snapshot management commands", no_args_is_help=True)
app.add_typer(config_app)
app.add_typer(snapshots_app)
console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"driftguard {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None, "--version", "-v", help="Show version", callback=_version_callback, is_eager=True
    ),
) -> None:
    """DriftGuard - Catch schema drift before it breaks production."""


@app.command()
def init(
    path: str = typer.Option("driftguard.yaml", "--config", "-c", help="Config file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config"),
) -> None:
    """Initialize DriftGuard configuration in the current directory."""
    config_path = Path(path)
    if config_path.exists() and not force:
        console.print(f"[yellow]Config file already exists: {config_path}[/yellow]")
        console.print("Use --force to overwrite.")
        raise typer.Exit(1)

    config = default_config()
    save_config(config, config_path)
    console.print(f"[green]Created config: {config_path}[/green]")


@app.command()
def snapshot(
    name: str = typer.Option(..., "--name", "-n", help="Snapshot name"),
    config: str = typer.Option("driftguard.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Take a snapshot of current schemas from configured sources."""
    cfg = _load_config(config)
    store = LocalStore(cfg.snapshot_dir)

    resources = []
    for source in cfg.sources:
        collector = _create_collector(source)
        if collector is None:
            console.print(f"[yellow]Skipping unknown source type: {source.type}[/yellow]")
            continue
        try:
            collected = collector.collect()
            resources.extend(collected)
            console.print(f"  [green]Collected {len(collected)} resource(s) from {source.name}[/green]")
        except Exception as e:
            console.print(f"  [red]Error collecting from {source.name}: {e}[/red]")

    snap = ContractSnapshot(
        name=name,
        created_at=datetime.now(UTC),
        resources=resources,
    )
    path = store.save(snap)
    console.print(f"[green]Snapshot saved: {path} ({len(resources)} resources)[/green]")


@app.command()
def diff(
    baseline: str = typer.Option(..., "--baseline", "-b", help="Baseline snapshot name"),
    current: str = typer.Option(..., "--current", "-c", help="Current snapshot name"),
    config: str = typer.Option("driftguard.yaml", "--config", help="Config file path"),
    only_breaking: bool = typer.Option(False, "--only-breaking", help="Show only breaking changes"),
    resource: str = typer.Option("", "--resource", "-r", help="Filter by resource name"),
) -> None:
    """Compare two snapshots and show semantic differences."""
    cfg = _load_config(config)
    store = LocalStore(cfg.snapshot_dir)

    base_snap = _load_snapshot(store, baseline)
    curr_snap = _load_snapshot(store, current)

    diff_result = compute_diff(base_snap, curr_snap)

    # Filter by resource if specified
    if resource:
        diff_result.events = [e for e in diff_result.events if e.resource_name == resource]

    if not diff_result.has_changes:
        console.print("[green]No schema changes detected.[/green]")
        return

    from driftguard.policy.models import Severity
    from driftguard.reporters.terminal import TerminalReporter

    policy_result = evaluate(diff_result)

    # Filter to only breaking if requested
    if only_breaking:
        policy_result.decisions = [d for d in policy_result.decisions if d.severity == Severity.BREAKING]
    reporter = TerminalReporter(console)
    reporter.report(diff_result, policy_result)


@app.command()
def check(
    baseline: str = typer.Option(..., "--baseline", "-b", help="Baseline snapshot name"),
    current: str = typer.Option("", "--current", "-c", help="Current snapshot name (default: latest)"),
    config: str = typer.Option("driftguard.yaml", "--config", help="Config file path"),
) -> None:
    """CI gate: exit non-zero if breaking changes are detected."""
    cfg = _load_config(config)
    store = LocalStore(cfg.snapshot_dir)

    base_snap = _load_snapshot(store, baseline)

    if current:
        curr_snap = _load_snapshot(store, current)
    else:
        # Take a fresh snapshot from sources
        resources = []
        for source in cfg.sources:
            collector = _create_collector(source)
            if collector is not None:
                try:
                    resources.extend(collector.collect())
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
        curr_snap = ContractSnapshot(name="current", resources=resources)

    diff_result = compute_diff(base_snap, curr_snap)
    policy_result = evaluate(diff_result)

    from driftguard.reporters.terminal import TerminalReporter

    reporter = TerminalReporter(console)
    reporter.report(diff_result, policy_result)

    if policy_result.has_breaking:
        console.print(
            f"\n[red bold]BREAKING CHANGES DETECTED: {policy_result.breaking_count} breaking change(s)[/red bold]"
        )
        raise typer.Exit(1)

    console.print("\n[green]No breaking changes. CI check passed.[/green]")


@app.command()
def report(
    baseline: str = typer.Option(..., "--baseline", "-b", help="Baseline snapshot name"),
    current: str = typer.Option(..., "--current", "-c", help="Current snapshot name"),
    format: str = typer.Option("markdown", "--format", "-f", help="Report format: terminal, json, markdown, html"),
    output: str = typer.Option("", "--output", "-o", help="Output file path (stdout if empty)"),
    config: str = typer.Option("driftguard.yaml", "--config", help="Config file path"),
) -> None:
    """Generate a drift report in the specified format."""
    cfg = _load_config(config)
    store = LocalStore(cfg.snapshot_dir)

    base_snap = _load_snapshot(store, baseline)
    curr_snap = _load_snapshot(store, current)

    diff_result = compute_diff(base_snap, curr_snap)
    policy_result = evaluate(diff_result)

    report_content = _generate_report(format, diff_result, policy_result)

    if output:
        Path(output).write_text(report_content, encoding="utf-8")
        console.print(f"[green]Report saved: {output}[/green]")
    else:
        if format == "terminal":
            from driftguard.reporters.terminal import TerminalReporter

            reporter = TerminalReporter(console)
            reporter.report(diff_result, policy_result)
        else:
            console.print(report_content)


@config_app.command("validate")
def config_validate(
    path: str = typer.Option("driftguard.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Validate the DriftGuard configuration file."""
    try:
        cfg = load_config(path)
        console.print(f"[green]Config is valid: {path}[/green]")
        console.print(f"  Schema version: {cfg.schema_version}")
        console.print(f"  Sources: {len(cfg.sources)}")
        console.print(f"  Policy overrides: {len(cfg.policy_overrides)}")
        console.print(f"  Report formats: {', '.join(cfg.report_formats)}")
    except FileNotFoundError:
        console.print(f"[red]Config not found: {path}[/red]")
        raise typer.Exit(1) from None
    except ValueError as e:
        console.print(f"[red]Config validation failed:[/red] {e}")
        raise typer.Exit(1) from None


@config_app.command("print")
def config_print(
    path: str = typer.Option("driftguard.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Print the resolved configuration as YAML."""
    import yaml as _yaml

    cfg = _load_config(path)
    data = cfg.model_dump(mode="json", exclude_none=True)
    output = _yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    console.print(output)


@snapshots_app.command("list")
def snapshots_list(
    config: str = typer.Option("driftguard.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """List all stored snapshots."""
    cfg = _load_config(config)
    store = LocalStore(cfg.snapshot_dir)
    names = store.list_snapshots()
    if not names:
        console.print("[yellow]No snapshots found.[/yellow]")
        return
    console.print(f"[bold]Snapshots ({len(names)}):[/bold]")
    for name in names:
        info = store.snapshot_info(name)
        console.print(f"  {name} — {info['resource_count']} resources, {info['size_bytes']} bytes")


@snapshots_app.command("show")
def snapshots_show(
    name: str = typer.Option(..., "--name", "-n", help="Snapshot name"),
    config: str = typer.Option("driftguard.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Show details of a stored snapshot."""
    cfg = _load_config(config)
    store = LocalStore(cfg.snapshot_dir)
    info = store.snapshot_info(name)
    snap = store.load(name)
    console.print(f"[bold]Snapshot: {name}[/bold]")
    console.print(f"  Created: {info['created_at']}")
    console.print(f"  Resources: {info['resource_count']}")
    console.print(f"  Size: {info['size_bytes']} bytes")
    console.print(f"  Checksum: {info['checksum']}")
    for res in snap.resources:
        console.print(f"  - {res.name} ({len(res.fields)} fields)")


@snapshots_app.command("delete")
def snapshots_delete(
    name: str = typer.Option(..., "--name", "-n", help="Snapshot name"),
    config: str = typer.Option("driftguard.yaml", "--config", "-c", help="Config file path"),
) -> None:
    """Delete a stored snapshot."""
    cfg = _load_config(config)
    store = LocalStore(cfg.snapshot_dir)
    if store.delete(name):
        console.print(f"[green]Deleted snapshot: {name}[/green]")
    else:
        console.print(f"[red]Snapshot not found: {name}[/red]")
        raise typer.Exit(1)


def _load_config(path: str) -> DriftGuardConfig:
    try:
        return load_config(path)
    except FileNotFoundError:
        console.print(f"[red]Config not found: {path}[/red]")
        console.print("Run 'driftguard init' to create one.")
        raise typer.Exit(1) from None


def _load_snapshot(store: LocalStore, name: str) -> ContractSnapshot:
    try:
        return store.load(name)
    except FileNotFoundError:
        console.print(f"[red]Snapshot not found: {name}[/red]")
        raise typer.Exit(1) from None


def _create_collector(source: SourceConfig) -> BaseCollector | None:  # type: ignore[name-defined]  # noqa: F821
    from driftguard.collectors import (
        CsvCollector,
        JsonSchemaCollector,
        MysqlCollector,
        OpenApiCollector,
        PostgresCollector,
        SqliteCollector,
    )
    from driftguard.config.models import SourceConfig

    assert isinstance(source, SourceConfig)
    match source.type:
        case SourceType.POSTGRES:
            if source.connection is None:
                return None
            return PostgresCollector(source.connection, source.options.get("schema", "public"))
        case SourceType.MYSQL:
            if source.connection is None:
                return None
            return MysqlCollector(source.connection, source.options.get("schema", ""))
        case SourceType.SQLITE:
            if source.path is None:
                return None
            return SqliteCollector(source.path)
        case SourceType.OPENAPI:
            if source.path is None:
                return None
            return OpenApiCollector(source.path)
        case SourceType.JSON_SCHEMA:
            if source.path is None:
                return None
            return JsonSchemaCollector(source.path, source.name)
        case SourceType.JSON_PAYLOAD:
            if source.path is None:
                return None
            return JsonSchemaCollector(source.path, source.name)
        case SourceType.CSV | SourceType.PARQUET:
            if source.path is None:
                return None
            return CsvCollector(source.path, source.name)
        case _:
            return None


def _generate_report(format: str, diff_result: DiffResult, policy_result: PolicyResult) -> str:  # type: ignore[name-defined]  # noqa: F821
    from driftguard.diff.events import DiffResult as _DiffResult
    from driftguard.policy.models import PolicyResult as _PolicyResult
    from driftguard.reporters.html import HtmlReporter
    from driftguard.reporters.json_reporter import JsonReporter
    from driftguard.reporters.markdown import MarkdownReporter

    assert isinstance(diff_result, _DiffResult)
    assert isinstance(policy_result, _PolicyResult)

    match format:
        case "json":
            return JsonReporter().render(diff_result, policy_result)
        case "markdown" | "md":
            return MarkdownReporter().render(diff_result, policy_result)
        case "html":
            return HtmlReporter().render(diff_result, policy_result)
        case _:
            return MarkdownReporter().render(diff_result, policy_result)
