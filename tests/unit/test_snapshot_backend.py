"""Tests for snapshot backend interface, S3 backend, and registry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from driftguard.schema.models import (
    ContractSnapshot,
    FieldDef,
    ResourceSchema,
    SourceType,
)
from driftguard.store.backend import SnapshotBackend
from driftguard.store.local import LocalStore
from driftguard.store.registry import SnapshotRegistry
from driftguard.store.s3_backend import S3Backend


def _make_snapshot(name: str = "test") -> ContractSnapshot:
    return ContractSnapshot(
        name=name,
        resources=[
            ResourceSchema(
                name="users",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer"),
                    FieldDef(name="email", field_type="string"),
                ],
            )
        ],
    )


class TestLocalStoreImplementsBackend:
    """Verify LocalStore implements SnapshotBackend interface."""

    def test_is_subclass(self) -> None:
        assert issubclass(LocalStore, SnapshotBackend)

    def test_is_instance(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        assert isinstance(store, SnapshotBackend)

    def test_save_returns_string(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        result = store.save(_make_snapshot("test"))
        assert isinstance(result, str)

    def test_exists_true(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        store.save(_make_snapshot("baseline"))
        assert store.exists("baseline") is True

    def test_exists_false(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        assert store.exists("nonexistent") is False

    def test_all_abstract_methods_implemented(self) -> None:
        """Ensure LocalStore doesn't have leftover abstract methods."""
        # If any abstractmethod is missing, instantiation would fail
        # We just verify we can instantiate with a path
        store = LocalStore("/tmp/test")
        assert store is not None


