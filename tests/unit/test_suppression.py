"""Tests for the suppression/waiver system."""

from __future__ import annotations

from pathlib import Path

import pytest

from driftguard.diff.events import ChangeCategory, DiffEvent
from driftguard.policy.models import PolicyDecision, Severity
from driftguard.policy.suppression import SuppressionFile, SuppressionRule


@pytest.fixture
def sample_suppression_path() -> Path:
    return Path(__file__).parent.parent / "fixtures" / "sample_driftguardignore.yaml"


@pytest.fixture
def breaking_field_removed() -> PolicyDecision:
    return PolicyDecision(
        event=DiffEvent(
            category=ChangeCategory.FIELD_REMOVED,
            resource_name="legacy_users",
            description="Field 'email' removed from legacy_users",
        ),
        severity=Severity.BREAKING,
        reason="Consumers expecting this field will fail",
    )


@pytest.fixture
def breaking_type_changed() -> PolicyDecision:
    return PolicyDecision(
        event=DiffEvent(
            category=ChangeCategory.TYPE_CHANGED,
            resource_name="orders",
            description="Field 'metadata.tags' type changed from array to string",
        ),
        severity=Severity.BREAKING,
        reason="Type changed",
    )


@pytest.fixture
def warning_nullable() -> PolicyDecision:
    return PolicyDecision(
        event=DiffEvent(
            category=ChangeCategory.NULLABLE_CHANGED,
            resource_name="users",
            description="Field 'phone' nullable changed from false to true",
        ),
        severity=Severity.WARNING,
        reason="Field became nullable",
    )


@pytest.fixture
def breaking_temp_table() -> PolicyDecision:
    return PolicyDecision(
        event=DiffEvent(
            category=ChangeCategory.FIELD_REMOVED,
            resource_name="temp_analytics",
            description="Field 'session_id' removed from temp_analytics",
        ),
        severity=Severity.BREAKING,
        reason="Consumers expecting this field will fail",
    )


class TestSuppressionRuleMatching:
    """Test individual rule matching logic."""

    def test_resource_pattern_match(self, breaking_field_removed: PolicyDecision) -> None:
        rule = SuppressionRule(
            resource="legacy_*",
            severity_override="warning",
            reason="Legacy tables deprecated",
            owner="team",
        )
        assert rule.matches(breaking_field_removed) is True

    def test_resource_pattern_no_match(self, breaking_type_changed: PolicyDecision) -> None:
        rule = SuppressionRule(
            resource="legacy_*",
            severity_override="warning",
            reason="Legacy tables deprecated",
            owner="team",
        )
        assert rule.matches(breaking_type_changed) is False

    def test_path_pattern_match(self, breaking_type_changed: PolicyDecision) -> None:
        rule = SuppressionRule(
            path="metadata.*",
            severity_override="info",
            reason="Metadata fields are internal",
            owner="team",
        )
        assert rule.matches(breaking_type_changed) is True

    def test_path_pattern_no_match(self, breaking_field_removed: PolicyDecision) -> None:
        rule = SuppressionRule(
            path="metadata.*",
            severity_override="info",
            reason="Metadata fields are internal",
            owner="team",
        )
        assert rule.matches(breaking_field_removed) is False

    def test_category_match(self, breaking_field_removed: PolicyDecision) -> None:
        rule = SuppressionRule(
            category="field_removed",
            severity_override="warning",
            reason="Known removal",
            owner="team",
        )
        assert rule.matches(breaking_field_removed) is True

    def test_category_no_match(self, breaking_type_changed: PolicyDecision) -> None:
        rule = SuppressionRule(
            category="field_removed",
            severity_override="warning",
            reason="Known removal",
            owner="team",
        )
        assert rule.matches(breaking_type_changed) is False

    def test_multiple_criteria_all_must_match(self, breaking_field_removed: PolicyDecision) -> None:
        """Multiple criteria use AND logic: all must match."""
        rule = SuppressionRule(
            resource="legacy_*",
            category="field_removed",
            severity_override="warning",
            reason="Known",
            owner="team",
        )
        assert rule.matches(breaking_field_removed) is True

    def test_multiple_criteria_partial_match_fails(self, breaking_field_removed: PolicyDecision) -> None:
        """If resource matches but category doesn't, rule doesn't apply."""
        rule = SuppressionRule(
            resource="legacy_*",
            category="type_changed",
            severity_override="warning",
            reason="Known",
            owner="team",
        )
        assert rule.matches(breaking_field_removed) is False

    def test_expired_rule_does_not_match(self, breaking_field_removed: PolicyDecision) -> None:
        rule = SuppressionRule(
            resource="legacy_*",
            severity_override="warning",
            reason="Expired rule",
            owner="team",
            expires_at="2020-01-01",
        )
        assert rule.matches(breaking_field_removed) is False


class TestSuppressionFileLoad:
    """Test loading suppression files from YAML."""

    def test_load_sample_file(self, sample_suppression_path: Path) -> None:
        sf = SuppressionFile.load(sample_suppression_path)
        assert len(sf.rules) == 4

    def test_load_first_rule_attributes(self, sample_suppression_path: Path) -> None:
        sf = SuppressionFile.load(sample_suppression_path)
        rule = sf.rules[0]
        assert rule.resource == "legacy_*"
        assert rule.category == "field_removed"
        assert rule.severity_override == "warning"
        assert rule.reason == "Legacy table being deprecated Q3"
        assert rule.owner == "platform-team"
        assert rule.expires_at == "2026-09-01"

    def test_load_empty_file(self, tmp_path: Path) -> None:
        empty_file = tmp_path / ".driftguardignore"
        empty_file.write_text("")
        sf = SuppressionFile.load(empty_file)
        assert len(sf.rules) == 0

    def test_load_file_no_suppressions_key(self, tmp_path: Path) -> None:
        f = tmp_path / ".driftguardignore"
        f.write_text("other_key: value\n")
        sf = SuppressionFile.load(f)
        assert len(sf.rules) == 0


