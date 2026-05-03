"""Golden tests for OpenAPI deep diff.

Verifies that diffing baseline vs breaking-current produces
the expected events and policy decisions.
"""

from pathlib import Path

import pytest

from driftguard.collectors.openapi_extractor import extract_openapi_contract
from driftguard.diff.events import ChangeCategory
from driftguard.diff.openapi_engine import compute_openapi_diff
from driftguard.policy.engine import evaluate
from driftguard.policy.models import Severity

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def breaking_diff():
    baseline = extract_openapi_contract(FIXTURE_DIR / "openapi_baseline.yaml")
    current = extract_openapi_contract(FIXTURE_DIR / "openapi_breaking_current.yaml")
    return compute_openapi_diff(baseline, current)


@pytest.fixture
def breaking_policy(breaking_diff):
    return evaluate(breaking_diff)


class TestOpenApiPathDiff:
    def test_owners_path_removed(self, breaking_diff) -> None:
        removed = breaking_diff.events_by_category(ChangeCategory.OPENAPI_PATH_REMOVED)
        paths = [e.path for e in removed]
        assert "/owners" in paths

    def test_health_path_added(self, breaking_diff) -> None:
        added = breaking_diff.events_by_category(ChangeCategory.OPENAPI_PATH_ADDED)
        paths = [e.path for e in added]
        assert "/health" in paths


class TestOpenApiMethodDiff:
    def test_delete_method_removed(self, breaking_diff) -> None:
        removed = breaking_diff.events_by_category(ChangeCategory.OPENAPI_METHOD_REMOVED)
        ops = [(e.method, e.path) for e in removed]
        assert ("delete", "/pets/{petId}") in ops

    def test_no_method_added(self, breaking_diff) -> None:
        # /health GET is a new path, not a method add on existing path
        added = breaking_diff.events_by_category(ChangeCategory.OPENAPI_METHOD_ADDED)
        assert len(added) == 0


class TestOpenApiParameterDiff:
    def test_required_header_added(self, breaking_diff) -> None:
        added = breaking_diff.events_by_category(ChangeCategory.OPENAPI_PARAMETER_ADDED)
        headers = [e for e in added if e.location == "header"]
        assert len(headers) == 1
        assert headers[0].param_name == "X-Api-Key"
        assert headers[0].required is True

    def test_status_param_became_required(self, breaking_diff) -> None:
        changed = breaking_diff.events_by_category(ChangeCategory.OPENAPI_PARAMETER_CHANGED)
        status_changes = [e for e in changed if e.param_name == "status"]
        assert len(status_changes) == 1
        assert "required: False -> True" in status_changes[0].change_detail

    def test_petid_type_changed(self, breaking_diff) -> None:
        changed = breaking_diff.events_by_category(ChangeCategory.OPENAPI_PARAMETER_CHANGED)
        petid_changes = [e for e in changed if e.param_name == "petId"]
        assert len(petid_changes) == 1
        assert "type: integer -> string" in petid_changes[0].change_detail


class TestOpenApiResponseDiff:
    def test_400_status_removed(self, breaking_diff) -> None:
        removed = breaking_diff.events_by_category(ChangeCategory.OPENAPI_RESPONSE_STATUS_REMOVED)
        codes = [(e.method, e.path, e.status_code) for e in removed]
        assert ("get", "/pets", "400") in codes

    def test_response_field_removed_tag(self, breaking_diff) -> None:
        """Pet.tag removed from GET /pets 200 response."""
        removed = breaking_diff.events_by_category(ChangeCategory.FIELD_REMOVED)
        response_removed = [e for e in removed if "response" in e.resource_name and e.field_name == "tag"]
        assert len(response_removed) >= 1


