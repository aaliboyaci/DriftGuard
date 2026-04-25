"""Base collector interface.

Every collector implements this interface: connect to source,
extract raw schema, return normalized ResourceSchema list.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from driftguard.schema.models import ResourceSchema


class BaseCollector(ABC):
    """Abstract base class for all schema collectors."""

    @abstractmethod
    def collect(self) -> list[ResourceSchema]:
        """Collect and return normalized schemas from this source."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this collector."""
        ...
