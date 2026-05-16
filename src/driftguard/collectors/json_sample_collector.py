"""JSON sample file collector.

Reads raw JSON files (single objects, arrays, or NDJSON) and feeds them
to the inference engine to produce a NestedResource describing the shape.

Supports:
- Single JSON file with an object (wrapped into a one-element list)
- Single JSON file with an array of objects
- NDJSON files (one JSON object per line)
- Multiple file paths combined into one sample set
- Configurable file size limit (default 50 MB)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from driftguard.inference.json_shape import InferenceConfig, infer_shape
from driftguard.schema.nested_models import NestedResource


class JsonSampleCollectorError(Exception):
    """Raised when the JSON sample collector encounters an error."""


class JsonSampleCollector:
    """Collects JSON samples from files and infers their schema shape.

    Args:
        paths: File paths to read JSON samples from.
        resource_name: Name for the resulting NestedResource.
        max_file_size_mb: Maximum allowed file size in megabytes.
        config: Optional InferenceConfig for the shape inference engine.
    """

    def __init__(
        self,
        paths: list[str | Path],
        resource_name: str = "",
        max_file_size_mb: int = 50,
        config: InferenceConfig | None = None,
    ) -> None:
        self._paths = [Path(p) for p in paths]
        self._resource_name = resource_name
        self._max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self._config = config

    def collect(self) -> NestedResource:
        """Read all configured files and return an inferred NestedResource.

        Returns:
            NestedResource with inferred schema from all samples.

        Raises:
            JsonSampleCollectorError: On file read or parse errors.
        """
        all_samples: list[dict[str, Any]] = []

        for path in self._paths:
            samples = self._read_file(path)
            all_samples.extend(samples)

        source = ", ".join(str(p) for p in self._paths)
        name = self._resource_name or (self._paths[0].stem if self._paths else "payload")

        return infer_shape(
            samples=all_samples,
            resource_name=name,
            source=source,
            config=self._config,
        )

    def _read_file(self, path: Path) -> list[dict[str, Any]]:
        """Read and parse a single JSON or NDJSON file.

        Args:
            path: Path to the file.

        Returns:
            List of dict samples extracted from the file.

        Raises:
            JsonSampleCollectorError: On missing file, size limit, or parse errors.
        """
        if not path.exists():
            raise JsonSampleCollectorError(f"File not found: {path}")

        file_size = path.stat().st_size
        if file_size > self._max_file_size_bytes:
            raise JsonSampleCollectorError(
                f"File exceeds size limit ({file_size} bytes > {self._max_file_size_bytes} bytes): {path}"
            )

        text = path.read_text(encoding="utf-8")

        if not text.strip():
            return []

        # Try standard JSON first
        try:
            data = json.loads(text)
            return self._normalize_parsed(data, path)
        except json.JSONDecodeError:
            pass

        # Fall back to NDJSON (one JSON object per line)
        return self._parse_ndjson(text, path)

    def _normalize_parsed(self, data: Any, path: Path) -> list[dict[str, Any]]:
        """Normalize parsed JSON into a list of dict samples.

        Args:
            data: Parsed JSON value.
            path: Source file path (for error messages).

        Returns:
            List of dict samples.

        Raises:
            JsonSampleCollectorError: If the data is not an object or array of objects.
        """
        if isinstance(data, dict):
            return [data]

        if isinstance(data, list):
            samples: list[dict[str, Any]] = []
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    samples.append(item)
                else:
                    raise JsonSampleCollectorError(f"Array item at index {idx} is not an object in file: {path}")
            return samples

        raise JsonSampleCollectorError(f"Expected JSON object or array of objects, got {type(data).__name__}: {path}")

    def _parse_ndjson(self, text: str, path: Path) -> list[dict[str, Any]]:
        """Parse NDJSON (newline-delimited JSON) content.

        Args:
            text: Raw file content.
            path: Source file path (for error messages).

        Returns:
            List of dict samples.

        Raises:
            JsonSampleCollectorError: On parse errors.
        """
        samples: list[dict[str, Any]] = []
        errors: list[str] = []

        for line_num, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: {e}")
                continue

            if isinstance(obj, dict):
                samples.append(obj)
            else:
                errors.append(f"Line {line_num}: expected object, got {type(obj).__name__}")

        if not samples and errors:
            raise JsonSampleCollectorError(f"Failed to parse any valid JSON objects from {path}: {'; '.join(errors)}")

        return samples