class TestS3BackendLazyImport:
    """Test S3Backend can be instantiated without boto3."""

    def test_init_without_boto3(self) -> None:
        """S3Backend init should NOT import boto3 (lazy import)."""
        backend = S3Backend(bucket="my-bucket", prefix="driftguard/")
        assert backend.bucket == "my-bucket"
        assert backend.prefix == "driftguard/"
        assert backend._client is None

    def test_init_with_all_params(self) -> None:
        backend = S3Backend(
            bucket="test-bucket",
            prefix="snapshots/",
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        assert backend.bucket == "test-bucket"
        assert backend.prefix == "snapshots/"
        assert backend.endpoint_url == "http://localhost:9000"
        assert backend.region == "us-east-1"

    def test_is_subclass(self) -> None:
        assert issubclass(S3Backend, SnapshotBackend)

    def test_get_client_raises_without_boto3(self) -> None:
        """If boto3 is not available, _get_client should raise ImportError."""
        backend = S3Backend(bucket="test")
        with (
            patch.dict("sys.modules", {"boto3": None}),
            patch("builtins.__import__", side_effect=ImportError("No module named 'boto3'")),
            pytest.raises(ImportError, match="boto3 is required"),
        ):
            backend._get_client()

    def test_object_key_construction(self) -> None:
        backend = S3Backend(bucket="b", prefix="driftguard/")
        assert backend._object_key("baseline") == "driftguard/baseline.json"
        assert backend._object_key("feature/test") == "driftguard/feature/test.json"


class TestS3BackendWithMock:
    """Test S3Backend operations with mocked boto3 client."""

    def _make_backend_with_mock(self) -> tuple[S3Backend, MagicMock]:
        backend = S3Backend(bucket="test-bucket", prefix="snaps/")
        mock_client = MagicMock()
        backend._client = mock_client
        return backend, mock_client

    def test_save(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        snap = _make_snapshot("baseline")
        result = backend.save(snap)
        assert result == "s3://test-bucket/snaps/baseline.json"
        mock_client.put_object.assert_called_once()
        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "snaps/baseline.json"
        assert call_kwargs["ContentType"] == "application/json"

    def test_load(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        snap = _make_snapshot("baseline")
        json_data = snap.model_dump_json(indent=2)

        mock_body = MagicMock()
        mock_body.read.return_value = json_data.encode("utf-8")
        mock_client.get_object.return_value = {"Body": mock_body}

        loaded = backend.load("baseline")
        assert loaded.name == "baseline"
        assert loaded.resource_names == {"users"}
        mock_client.get_object.assert_called_once_with(Bucket="test-bucket", Key="snaps/baseline.json")

    def test_load_not_found(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        mock_client.exceptions.NoSuchKey = type("NoSuchKey", (Exception,), {})
        mock_client.get_object.side_effect = mock_client.exceptions.NoSuchKey("not found")

        with pytest.raises(FileNotFoundError, match="Snapshot not found"):
            backend.load("missing")

    def test_list_snapshots(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "snaps/alpha.json"},
                    {"Key": "snaps/beta.json"},
                    {"Key": "snaps/gamma.json"},
                ]
            }
        ]

        result = backend.list_snapshots()
        assert result == ["alpha", "beta", "gamma"]

    def test_list_snapshots_empty(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        mock_paginator = MagicMock()
        mock_client.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{}]

        result = backend.list_snapshots()
        assert result == []

    def test_exists_true(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        mock_client.head_object.return_value = {}

        assert backend.exists("baseline") is True
        mock_client.head_object.assert_called_once_with(Bucket="test-bucket", Key="snaps/baseline.json")

    def test_exists_false(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        mock_client.exceptions.ClientError = type("ClientError", (Exception,), {})
        mock_client.head_object.side_effect = mock_client.exceptions.ClientError("404")

        assert backend.exists("missing") is False

    def test_delete_existing(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        mock_client.head_object.return_value = {}  # exists returns True

        result = backend.delete("baseline")
        assert result is True
        mock_client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="snaps/baseline.json")

    def test_delete_not_found(self) -> None:
        backend, mock_client = self._make_backend_with_mock()
        mock_client.exceptions.ClientError = type("ClientError", (Exception,), {})
        mock_client.head_object.side_effect = mock_client.exceptions.ClientError("404")

        result = backend.delete("missing")
        assert result is False
        mock_client.delete_object.assert_not_called()


class TestSnapshotRegistry:
    """Test branch-aware snapshot registry."""

    def test_save_for_branch(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)
        snap = _make_snapshot("baseline")

        result = registry.save_for_branch(snap, "feature/login")
        assert "branches" in result
        assert store.exists("branches/feature_login/baseline")

    def test_load_baseline(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)

        snap = _make_snapshot("baseline")
        registry.save_for_branch(snap, "main")

        loaded = registry.load_baseline("baseline", branch="main")
        assert loaded.name == "baseline"
        assert loaded.resource_names == {"users"}

    def test_load_baseline_not_found(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)

        with pytest.raises(FileNotFoundError):
            registry.load_baseline("baseline", branch="main")

    def test_discover_baseline_current_branch(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)

        snap = _make_snapshot("baseline")
        registry.save_for_branch(snap, "feature/auth")

        result = registry.discover_baseline("feature/auth")
        assert result is not None
        assert result.name == "baseline"

    def test_discover_baseline_fallback_to_main(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)

        snap = _make_snapshot("baseline")
        registry.save_for_branch(snap, "main")

        result = registry.discover_baseline("feature/new", fallback_branch="main")
        assert result is not None
        assert result.name == "baseline"

    def test_discover_baseline_none(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)

        result = registry.discover_baseline("feature/new")
        assert result is None

    def test_discover_baseline_same_branch_as_fallback(self, tmp_path) -> None:
        """If current_branch == fallback_branch and not found, return None."""
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)

        result = registry.discover_baseline("main", fallback_branch="main")
        assert result is None

    def test_custom_branch_prefix(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store, branch_prefix="refs")

        snap = _make_snapshot("baseline")
        registry.save_for_branch(snap, "main")

        assert store.exists("refs/main/baseline")

    def test_list_branches(self, tmp_path) -> None:
        store = LocalStore(tmp_path / "snapshots")
        registry = SnapshotRegistry(store)

        registry.save_for_branch(_make_snapshot("baseline"), "main")
        registry.save_for_branch(_make_snapshot("baseline"), "develop")
        registry.save_for_branch(_make_snapshot("v1"), "main")

        branches = registry.list_branches()
        assert "main" in branches
        assert "develop" in branches
