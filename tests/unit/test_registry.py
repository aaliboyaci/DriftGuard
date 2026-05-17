"""Tests for the cross-service contract registry."""

from __future__ import annotations

import pytest

from driftguard.diff.events import (
    DiffResult,
    FieldAdded,
    FieldRemoved,
    TypeChanged,
)
from driftguard.registry.models import RegistryConfig, ServiceDependency, ServiceMetadata
from driftguard.registry.registry import ContractRegistry
from driftguard.schema.models import (
    ContractSnapshot,
    FieldDef,
    ResourceSchema,
    SourceType,
)


def _make_snapshot(name: str = "test") -> ContractSnapshot:
    """Create a minimal test snapshot."""
    return ContractSnapshot(
        name=name,
        resources=[
            ResourceSchema(
                name="orders",
                source_type=SourceType.POSTGRES,
                fields=[
                    FieldDef(name="id", field_type="integer"),
                    FieldDef(name="sku", field_type="string"),
                    FieldDef(name="quantity", field_type="integer"),
                    FieldDef(name="status", field_type="string"),
                ],
            )
        ],
    )


def _make_consumer_config(
    consumer_name: str,
    depends_on_service: str,
    contract_name: str,
    required_fields: list[str],
) -> RegistryConfig:
    """Create a registry config for a consumer service."""
    return RegistryConfig(
        service=ServiceMetadata(
            service_name=consumer_name,
            service_version="1.0.0",
            role="consumer",
        ),
        dependencies=[
            ServiceDependency(
                service_name=depends_on_service,
                contract_name=contract_name,
                required_fields=required_fields,
            )
        ],
    )


