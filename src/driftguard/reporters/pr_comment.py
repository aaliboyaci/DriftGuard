"""GitHub PR comment reporter.

Generates compact Markdown optimized for PR comments with:
- Breaking changes summary at top
- Collapsible warning/info sections
- Max length truncation
- GitHub Actions step summary compatible
"""

from __future__ import annotations

from driftguard.diff.events import DiffResult
from driftguard.policy.models import PolicyResult, Severity

# GitHub PR comment body limit is ~65536 chars. Leave margin.
DEFAULT_MAX_LENGTH = 60000


class PrCommentReporter:
    """Generate compact Markdown for GitHub PR comments."""

    def __init__(self, max_length: int = DEFAULT_MAX_LENGTH) -> None:
        self._max_length = max_length

    def render(self, diff_result: DiffResult, policy_result: PolicyResult) -> str:
        lines: list[str] = []

        # Header
        lines.append("## DriftGuard Schema Drift Report")
        lines.append("")

        # Verdict badge
        if policy_result.has_breaking:
            lines.append(f"> **{policy_result.breaking_count} breaking change(s) detected** — CI would fail")
        else:
            lines.append("> No breaking changes — CI passes")
        lines.append("")

        # Summary line
        lines.append(
            f"**{diff_result.baseline_name}** → **{diff_result.current_name}** | "
            f"{diff_result.event_count} changes: "
            f"{policy_result.breaking_count} breaking, "
            f"{policy_result.warning_count} warning, "
            f"{policy_result.info_count} info"
        )
        lines.append("")

        if not policy_result.decisions:
            lines.append("No schema changes detected.")
            return "\n".join(lines)

        # Breaking changes section (always expanded)
        breaking = [d for d in policy_result.decisions if d.severity == Severity.BREAKING]
        if breaking:
            lines.append("### Breaking Changes")
            lines.append("")
            lines.append("| Resource | Change | Reason |")
            lines.append("|----------|--------|--------|")
            for d in breaking:
                lines.append(f"| {d.event.resource_name} | {d.event.description} | {d.reason} |")
            lines.append("")

        # Warnings (collapsible)
        warnings = [d for d in policy_result.decisions if d.severity == Severity.WARNING]
        if warnings:
            lines.append(f"<details><summary>Warnings ({len(warnings)})</summary>")
            lines.append("")
            lines.append("| Resource | Change | Reason |")
            lines.append("|----------|--------|--------|")
            for d in warnings:
                lines.append(f"| {d.event.resource_name} | {d.event.description} | {d.reason} |")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        # Info (collapsible)
        infos = [d for d in policy_result.decisions if d.severity == Severity.INFO]
        if infos:
            lines.append(f"<details><summary>Info ({len(infos)})</summary>")
            lines.append("")
            lines.append("| Resource | Change | Reason |")
            lines.append("|----------|--------|--------|")
            for d in infos:
                lines.append(f"| {d.event.resource_name} | {d.event.description} | {d.reason} |")
            lines.append("")
            lines.append("</details>")
            lines.append("")

        result = "\n".join(lines)

        # Truncation
        if len(result) > self._max_length:
            result = self._truncate(result, policy_result)

        return result

    def _truncate(self, content: str, policy_result: PolicyResult) -> str:
        """Truncate content and append a notice."""
        truncation_notice = (
            "\n\n---\n"
            f"*Report truncated ({len(content)} chars). "
            f"Full report: {policy_result.breaking_count} breaking, "
            f"{policy_result.warning_count} warning, "
            f"{policy_result.info_count} info changes. "
            "Run `driftguard report -f markdown` locally for full output.*\n"
        )
        max_content = self._max_length - len(truncation_notice)
        return content[:max_content] + truncation_notice
