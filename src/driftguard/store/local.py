"""Local file-based snapshot store.

Stores ContractSnapshots as versioned JSON files in a local directory.
Default location: .driftguard/snapshots/
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from driftguard.schema.models import ContractSnapshot
from driftguard.store.backend import SnapshotBackend

DEFAULT_STORE_DIR = ".driftguard/snapshots"


class LocalStore(SnapshotBackend):
    """Read/write snapshots as JSON files on the local filesystem."""

    def __init__(self, base_dir: str | Path = DEFAULT_STORE_DIR) -> None:
        self.base_dir = Path(base_dir)

    def _snapshot_path(self, name: str) -> Path:
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self.base_dir / f"{safe_name}.json"

    def save(self, snapshot: ContractSnapshot) -> str:
        """Save a snapshot to disk. Creates directories if needed."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        path = self._snapshot_path(snapshot.name)
        data = snapshot.model_dump_json(indent=2)
        path.write_text(data, encoding="utf-8")
        return str(path)

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

    def checksum(self, name: str) -> str:
        """Return SHA-256 checksum of a snapshot file."""
        path = self._snapshot_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {path}")
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def export_snapshot(self, name: str, output_path: str | Path, compress: bool = False) -> Path:
        """Export a snapshot to a file, optionally gzip-compressed."""
        path = self._snapshot_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {path}")
        out = Path(output_path)
        content = path.read_bytes()
        if compress:
            out = out.with_suffix(".json.gz") if not str(out).endswith(".gz") else out
            out.write_bytes(gzip.compress(content))
        else:
            out.write_bytes(content)
        return out

    def import_snapshot(self, input_path: str | Path) -> ContractSnapshot:
        """Import a snapshot from a file (supports gzip)."""
        inp = Path(input_path)
        if not inp.exists():
            raise FileNotFoundError(f"File not found: {inp}")
        if str(inp).endswith(".gz"):
            content = gzip.decompress(inp.read_bytes()).decode("utf-8")
        else:
            content = inp.read_text(encoding="utf-8")
        snapshot = ContractSnapshot.model_validate_json(content)
        self.save(snapshot)
        return snapshot

    def cleanup(self, keep: int = 5) -> list[str]:
        """Remove old snapshots, keeping only the N most recent by file modification time."""
        if not self.base_dir.exists():
            return []
        files = sorted(self.base_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        removed: list[str] = []
        for f in files[keep:]:
            removed.append(f.stem)
            f.unlink()
        return removed

    def snapshot_info(self, name: str) -> dict[str, str | int]:
        """Return metadata about a stored snapshot."""
        path = self._snapshot_path(name)
        if not path.exists():
            raise FileNotFoundError(f"Snapshot not found: {path}")
        stat = path.stat()
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        return {
            "name": name,
            "size_bytes": stat.st_size,
            "checksum": hashlib.sha256(content.encode()).hexdigest(),
            "resource_count": len(data.get("resources", [])),
            "created_at": data.get("created_at", ""),
        }