class TestContractRegistryPublishPull:
    """Tests for publish and pull operations."""

    def test_publish_and_pull(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")
        snap = _make_snapshot("v1.0.0")
        registry.publish("orders-api", "v1.0.0", snap)

        loaded = registry.pull("orders-api", "v1.0.0")
        assert loaded.name == "v1.0.0"
        assert loaded.resource_names == {"orders"}
        assert len(loaded.resources[0].fields) == 4

    def test_pull_latest(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")

        snap_v1 = _make_snapshot("v1.0.0")
        snap_v2 = _make_snapshot("v2.0.0")

        registry.publish("orders-api", "v1.0.0", snap_v1)
        registry.publish("orders-api", "v2.0.0", snap_v2)

        latest = registry.pull("orders-api", "latest")
        assert latest.name == "v2.0.0"

    def test_pull_not_found_service(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")
        with pytest.raises(FileNotFoundError, match="Service not found"):
            registry.pull("nonexistent")

    def test_pull_not_found_version(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")
        registry.publish("orders-api", "v1.0.0", _make_snapshot("v1.0.0"))
        with pytest.raises(FileNotFoundError, match="Version not found"):
            registry.pull("orders-api", "v9.9.9")


class TestContractRegistryList:
    """Tests for list operations."""

    def test_list_services(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")
        registry.publish("orders-api", "v1.0.0", _make_snapshot("v1.0.0"))
        registry.publish("inventory-api", "v1.0.0", _make_snapshot("v1.0.0"))
        registry.publish("payments-api", "v1.0.0", _make_snapshot("v1.0.0"))

        services = registry.list_services()
        assert services == ["inventory-api", "orders-api", "payments-api"]

    def test_list_services_empty(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")
        assert registry.list_services() == []

    def test_list_versions(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")
        registry.publish("orders-api", "v1.0.0", _make_snapshot("v1.0.0"))
        registry.publish("orders-api", "v1.1.0", _make_snapshot("v1.1.0"))
        registry.publish("orders-api", "v2.0.0", _make_snapshot("v2.0.0"))

        versions = registry.list_versions("orders-api")
        assert versions == ["v1.0.0", "v1.1.0", "v2.0.0"]

    def test_list_versions_nonexistent_service(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")
        assert registry.list_versions("ghost-service") == []


class TestContractRegistryImpactAnalysis:
    """Tests for impact analysis."""

    def test_impact_consumer_depends_on_removed_field(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")

        # Register a consumer that depends on "sku" field from orders-api
        consumer_config = _make_consumer_config(
            consumer_name="shipping-service",
            depends_on_service="orders-api",
            contract_name="orders",
            required_fields=["sku", "quantity"],
        )
        registry.register_config(consumer_config)

        # Simulate diff where "sku" was removed
        diff_result = DiffResult(
            baseline_name="v1.0.0",
            current_name="v2.0.0",
            events=[
                FieldRemoved(
                    resource_name="orders",
                    description="Field removed: orders.sku (string)",
                    field_name="sku",
                    field_type="string",
                ),
            ],
        )

        impacted = registry.impact_analysis("orders-api", diff_result)
        assert impacted == ["shipping-service"]

    def test_impact_consumer_depends_on_existing_field(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")

        # Register a consumer that depends on "status" field
        consumer_config = _make_consumer_config(
            consumer_name="shipping-service",
            depends_on_service="orders-api",
            contract_name="orders",
            required_fields=["status"],
        )
        registry.register_config(consumer_config)

        # Simulate diff where "sku" was removed (not "status")
        diff_result = DiffResult(
            baseline_name="v1.0.0",
            current_name="v2.0.0",
            events=[
                FieldRemoved(
                    resource_name="orders",
                    description="Field removed: orders.sku (string)",
                    field_name="sku",
                    field_type="string",
                ),
            ],
        )

        impacted = registry.impact_analysis("orders-api", diff_result)
        assert impacted == []

    def test_impact_no_consumers(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")

        # No configs registered, so no consumers exist
        diff_result = DiffResult(
            baseline_name="v1.0.0",
            current_name="v2.0.0",
            events=[
                FieldRemoved(
                    resource_name="orders",
                    description="Field removed: orders.sku (string)",
                    field_name="sku",
                    field_type="string",
                ),
            ],
        )

        impacted = registry.impact_analysis("orders-api", diff_result)
        assert impacted == []

    def test_impact_type_changed_affects_consumer(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")

        consumer_config = _make_consumer_config(
            consumer_name="analytics-service",
            depends_on_service="orders-api",
            contract_name="orders",
            required_fields=["quantity"],
        )
        registry.register_config(consumer_config)

        # Type change on "quantity" field
        diff_result = DiffResult(
            baseline_name="v1.0.0",
            current_name="v2.0.0",
            events=[
                TypeChanged(
                    resource_name="orders",
                    description="Type changed: orders.quantity (integer -> string)",
                    field_name="quantity",
                    old_type="integer",
                    new_type="string",
                ),
            ],
        )

        impacted = registry.impact_analysis("orders-api", diff_result)
        assert impacted == ["analytics-service"]

    def test_impact_multiple_consumers(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")

        # Two consumers depend on the same field
        config1 = _make_consumer_config(
            consumer_name="shipping-service",
            depends_on_service="orders-api",
            contract_name="orders",
            required_fields=["sku"],
        )
        config2 = _make_consumer_config(
            consumer_name="billing-service",
            depends_on_service="orders-api",
            contract_name="orders",
            required_fields=["sku", "quantity"],
        )
        registry.register_config(config1)
        registry.register_config(config2)

        diff_result = DiffResult(
            baseline_name="v1.0.0",
            current_name="v2.0.0",
            events=[
                FieldRemoved(
                    resource_name="orders",
                    description="Field removed: orders.sku (string)",
                    field_name="sku",
                    field_type="string",
                ),
            ],
        )

        impacted = registry.impact_analysis("orders-api", diff_result)
        assert impacted == ["billing-service", "shipping-service"]

    def test_impact_no_breaking_changes(self, tmp_path: pytest.TempPathFactory) -> None:  # type: ignore[type-arg]
        registry = ContractRegistry(store_path=tmp_path / "registry")

        consumer_config = _make_consumer_config(
            consumer_name="shipping-service",
            depends_on_service="orders-api",
            contract_name="orders",
            required_fields=["sku"],
        )
        registry.register_config(consumer_config)

        # Only an info-level change (field added), no breaking changes
        diff_result = DiffResult(
            baseline_name="v1.0.0",
            current_name="v2.0.0",
            events=[
                FieldAdded(
                    resource_name="orders",
                    description="Field added: orders.notes (string)",
                    field_name="notes",
                    field_type="string",
                    required=False,
                    nullable=True,
                ),
            ],
        )

        impacted = registry.impact_analysis("orders-api", diff_result)
        assert impacted == []
