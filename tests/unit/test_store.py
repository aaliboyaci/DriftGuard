"""Tests for the local snapshot store."""

import pytest

from driftguard.schema.models import (
    ContractSnapshot,
    FieldDef,
    ResourceSchema,
    SourceType,
)
from driftguard.store.local import LocalStore


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


class TestLocalStore:
    def test_save_and_load(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        snap = _make_snapshot("baseline")
        store.save(snap)
        loaded = store.load("baseline")
        assert loaded.name == "baseline"
        assert loaded.resource_names == {"users"}
        assert len(loaded.resources[0].fields) == 2

    def test_load_not_found(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        with pytest.raises(FileNotFoundError):
            store.load("nonexistent")

    def test_exists(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        assert store.exists("baseline") is False
        store.save(_make_snapshot("baseline"))
        assert store.exists("baseline") is True

    def test_list_snapshots_empty(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        assert store.list_snapshots() == []

    def test_list_snapshots(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        store.save(_make_snapshot("alpha"))
        store.save(_make_snapshot("beta"))
        store.save(_make_snapshot("gamma"))
        assert store.list_snapshots() == ["alpha", "beta", "gamma"]

    def test_delete_existing(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        store.save(_make_snapshot("temp"))
        assert store.delete("temp") is True
        assert store.exists("temp") is False

    def test_delete_nonexistent(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        assert store.delete("nope") is False

    def test_overwrite(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        snap1 = _make_snapshot("v1")
        store.save(snap1)

        snap2 = ContractSnapshot(
            name="v1",
            resources=[
                ResourceSchema(
                    name="orders",
                    source_type=SourceType.POSTGRES,
                    fields=[FieldDef(name="id", field_type="integer")],
                )
            ],
        )
        store.save(snap2)
        loaded = store.load("v1")
        assert loaded.resource_names == {"orders"}

    def test_roundtrip_preserves_all_data(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        snap = ContractSnapshot(
            name="full",
            resources=[
                ResourceSchema(
                    name="products",
                    source_type=SourceType.JSON_SCHEMA,
                    fields=[
                        FieldDef(
                            name="status",
                            field_type="string",
                            nullable=True,
                            required=False,
                            enum_values=["draft", "published"],
                        ),
                    ],
                )
            ],
            metadata={"env": "staging"},
        )
        store.save(snap)
        loaded = store.load("full")
        assert loaded.metadata == {"env": "staging"}
        field = loaded.resources[0].fields[0]
        assert field.enum_values == ["draft", "published"]
        assert field.nullable is True

    def test_creates_directories(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        deep_path = tmp_path / "a" / "b" / "c"
        store = LocalStore(deep_path)
        store.save(_make_snapshot("test"))
        assert deep_path.exists()

    def test_safe_name_with_slashes(self, tmp_path: "pytest.TempPathFactory") -> None:  # type: ignore[type-arg]
        store = LocalStore(tmp_path / "snapshots")
        snap = _make_snapshot("feature/branch")
        store.save(snap)
        assert store.exists("feature/branch")
