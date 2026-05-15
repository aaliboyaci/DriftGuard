"""Tests for PR comment reporter."""

from __future__ import annotations

from pathlib import Path

from driftguard.collectors.openapi_extractor import extract_openapi_contract
from driftguard.diff.openapi_engine import compute_openapi_diff
from driftguard.policy.engine import evaluate
from driftguard.reporters.pr_comment import PrCommentReporter

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


def _breaking_result():
    baseline = extract_openapi_contract(FIXTURE_DIR / "openapi_baseline.yaml")
    current = extract_openapi_contract(FIXTURE_DIR / "openapi_breaking_current.yaml")
    diff = compute_openapi_diff(baseline, current)
    policy = evaluate(diff)
    return diff, policy


class TestPrCommentStructure:
    def test_header(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter().render(diff, policy)
        assert "## DriftGuard Schema Drift Report" in output

    def test_verdict_breaking(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter().render(diff, policy)
        assert "breaking change(s) detected" in output
        assert "CI would fail" in output

    def test_summary_line(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter().render(diff, policy)
        assert "Pet Store API 1.0.0" in output
        assert "Pet Store API 2.0.0" in output
        assert "breaking" in output

    def test_breaking_section_expanded(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter().render(diff, policy)
        assert "### Breaking Changes" in output
        assert "Path removed" in output

    def test_warnings_collapsible(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter().render(diff, policy)
        assert "<details><summary>Warnings" in output
        assert "</details>" in output

    def test_info_collapsible(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter().render(diff, policy)
        assert "<details><summary>Info" in output


class TestPrCommentTruncation:
    def test_no_truncation_normal(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter().render(diff, policy)
        assert "truncated" not in output

    def test_truncation_with_low_limit(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter(max_length=200).render(diff, policy)
        assert "truncated" in output.lower()
        assert len(output) <= 200 + 300  # allow for truncation notice

    def test_truncation_preserves_header(self) -> None:
        diff, policy = _breaking_result()
        output = PrCommentReporter(max_length=500).render(diff, policy)
        assert "## DriftGuard" in output


class TestPrCommentSafe:
    def test_no_breaking_verdict(self) -> None:
        baseline = extract_openapi_contract(FIXTURE_DIR / "openapi_baseline.yaml")
        diff = compute_openapi_diff(baseline, baseline)
        policy = evaluate(diff)
        output = PrCommentReporter().render(diff, policy)
        assert "No breaking changes" in output
        assert "CI passes" in output

    def test_no_changes(self) -> None:
        baseline = extract_openapi_contract(FIXTURE_DIR / "openapi_baseline.yaml")
        diff = compute_openapi_diff(baseline, baseline)
        policy = evaluate(diff)
        output = PrCommentReporter().render(diff, policy)
        assert "No schema changes detected" in output


class TestPrCommentCli:
    def test_pr_format(self) -> None:
        from typer.testing import CliRunner

        from driftguard.cli.app import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "openapi",
                "diff",
                str(FIXTURE_DIR / "openapi_baseline.yaml"),
                str(FIXTURE_DIR / "openapi_breaking_current.yaml"),
                "--format",
                "pr",
            ],
        )
        assert result.exit_code == 1
        assert "DriftGuard Schema Drift Report" in result.stdout
        assert "Breaking Changes" in result.stdout
