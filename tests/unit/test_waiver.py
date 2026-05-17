"""Tests for the waiver store."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from driftguard.policy.waiver import Waiver, WaiverStore


@pytest.fixture
def waiver_path(tmp_path: Path) -> Path:
    return tmp_path / "waivers.yaml"


@pytest.fixture
def store(waiver_path: Path) -> WaiverStore:
    return WaiverStore(waiver_path)


@pytest.fixture
def sample_waiver() -> Waiver:
    return Waiver(
        id="WVR-001",
        resource="users",
        description="Allow nullable change on phone field",
        reason="Phone field migration in progress",
        owner="auth-team",
        created_at="2026-05-01",
        expires_at="2026-08-01",
    )


@pytest.fixture
def expired_waiver() -> Waiver:
    return Waiver(
        id="WVR-002",
        resource="legacy_orders",
        description="Legacy table removal accepted",
        reason="Table being sunset",
        owner="data-team",
        created_at="2025-01-01",
        expires_at="2025-06-01",
    )


class TestWaiverCreate:
    """Test waiver creation."""

    def test_create_waiver(self, store: WaiverStore, sample_waiver: Waiver) -> None:
        store.create(sample_waiver)
        waivers = store.list_all()
        assert len(waivers) == 1
        assert waivers[0].id == "WVR-001"
        assert waivers[0].resource == "users"
        assert waivers[0].reason == "Phone field migration in progress"

    def test_create_multiple_waivers(self, store: WaiverStore, sample_waiver: Waiver, expired_waiver: Waiver) -> None:
        store.create(sample_waiver)
        store.create(expired_waiver)
        waivers = store.list_all()
        assert len(waivers) == 2


class TestWaiverList:
    """Test listing waivers."""

    def test_list_empty_store(self, store: WaiverStore) -> None:
        waivers = store.list_all()
        assert waivers == []

    def test_list_nonexistent_file(self, tmp_path: Path) -> None:
        store = WaiverStore(tmp_path / "nonexistent.yaml")
        waivers = store.list_all()
        assert waivers == []

    def test_list_preserves_all_fields(self, store: WaiverStore, sample_waiver: Waiver) -> None:
        store.create(sample_waiver)
        waivers = store.list_all()
        w = waivers[0]
        assert w.id == sample_waiver.id
        assert w.resource == sample_waiver.resource
        assert w.description == sample_waiver.description
        assert w.reason == sample_waiver.reason
        assert w.owner == sample_waiver.owner
        assert w.created_at == sample_waiver.created_at
        assert w.expires_at == sample_waiver.expires_at


class TestWaiverValidation:
    """Test waiver expiry validation."""

    def test_validate_no_expired(self, store: WaiverStore, sample_waiver: Waiver) -> None:
        store.create(sample_waiver)
        warnings = store.validate()
        assert warnings == []

    def test_validate_expired_waiver(self, store: WaiverStore, expired_waiver: Waiver) -> None:
        store.create(expired_waiver)
        warnings = store.validate()
        assert len(warnings) == 1
        assert "WVR-002" in warnings[0]
        assert "expired" in warnings[0]

    def test_validate_mixed_waivers(self, store: WaiverStore, sample_waiver: Waiver, expired_waiver: Waiver) -> None:
        store.create(sample_waiver)
        store.create(expired_waiver)
        warnings = store.validate()
        assert len(warnings) == 1


class TestWaiverExpire:
    """Test expiring specific waivers."""

    def test_expire_existing_waiver(self, store: WaiverStore, sample_waiver: Waiver) -> None:
        store.create(sample_waiver)
        result = store.expire("WVR-001")
        assert result is True
        waivers = store.list_all()
        assert waivers[0].is_expired() is True

    def test_expire_nonexistent_waiver(self, store: WaiverStore) -> None:
        result = store.expire("WVR-999")
        assert result is False

    def test_expire_updates_file(self, store: WaiverStore, sample_waiver: Waiver, waiver_path: Path) -> None:
        store.create(sample_waiver)
        store.expire("WVR-001")

        # Read back from file directly
        with open(waiver_path) as f:
            data = yaml.safe_load(f)
        assert data["waivers"][0]["expires_at"] is not None


class TestWaiverPersistence:
    """Test waiver file persistence (write + read back)."""

    def test_write_and_read_back(self, waiver_path: Path) -> None:
        store1 = WaiverStore(waiver_path)
        waiver = Waiver(
            id="WVR-100",
            resource="products",
            description="Allow type change",
            reason="Migration in progress",
            owner="catalog-team",
            created_at="2026-03-15",
            expires_at="2026-09-15",
        )
        store1.create(waiver)

        # Create a new store instance reading the same file
        store2 = WaiverStore(waiver_path)
        waivers = store2.list_all()
        assert len(waivers) == 1
        assert waivers[0].id == "WVR-100"
        assert waivers[0].resource == "products"

    def test_file_is_valid_yaml(self, store: WaiverStore, sample_waiver: Waiver, waiver_path: Path) -> None:
        store.create(sample_waiver)
        with open(waiver_path) as f:
            data = yaml.safe_load(f)
        assert "waivers" in data
        assert isinstance(data["waivers"], list)
        assert len(data["waivers"]) == 1

    def test_waiver_without_expiry(self, store: WaiverStore, waiver_path: Path) -> None:
        waiver = Waiver(
            id="WVR-200",
            resource="accounts",
            description="Permanent waiver",
            reason="Known accepted drift",
            owner="infra-team",
            created_at="2026-01-01",
            expires_at=None,
        )
        store.create(waiver)

        with open(waiver_path) as f:
            data = yaml.safe_load(f)
        # expires_at should not be in the output when None
        assert "expires_at" not in data["waivers"][0]
