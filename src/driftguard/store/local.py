"""Local file-based snapshot store.

Stores ContractSnapshots as versioned JSON files in a local directory.
Default location: .driftguard/snapshots/
"""

from __future__ import annotations

from pathlib import Path

from driftguard.schema.models import ContractSnapshot

DEFAULT_STORE_DIR = ".driftguard/snapshots"


class LocalStore:
    """Read/write snapshots as JSON files on the local filesystem."""

    def __init__(self, base_dir: str | Path = DEFAULT_STORE_DIR) -> None:
        self.base_dir = Path(base_dir)

    def _snapshot_path(self, name: str) -> Path:
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_name}.json"

    def save(self, snapshot: ContractSnapshot) -> Path:
        """Save a snapshot to disk. Creates directories if needed."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self._snapshot_path(snapshot.name)
        data = snapshot.model_dump_json(indent=2)
        path.write_text(data, encoding="utf-8")
        return path

    def load(self, name: str) -> ContractSnapshot:
        """Load a snapshot by name. Raises FileNotFoundError if not found."""
        path = self._snapshot_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {path}")
        text = path.read_text(encoding="utf-8")
        return ContractSnapshot.model_validate_json(text)

    def exists(self, name: str) -> bool:
        """Check if a snapshot exists."""
        return self._snapshot_path(name).exists()

    def list_snapshots(self) -> list[str]:
        """List all available snapshot names."""
        if not self.base_dir.exists():
            return []
        return sorted(p.stem for p in self.base_dir.glob("*.json"))

    def delete(self, name: str) -> bool:
        """Delete a snapshot. Returns True if deleted, False if not found."""
        path = self._snapshot_path(name)
        if path.exists():
            path.unlink()
            return True
        return False
