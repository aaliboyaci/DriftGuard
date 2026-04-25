"""Terminal reporter using Rich."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from driftguard.diff.events import DiffResult
from driftguard.policy.models import PolicyResult, Severity

SEVERITY_COLORS = {
    Severity.BREAKING: "red bold",
    Severity.WARNING: "yellow",
    Severity.INFO: "blue",
}

SEVERITY_ICONS = {
    Severity.BREAKING: "X",
    Severity.WARNING: "!",
    Severity.INFO: "i",
}


class TerminalReporter:
    """Rich-based terminal output for drift reports."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def report(self, diff_result: DiffResult, policy_result: PolicyResult) -> None:
        if not diff_result.has_changes:
            self.console.print("[green]No schema changes detected.[/green]")
            return

        self.console.print(
            f"\n[bold]Schema Drift Report[/bold]: {diff_result.baseline_name} -> {diff_result.current_name}"
        )
        self.console.print(
            f"Changes: {diff_result.event_count} | Breaking: {policy_result.breaking_count} | Warnings: {policy_result.warning_count} | Info: {policy_result.info_count}\n"
        )

        table = Table(show_header=True, header_style="bold")
        table.add_column("Severity", width=10)
        table.add_column("Resource", width=20)
        table.add_column("Change", min_width=30)
        table.add_column("Reason", min_width=30)

        for decision in policy_result.decisions:
            severity = decision.severity
            color = SEVERITY_COLORS[severity]
            icon = SEVERITY_ICONS[severity]
            table.add_row(
                f"[{color}][{icon}] {severity.value.upper()}[/{color}]",
                decision.event.resource_name,
                decision.event.description,
                decision.reason,
            )

        self.console.print(table)