class TestOpenApiRequestBodyDiff:
    def test_required_request_field_added(self, breaking_diff) -> None:
        """PetCreate.category added as required in POST /pets request body."""
        added = breaking_diff.events_by_category(ChangeCategory.FIELD_ADDED)
        request_added = [e for e in added if "request" in e.resource_name and e.field_name == "category"]
        assert len(request_added) == 1
        assert request_added[0].required is True

    def test_request_field_removed_tag(self, breaking_diff) -> None:
        """PetCreate.tag removed from POST /pets request body."""
        removed = breaking_diff.events_by_category(ChangeCategory.FIELD_REMOVED)
        request_removed = [e for e in removed if "request" in e.resource_name and e.field_name == "tag"]
        assert len(request_removed) == 1


class TestOpenApiDeprecated:
    def test_deprecated_endpoint(self, breaking_diff) -> None:
        deprecated = breaking_diff.events_by_category(ChangeCategory.OPENAPI_ENDPOINT_DEPRECATED)
        assert len(deprecated) == 1
        assert deprecated[0].method == "get"
        assert deprecated[0].path == "/pets/{petId}"


class TestOpenApiPolicyRules:
    def test_path_removed_is_breaking(self, breaking_policy) -> None:
        path_removed = [d for d in breaking_policy.decisions if d.event.category == ChangeCategory.OPENAPI_PATH_REMOVED]
        assert all(d.severity == Severity.BREAKING for d in path_removed)

    def test_method_removed_is_breaking(self, breaking_policy) -> None:
        method_removed = [
            d for d in breaking_policy.decisions if d.event.category == ChangeCategory.OPENAPI_METHOD_REMOVED
        ]
        assert all(d.severity == Severity.BREAKING for d in method_removed)

    def test_response_status_removed_is_breaking(self, breaking_policy) -> None:
        status_removed = [
            d for d in breaking_policy.decisions if d.event.category == ChangeCategory.OPENAPI_RESPONSE_STATUS_REMOVED
        ]
        assert all(d.severity == Severity.BREAKING for d in status_removed)

    def test_required_param_added_is_breaking(self, breaking_policy) -> None:
        param_added = [
            d
            for d in breaking_policy.decisions
            if d.event.category == ChangeCategory.OPENAPI_PARAMETER_ADDED and d.event.required
        ]
        assert all(d.severity == Severity.BREAKING for d in param_added)

    def test_param_became_required_is_breaking(self, breaking_policy) -> None:
        param_changed = [
            d
            for d in breaking_policy.decisions
            if d.event.category == ChangeCategory.OPENAPI_PARAMETER_CHANGED
            and "required: False -> True" in d.event.change_detail
        ]
        assert all(d.severity == Severity.BREAKING for d in param_changed)

    def test_deprecated_is_warning(self, breaking_policy) -> None:
        deprecated = [
            d for d in breaking_policy.decisions if d.event.category == ChangeCategory.OPENAPI_ENDPOINT_DEPRECATED
        ]
        assert all(d.severity == Severity.WARNING for d in deprecated)

    def test_path_added_is_info(self, breaking_policy) -> None:
        path_added = [d for d in breaking_policy.decisions if d.event.category == ChangeCategory.OPENAPI_PATH_ADDED]
        assert all(d.severity == Severity.INFO for d in path_added)

    def test_has_breaking_changes(self, breaking_policy) -> None:
        assert breaking_policy.has_breaking

    def test_breaking_count_at_least_5(self, breaking_policy) -> None:
        # Path removed, method removed, status removed, required param added,
        # param became required, required request field added, response field removed
        assert breaking_policy.breaking_count >= 5

    def test_response_field_removed_is_breaking(self, breaking_policy) -> None:
        """Response field removed should be breaking (consumers depend on it)."""
        field_removed = [
            d
            for d in breaking_policy.decisions
            if d.event.category == ChangeCategory.FIELD_REMOVED and "response" in d.event.resource_name
        ]
        assert all(d.severity == Severity.BREAKING for d in field_removed)

    def test_required_request_field_added_is_breaking(self, breaking_policy) -> None:
        """Required field added to request body breaks existing clients."""
        field_added = [
            d
            for d in breaking_policy.decisions
            if d.event.category == ChangeCategory.FIELD_ADDED
            and "request" in d.event.resource_name
            and d.event.required
        ]
        assert all(d.severity == Severity.BREAKING for d in field_added)