class TestSuppressionFileApply:
    """Test applying suppressions to policy decisions."""

    def test_severity_demotion(self, breaking_field_removed: PolicyDecision) -> None:
        sf = SuppressionFile(
            rules=[
                SuppressionRule(
                    resource="legacy_*",
                    category="field_removed",
                    severity_override="warning",
                    reason="Legacy deprecated",
                    owner="team",
                )
            ]
        )
        result = sf.apply([breaking_field_removed])
        assert len(result) == 1
        assert result[0].severity == Severity.WARNING
        assert result[0].override is True
        assert "[suppressed]" in result[0].reason

    def test_severity_ignore_removes_decision(self, breaking_temp_table: PolicyDecision) -> None:
        sf = SuppressionFile(
            rules=[
                SuppressionRule(
                    resource="temp_*",
                    severity_override="ignore",
                    reason="Temporary tables",
                    owner="team",
                )
            ]
        )
        result = sf.apply([breaking_temp_table])
        assert len(result) == 0

    def test_no_match_no_change(self, breaking_type_changed: PolicyDecision) -> None:
        sf = SuppressionFile(
            rules=[
                SuppressionRule(
                    resource="legacy_*",
                    severity_override="warning",
                    reason="Legacy",
                    owner="team",
                )
            ]
        )
        result = sf.apply([breaking_type_changed])
        assert len(result) == 1
        assert result[0].severity == Severity.BREAKING
        assert result[0].override is False

    def test_multiple_decisions_selective_suppression(
        self,
        breaking_field_removed: PolicyDecision,
        breaking_type_changed: PolicyDecision,
    ) -> None:
        sf = SuppressionFile(
            rules=[
                SuppressionRule(
                    resource="legacy_*",
                    severity_override="warning",
                    reason="Legacy deprecated",
                    owner="team",
                )
            ]
        )
        result = sf.apply([breaking_field_removed, breaking_type_changed])
        assert len(result) == 2
        assert result[0].severity == Severity.WARNING  # matched
        assert result[1].severity == Severity.BREAKING  # not matched

    def test_apply_with_resource_and_category(self, warning_nullable: PolicyDecision) -> None:
        sf = SuppressionFile(
            rules=[
                SuppressionRule(
                    resource="users",
                    category="nullable_changed",
                    severity_override="info",
                    reason="Users nullable safe",
                    owner="team",
                )
            ]
        )
        result = sf.apply([warning_nullable])
        assert len(result) == 1
        assert result[0].severity == Severity.INFO


class TestSuppressionExpiry:
    """Test expiry date handling."""

    def test_expired_rules_detection(self) -> None:
        sf = SuppressionFile(
            rules=[
                SuppressionRule(
                    resource="old_*",
                    severity_override="warning",
                    reason="Old",
                    owner="team",
                    expires_at="2020-01-01",
                ),
                SuppressionRule(
                    resource="new_*",
                    severity_override="warning",
                    reason="New",
                    owner="team",
                    expires_at="2099-12-31",
                ),
            ]
        )
        expired = sf.expired_rules()
        assert len(expired) == 1
        assert expired[0].resource == "old_*"

    def test_no_expiry_never_expires(self) -> None:
        rule = SuppressionRule(
            resource="any_*",
            severity_override="warning",
            reason="No expiry",
            owner="team",
            expires_at=None,
        )
        assert rule.is_expired() is False

    def test_future_expiry_not_expired(self) -> None:
        rule = SuppressionRule(
            resource="any_*",
            severity_override="warning",
            reason="Future",
            owner="team",
            expires_at="2099-12-31",
        )
        assert rule.is_expired() is False


class TestSuppressionValidation:
    """Test validation of suppression rules."""

    def test_missing_reason(self) -> None:
        rule = SuppressionRule(
            resource="legacy_*",
            severity_override="warning",
            reason="",
            owner="team",
        )
        errors = rule.validate()
        assert any("reason" in e for e in errors)

    def test_missing_owner(self) -> None:
        rule = SuppressionRule(
            resource="legacy_*",
            severity_override="warning",
            reason="Valid reason",
            owner="",
        )
        errors = rule.validate()
        assert any("owner" in e for e in errors)

    def test_invalid_severity_override(self) -> None:
        rule = SuppressionRule(
            resource="legacy_*",
            severity_override="critical",
            reason="Valid",
            owner="team",
        )
        errors = rule.validate()
        assert any("severity_override" in e for e in errors)

    def test_valid_rule_no_errors(self) -> None:
        rule = SuppressionRule(
            resource="legacy_*",
            severity_override="warning",
            reason="Valid reason",
            owner="team",
        )
        errors = rule.validate()
        assert errors == []

    def test_file_level_validation(self) -> None:
        sf = SuppressionFile(
            rules=[
                SuppressionRule(resource="a_*", severity_override="warning", reason="", owner="t"),
                SuppressionRule(resource="b_*", severity_override="warning", reason="ok", owner=""),
            ]
        )
        errors = sf.validate()
        assert len(errors) == 2
        assert "Rule 0" in errors[0]
        assert "Rule 1" in errors[1]
