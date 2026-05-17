"""Branch/tag-aware snapshot registry.

Provides a layer over SnapshotBackend that organizes snapshots
by branch, enabling multi-branch baseline workflows in CI.
"""

from __future__ import annotations

from driftguard.schema.models import ContractSnapshot
from driftguard.store.backend import SnapshotBackend


class SnapshotRegistry:
    """Branch/tag-aware snapshot discovery."""

    def __init__(self, backend: SnapshotBackend, branch_prefix: str = "") -> None:
        self._backend = backend
        self._branch_prefix = branch_prefix

    def _branch_key(self, name: str, branch: str) -> str:
        """Build a branch-prefixed snapshot name."""
        base = self._branch_prefix if self._branch_prefix else "branches"
        return f"{base}/{branch}/{name}"

    def save_for_branch(self, snapshot: ContractSnapshot, branch: str) -> str:
        """Save with branch prefix: branches/{branch}/{name}."""
        key = self._branch_key(snapshot.name, branch)
        # Create a copy of the snapshot with the prefixed name for storage
        stored = snapshot.model_copy(update={"name": key})
        return self._backend.save(stored)

    def load_baseline(self, name: str, branch: str = "main") -> ContractSnapshot:
        """Load baseline from specific branch."""
        key = self._branch_key(name, branch)
        snapshot = self._backend.load(key)
        # Return with original name (without branch prefix)
        return snapshot.model_copy(update={"name": name})

    def discover_baseline(
        self, current_branch: str, fallback_branch: str = "main", name: str = "baseline"
    ) -> ContractSnapshot | None:
        """Try current branch first, fall back to main.

        Returns None if no baseline found in either branch.
        """
        key = self._branch_key(name, current_branch)
        if self._backend.exists(key):
            snapshot = self._backend.load(key)
            return snapshot.model_copy(update={"name": name})

        if current_branch != fallback_branch:
            fallback_key = self._branch_key(name, fallback_branch)
            if self._backend.exists(fallback_key):
                snapshot = self._backend.load(fallback_key)
                return snapshot.model_copy(update={"name": name})

        return None

    def list_branches(self) -> list[str]:
        """List all branches that have snapshots."""
        base = self._branch_prefix if self._branch_prefix else "branches"
        # Check both raw prefix (for backends like S3 that preserve /)
        # and sanitized prefix (for backends like LocalStore that replace / with _)
        prefix_slash = f"{base}/"
        prefix_underscore = f"{base}_"
        all_snapshots = self._backend.list_snapshots()
        branches: set[str] = set()
        for snap_name in all_snapshots:
            if snap_name.startswith(prefix_slash):
                rest = snap_name[len(prefix_slash) :]
                parts = rest.split("/", 1)
                if len(parts) >= 1:
                    branches.add(parts[0])
            elif snap_name.startswith(prefix_underscore):
                rest = snap_name[len(prefix_underscore) :]
                # For sanitized names, the branch/name separator is also _
                # We split on last _ to separate branch from snapshot name
                parts = rest.rsplit("_", 1)
                if len(parts) >= 2:
                    branches.add(parts[0])
        return sorted(branches)
