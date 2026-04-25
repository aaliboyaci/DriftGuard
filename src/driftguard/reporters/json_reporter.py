"""JSON reporter for machine-readable output."""

from __future__ import annotations

import json

from driftguard.diff.events import DiffResult
from driftguard.policy.models import PolicyResult


class JsonReporter:
    """Generate JSON report from diff and policy results."""

    def render(self, diff_result: DiffResult, policy_result: PolicyResult) -> str:
        report = {
            "baseline": diff_result.baseline_name,
            "current": diff_result.current_name,
            "summary": {
                "total_changes": diff_result.event_count,
                "breaking": policy_result.breaking_count,
                "warning": policy_result.warning_count,
                "info": policy_result.info_count,
            },
            "changes": [
                {
                    "severity": d.severity.value,
                    "category": d.event.category.value,
                    "resource": d.event.resource_name,
                    "description": d.event.description,
                    "reason": d.reason,
                }
                for d in policy_result.decisions
            ],
        }
        return json.dumps(report, indent=2)
