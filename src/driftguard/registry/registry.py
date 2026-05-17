"""Cross-service contract registry implementation.

Provides publish/pull/list/impact-analysis capabilities for managing
contracts across multiple services using local filesystem storage.
"""

from __future__ import annotations

from pathlib import Path

from driftguard.diff.events import (
    ChangeCategory,
    DiffResult,
)
from driftguard.registry.models import RegistryConfig
from driftguard.schema.models import ContractSnapshot


class ContractRegistry:
    """Cross-service contract registry for publish/pull/impact analysis."""

    def __init__(self, store_path: Path) -> None:
        """Uses local filesystem as registry storage.

        Directory structure:
            store_path/
                {service_name}/
                    {version}.json   -- contract snapshots
                configs/
                    {service_name}.json  -- registry configs
        """
        self.store_path = Path(store_path)

    def publish(self, service_name: str, version: str, snapshot: ContractSnapshot) -> str:
        """Publish a contract: store as {service_name}/{version}.json.

        Returns the path where the contract was stored.
        """
        service_dir = self.store_path / service_name
        service_dir.mkdir(parents=True, exist_ok=True)
        file_path = service_dir / f"{version}.json"
        data = snapshot.model_dump_json(indent=2)
        file_path.write_text(data, encoding="utf-8")
        return str(file_path)

    def pull(self, service_name: str, version: str = "latest") -> ContractSnapshot:
        """Pull a specific version or latest.

        If version is "latest", returns the most recently published version
        based on alphabetical sort of version names (semantic versioning friendly).
        Raises FileNotFoundError if not found.
        """
        service_dir = self.store_path / service_name
        if not service_dir.exists():
            raise FileNotFoundError(f"Service not found in registry: {service_name}")

        if version == "latest":
            versions = self.list_versions(service_name)
            if not versions:
                raise FileNotFoundError(f"No versions found for service: {service_name}")
            version = versions[-1]  # last in sorted order = latest

        file_path = service_dir / f"{version}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Version not found: {service_name}/{version}")

        text = file_path.read_text(encoding="utf-8")
        return ContractSnapshot.model_validate_json(text)

    def list_services(self) -> list[str]:
        """List all registered services."""
        if not self.store_path.exists():
            return []
        return sorted(d.name for d in self.store_path.iterdir() if d.is_dir() and d.name != "configs")

    def list_versions(self, service_name: str) -> list[str]:
        """List all versions for a service, sorted alphabetically."""
        service_dir = self.store_path / service_name
        if not service_dir.exists():
            return []
        return sorted(p.stem for p in service_dir.glob("*.json"))

    def register_config(self, config: RegistryConfig) -> str:
        """Register a service config (metadata + dependencies).

        Returns the path where the config was stored.
        """
        configs_dir = self.store_path / "configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        file_path = configs_dir / f"{config.service.service_name}.json"
        data = config.model_dump_json(indent=2)
        file_path.write_text(data, encoding="utf-8")
        return str(file_path)

    def load_config(self, service_name: str) -> RegistryConfig:
        """Load a service's registry config.

        Raises FileNotFoundError if not registered.
        """
        configs_dir = self.store_path / "configs"
        file_path = configs_dir / f"{service_name}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Config not found for service: {service_name}")
        text = file_path.read_text(encoding="utf-8")
        return RegistryConfig.model_validate_json(text)

    def list_configs(self) -> list[RegistryConfig]:
        """Load all registered service configs."""
        configs_dir = self.store_path / "configs"
        if not configs_dir.exists():
            return []
        configs: list[RegistryConfig] = []
        for path in sorted(configs_dir.glob("*.json")):
            text = path.read_text(encoding="utf-8")
            configs.append(RegistryConfig.model_validate_json(text))
        return configs

    def impact_analysis(self, service_name: str, diff_result: DiffResult) -> list[str]:
        """Given changes in service_name, return list of impacted consumer services.

        Logic:
        1. Load all RegistryConfigs
        2. Find services with dependencies on the changed service
        3. Check if any required_fields overlap with removed/changed fields in diff_result
        4. Return impacted service names
        """
        # Collect field paths that were removed or changed
        affected_fields = self._extract_affected_fields(diff_result)

        if not affected_fields:
            return []

        # Find all consumers that depend on this service
        configs = self.list_configs()
        impacted: list[str] = []

        for config in configs:
            for dep in config.dependencies:
                if dep.service_name != service_name:
                    continue
                # Check if any required fields are in the affected set
                for required_field in dep.required_fields:
                    if required_field in affected_fields:
                        impacted.append(config.service.service_name)
                        break  # one hit is enough to mark as impacted

        return sorted(set(impacted))

    def _extract_affected_fields(self, diff_result: DiffResult) -> set[str]:
        """Extract field paths that were removed or had breaking changes."""
        affected: set[str] = set()

        # Categories that represent removed or breaking field changes
        breaking_categories = {
            ChangeCategory.FIELD_REMOVED,
            ChangeCategory.TYPE_CHANGED,
            ChangeCategory.FIELD_RENAMED,
            ChangeCategory.RESOURCE_REMOVED,
            ChangeCategory.NESTED_FIELD_REMOVED,
            ChangeCategory.NESTED_FIELD_TYPE_CHANGED,
        }

        for event in diff_result.events:
            if event.category not in breaking_categories:
                continue

            if event.category in (
                ChangeCategory.FIELD_REMOVED,
                ChangeCategory.TYPE_CHANGED,
            ):
                affected.add(event.field_name)  # type: ignore[attr-defined]
            elif event.category == ChangeCategory.FIELD_RENAMED:
                affected.add(event.old_name)  # type: ignore[attr-defined]
            elif event.category == ChangeCategory.RESOURCE_REMOVED:
                affected.add(event.resource_name)
            elif event.category in (
                ChangeCategory.NESTED_FIELD_REMOVED,
                ChangeCategory.NESTED_FIELD_TYPE_CHANGED,
            ):
                affected.add(event.path)  # type: ignore[attr-defined]

        return affected
