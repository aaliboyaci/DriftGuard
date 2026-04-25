"""Tests for policy decision models."""

from driftguard.diff import FieldAdded, FieldRemoved, TypeChanged
from driftguard.policy import PolicyDecision, PolicyResult, Severity


def _breaking_decision() -> PolicyDecision:
    return PolicyDecision(
        event=FieldRemoved(
            resource_name="users", description="Removed email", field_name="email", field_type="string"
        ),
        severity=Severity.BREAKING,
        reason="Consumer expects this field",
    )


def _warning_decision() -> PolicyDecision:
    return PolicyDecision(
        event=TypeChanged(
            resource_name="orders",
            description="Type changed",
            field_name="amount",
            old_type="integer",
            new_type="number",
        ),
        severity=Severity.WARNING,
        reason="Some consumers may accept this",
    )


def _info_decision() -> PolicyDecision:
    return PolicyDecision(
        event=FieldAdded(
            resource_name="users",
            description="Added phone",
            field_name="phone",
            field_type="string",
            required=False,
        ),
        severity=Severity.INFO,
        reason="Backward compatible addition",
    )


class TestPolicyDecision:
    def test_create(self) -> None:
        d = _breaking_decision()
        assert d.severity == Severity.BREAKING
        assert d.override is False

    def test_override(self) -> None:
        d = _breaking_decision()
        d.override = True
        assert d.override is True

    def test_serialization(self) -> None:
        d = _warning_decision()
        data = d.model_dump()
        restored = PolicyDecision.model_validate(data)
        assert restored.severity == Severity.WARNING


class TestPolicyResult:
    def test_empty(self) -> None:
        r = PolicyResult()
        assert r.has_breaking is False
        assert r.has_warnings is False
        assert r.breaking_count == 0
        assert r.exit_code == 0

    def test_with_breaking(self) -> None:
        r = PolicyResult(decisions=[_breaking_decision(), _info_decision()])
        assert r.has_breaking is True
        assert r.breaking_count == 1
        assert r.info_count == 1
        assert r.exit_code == 1

    def test_only_warnings(self) -> None:
        r = PolicyResult(decisions=[_warning_decision(), _info_decision()])
        assert r.has_breaking is False
        assert r.has_warnings is True
        assert r.exit_code == 0

    def test_by_severity(self) -> None:
        r = PolicyResult(decisions=[_breaking_decision(), _warning_decision(), _info_decision()])
        assert len(r.by_severity(Severity.BREAKING)) == 1
        assert len(r.by_severity(Severity.WARNING)) == 1
        assert len(r.by_severity(Severity.INFO)) == 1

    def test_counts(self) -> None:
        r = PolicyResult(
            decisions=[_breaking_decision(), _breaking_decision(), _warning_decision(), _info_decision()]
        )
        assert r.breaking_count == 2
        assert r.warning_count == 1
        assert r.info_count == 1
