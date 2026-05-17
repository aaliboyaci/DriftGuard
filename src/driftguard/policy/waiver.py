"""Waiver store for tracked drift exceptions.

Waivers are explicit, auditable records that a specific drift detection
has been reviewed and accepted. Unlike suppressions (pattern-based),
waivers are tied to specific resources and have lifecycle management.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml


@dataclass
class Waiver:
    """A single waiver record for an accepted drift detection."""

    id: str
    resource: str
    description: str
    reason: str
    owner: str
    created_at: str
    expires_at: str | None = None

    def is_expired(self) -> bool:
        """Check if this waiver has passed its expiry date."""
        if self.expires_at is None:
            return False
        try:
            expiry = date.fromisoformat(self.expires_at)
            return date.today() >= expiry
        except ValueError:
            return False


class WaiverStore:
    """Persistent storage for waivers in a YAML file."""

    def __init__(self, path: Path):
        self._path = path

    def create(self, waiver: Waiver) -> None:
        """Add a new waiver to the store."""
        waivers = self.list_all()
        waivers.append(waiver)
        self._save(waivers)

    def list_all(self) -> list[Waiver]:
        """Load all waivers from the store."""
        if not self._path.exists():
            return []

        with open(self._path) as f:
            data = yaml.safe_load(f)

        if data is None:
            return []

        raw_waivers = data.get("waivers", [])
        waivers: list[Waiver] = []
        for raw in raw_waivers:
            expires_at = raw.get("expires_at")
            if isinstance(expires_at, (date, datetime)):
                expires_at = expires_at.isoformat()
            created_at = raw.get("created_at", "")
            if isinstance(created_at, (date, datetime)):
                created_at = created_at.isoformat()
            waiver = Waiver(
                id=raw["id"],
                resource=raw["resource"],
                description=raw.get("description", ""),
                reason=raw.get("reason", ""),
                owner=raw.get("owner", ""),
                created_at=created_at,
                expires_at=expires_at,
            )
            waivers.append(waiver)

        return waivers

    def validate(self) -> list[str]:
        """Return warnings for expired waivers."""
        warnings: list[str] = []
        for waiver in self.list_all():
            if waiver.is_expired():
                warnings.append(f"Waiver '{waiver.id}' for resource '{waiver.resource}' expired on {waiver.expires_at}")
        return warnings

    def expire(self, waiver_id: str) -> bool:
        """Mark a waiver as expired by setting its expires_at to today.

        Returns True if the waiver was found and expired, False otherwise.
        """
        waivers = self.list_all()
        found = False
        for waiver in waivers:
            if waiver.id == waiver_id:
                waiver.expires_at = date.today().isoformat()
                found = True
                break

        if found:
            self._save(waivers)
        return found

    def _save(self, waivers: list[Waiver]) -> None:
        """Persist waivers to the YAML file."""
        data = {
            "waivers": [
                {
                    "id": w.id,
                    "resource": w.resource,
                    "description": w.description,
                    "reason": w.reason,
                    "owner": w.owner,
                    "created_at": w.created_at,
                    **({"expires_at": w.expires_at} if w.expires_at else {}),
                }
                for w in waivers
            ]
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
