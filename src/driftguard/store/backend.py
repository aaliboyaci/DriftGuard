"""Abstract snapshot storage backend interface.

Defines the contract that all snapshot storage backends must implement.
This enables remote storage (S3, GCS) alongside the local file store.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from driftguard.schema.models import ContractSnapshot


class SnapshotBackend(ABC):
    """Abstract snapshot storage backend."""

    @abstractmethod
    def save(self, snapshot: ContractSnapshot) -> str:
        """Save snapshot, return identifier/path."""
        ...

    @abstractmethod
    def load(self, name: str) -> ContractSnapshot:
        """Load snapshot by name. Raise FileNotFoundError if missing."""
        ...

    @abstractmethod
    def list_snapshots(self) -> list[str]:
        """List all snapshot names."""
        ...

    @abstractmethod
    def delete(self, name: str) -> bool:
        """Delete snapshot. Return True if deleted, False if not found."""
        ...

    @abstractmethod
    def exists(self, name: str) -> bool:
        """Check if snapshot exists."""
        ...
