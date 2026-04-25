"""HTML reporter for standalone drift reports."""

from __future__ import annotations

from driftguard.diff.events import DiffResult
from driftguard.policy.models import PolicyResult, Severity

SEVERITY_COLORS = {
    Severity.BREAKING: "#dc3545",
    Severity.WARNING: "#ffc107",
    Severity.INFO: "#0d6efd",
}


class HtmlReporter:
    """Generate standalone HTML drift report."""

    def render(self, diff_result: DiffResult, policy_result: PolicyResult) -> str:
        rows = ""
        for d in policy_result.decisions:
            color = SEVERITY_COLORS[d.severity]
            rows += f"""        <tr>
          <td><span style="background:{color};color:#fff;padding:2px 8px;border-radius:3px;font-weight:bold">{d.severity.value.upper()}</span></td>
          <td>{d.event.resource_name}</td>
          <td>{d.event.description}</td>
          <td>{d.reason}</td>
        </tr>\n"""

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DriftGuard Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; color: #333; }}
    h1 {{ color: #1a1a2e; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #dee2e6; padding: 0.5rem 0.75rem; text-align: left; }}
    th {{ background: #f8f9fa; font-weight: 600; }}
    .summary {{ display: flex; gap: 2rem; margin: 1rem 0; }}
    .stat {{ padding: 0.5rem 1rem; border-radius: 6px; background: #f8f9fa; }}
    .stat strong {{ font-size: 1.5rem; }}
  </style>
</head>
<body>
  <h1>Schema Drift Report</h1>
  <p><strong>Baseline:</strong> {diff_result.baseline_name} &rarr; <strong>Current:</strong> {diff_result.current_name}</p>
  <div class="summary">
    <div class="stat"><strong>{diff_result.event_count}</strong><br>Total</div>
    <div class="stat" style="border-left:4px solid #dc3545"><strong>{policy_result.breaking_count}</strong><br>Breaking</div>
    <div class="stat" style="border-left:4px solid #ffc107"><strong>{policy_result.warning_count}</strong><br>Warning</div>
    <div class="stat" style="border-left:4px solid #0d6efd"><strong>{policy_result.info_count}</strong><br>Info</div>
  </div>
  <table>
    <thead>
      <tr><th>Severity</th><th>Resource</th><th>Change</th><th>Reason</th></tr>
    </thead>
    <tbody>
{rows}    </tbody>
  </table>
</body>
</html>"""
