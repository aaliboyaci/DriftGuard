"""Markdown reporter for CI artifacts and PR comments."""

from __future__ import annotations

from driftguard.diff.events import DiffResult
from driftguard.policy.models import PolicyResult, Severity

SEVERITY_EMOJI = {
    Severity.BREAKING: "BREAKING",
    Severity.WARNING: "WARNING",
    Severity.INFO: "INFO",
}


class MarkdownReporter:
    """Generate Markdown drift report."""

    def render(self, diff_result: DiffResult, policy_result: PolicyResult) -> str:
        lines: list[str] = []
        lines.append("# Schema Drift Report")
        lines.append("")
        lines.append(f"**Baseline:** {diff_result.baseline_name}  ")
        lines.append(f"**Current:** {diff_result.current_name}  ")
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"| Metric | Count |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total changes | {diff_result.event_count} |")
        lines.append(f"| Breaking | {policy_result.breaking_count} |")
        lines.append(f"| Warning | {policy_result.warning_count} |")
        lines.append(f"| Info | {policy_result.info_count} |")
        lines.append("")

        if not policy_result.decisions:
            lines.append("No schema changes detected.")
            return "\n".join(lines)

        lines.append("## Changes")
        lines.append("")
        lines.append("| Severity | Resource | Change | Reason |")
        lines.append("|----------|----------|--------|--------|")

        for d in policy_result.decisions:
            sev = SEVERITY_EMOJI[d.severity]
            lines.append(f"| **{sev}** | {d.event.resource_name} | {d.event.description} | {d.reason} |")

        lines.append("")
        return "\n".join(lines)
