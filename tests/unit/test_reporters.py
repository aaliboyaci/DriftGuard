"""Tests for report generators."""

import json

from driftguard.diff.engine import compute_diff
from driftguard.policy.engine import evaluate
from driftguard.reporters.html import HtmlReporter
from driftguard.reporters.json_reporter import JsonReporter
from driftguard.reporters.markdown import MarkdownReporter
from driftguard.schema.models import (
    ContractSnapshot,
    FieldDef,
    ResourceSchema,
    SourceType,
)


def _make_diff_and_policy():  # type: ignore[no-untyped-def]
    baseline = ContractSnapshot(
        name="v1",
        resources=[
            ResourceSchema(
                name="users",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer"),
                    FieldDef(name="email", field_type="string"),
                    FieldDef(name="age", field_type="integer"),
                ],
            )
        ],
    )
    current = ContractSnapshot(
        name="v2",
        resources=[
            ResourceSchema(
                name="users",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer"),
                    # email removed
                    FieldDef(name="age", field_type="string"),  # type changed
                    FieldDef(name="phone", field_type="string", required=False),  # added optional
                ],
            )
        ],
    )
    diff_result = compute_diff(baseline, current)
    policy_result = evaluate(diff_result)
    return diff_result, policy_result


class TestJsonReporter:
    def test_render(self) -> None:
        diff_result, policy_result = _make_diff_and_policy()
        output = JsonReporter().render(diff_result, policy_result)
        data = json.loads(output)
        assert data["baseline"] == "v1"
        assert data["current"] == "v2"
        assert data["summary"]["total_changes"] == 3
        assert len(data["changes"]) == 3

    def test_contains_severity(self) -> None:
        diff_result, policy_result = _make_diff_and_policy()
        output = JsonReporter().render(diff_result, policy_result)
        data = json.loads(output)
        severities = {c["severity"] for c in data["changes"]}
        assert "breaking" in severities


class TestMarkdownReporter:
    def test_render(self) -> None:
        diff_result, policy_result = _make_diff_and_policy()
        output = MarkdownReporter().render(diff_result, policy_result)
        assert "# Schema Drift Report" in output
        assert "v1" in output
        assert "v2" in output
        assert "BREAKING" in output

    def test_table_rows(self) -> None:
        diff_result, policy_result = _make_diff_and_policy()
        output = MarkdownReporter().render(diff_result, policy_result)
        # Count table data rows (skip header + separator)
        table_lines = [line for line in output.split("\n") if line.startswith("| **")]
        assert len(table_lines) == 3  # 3 changes

    def test_empty_diff(self) -> None:
        snap = ContractSnapshot(
            name="same",
            resources=[
                ResourceSchema(
                    name="t", source_type=SourceType.POSTGRES, fields=[FieldDef(name="id", field_type="integer")]
                )
            ],
        )
        diff_result = compute_diff(snap, snap)
        policy_result = evaluate(diff_result)
        output = MarkdownReporter().render(diff_result, policy_result)
        assert "No schema changes" in output


class TestHtmlReporter:
    def test_render(self) -> None:
        diff_result, policy_result = _make_diff_and_policy()
        output = HtmlReporter().render(diff_result, policy_result)
        assert "<!DOCTYPE html>" in output
        assert "DriftGuard Report" in output
        assert "v1" in output

    def test_contains_rows(self) -> None:
        diff_result, policy_result = _make_diff_and_policy()
        output = HtmlReporter().render(diff_result, policy_result)
        assert output.count("<tr>") >= 3  # at least 3 data rows
