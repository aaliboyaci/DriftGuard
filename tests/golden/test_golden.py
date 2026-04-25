"""Golden tests - verify diff and policy results against known fixture pairs."""

from driftguard.diff.engine import compute_diff
from driftguard.diff.events import ChangeCategory
from driftguard.policy.engine import evaluate
from driftguard.policy.models import Severity
from tests.golden.fixtures import (
    baseline_snapshot,
    current_snapshot_breaking,
    current_snapshot_clean,
)


class TestGoldenBreaking:
    """Verify the breaking changes scenario produces expected results."""

    def setup_method(self) -> None:
        self.baseline = baseline_snapshot()
        self.current = current_snapshot_breaking()
        self.diff = compute_diff(self.baseline, self.current)
        self.policy = evaluate(self.diff)

    def test_total_event_count(self) -> None:
        # email removed, age type changed, status enum added, phone required added,
        # amount type widened, currency nullable changed,
        # legacy_reports removed, payments added
        assert self.diff.event_count == 8

    def test_resource_removed(self) -> None:
        removed = self.diff.events_by_category(ChangeCategory.RESOURCE_REMOVED)
        assert len(removed) == 1
        assert removed[0].resource_name == "legacy_reports"

    def test_resource_added(self) -> None:
        added = self.diff.events_by_category(ChangeCategory.RESOURCE_ADDED)
        assert len(added) == 1
        assert added[0].resource_name == "payments"

    def test_field_removed(self) -> None:
        removed = self.diff.events_by_category(ChangeCategory.FIELD_REMOVED)
        assert len(removed) == 1
        assert removed[0].resource_name == "customers"

    def test_type_changed(self) -> None:
        changed = self.diff.events_by_category(ChangeCategory.TYPE_CHANGED)
        assert len(changed) == 2  # age: integer->string, amount: integer->number

    def test_has_breaking_changes(self) -> None:
        assert self.policy.has_breaking is True

    def test_breaking_count(self) -> None:
        # email removed (breaking), phone required added (breaking),
        # legacy_reports removed (breaking)
        assert self.policy.breaking_count == 3

    def test_warning_count(self) -> None:
        # age int->string widening (warning), status enum added (warning),
        # amount int->number widening (warning), currency nullable changed (warning)
        assert self.policy.warning_count == 4

    def test_info_count(self) -> None:
        # payments resource added (info)
        assert self.policy.info_count == 1

    def test_exit_code_is_one(self) -> None:
        assert self.policy.exit_code == 1

    def test_all_decisions_have_reasons(self) -> None:
        for d in self.policy.decisions:
            assert len(d.reason) > 0


class TestGoldenClean:
    """Verify the clean (backward-compatible) scenario."""

    def setup_method(self) -> None:
        self.baseline = baseline_snapshot()
        self.current = current_snapshot_clean()
        self.diff = compute_diff(self.baseline, self.current)
        self.policy = evaluate(self.diff)

    def test_only_info_changes(self) -> None:
        assert not self.policy.has_breaking
        assert not self.policy.has_warnings

    def test_event_count(self) -> None:
        # only phone optional field added
        assert self.diff.event_count == 1

    def test_exit_code_is_zero(self) -> None:
        assert self.policy.exit_code == 0

    def test_added_field_is_info(self) -> None:
        assert self.policy.info_count == 1
        assert self.policy.decisions[0].severity == Severity.INFO


class TestGoldenIdentical:
    """Verify no changes when comparing a snapshot to itself."""

    def test_no_diff(self) -> None:
        s = baseline_snapshot()
        diff = compute_diff(s, s)
        assert not diff.has_changes

    def test_exit_code_zero(self) -> None:
        s = baseline_snapshot()
        result = evaluate(compute_diff(s, s))
        assert result.exit_code == 0
