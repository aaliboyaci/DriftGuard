"""JSON shape inference engine.

Analyzes one or more JSON samples and produces a NestedResource
describing the inferred schema shape with occurrence statistics.

Key behaviors:
- Dot-path notation for nested objects: user.email
- Array bracket notation: items[].sku
- Type inference: string, integer, number, boolean, object, array, null, mixed
- Format hints: date, datetime, uuid, email
- Enum candidate detection for low-cardinality string fields
- Confidence = occurrence_count / sample_count
- Never stores raw values (PII safety)
"""

from __future__ import annotations

import re
from typing import Any

from driftguard.schema.nested_models import NestedField, NestedFieldType, NestedResource

# Format detection patterns
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class InferenceConfig:
    """Configuration for shape inference behavior."""

    def __init__(
        self,
        max_depth: int = 10,
        max_enum_values: int = 20,
        enum_min_repetition_ratio: float = 0.2,
        max_samples: int = 10000,
    ) -> None:
        self.max_depth = max_depth
        self.max_enum_values = max_enum_values
        self.enum_min_repetition_ratio = enum_min_repetition_ratio
        self.max_samples = max_samples


def infer_shape(
    samples: list[dict[str, Any]],
    resource_name: str = "payload",
    source: str = "",
    config: InferenceConfig | None = None,
) -> NestedResource:
    """Infer nested schema from multiple JSON samples.

    Args:
        samples: List of JSON objects (dicts) to analyze.
        resource_name: Name for the resulting resource.
        source: Origin description (e.g., "orders.payload").
        config: Inference configuration.

    Returns:
        NestedResource with all discovered fields and statistics.
    """
    if config is None:
        config = InferenceConfig()

    effective_samples = samples[: config.max_samples]
    sample_count = len(effective_samples)

    if sample_count == 0:
        return NestedResource(name=resource_name, source=source, sample_count=0)

    # Accumulate path statistics
    path_stats: dict[str, _PathAccumulator] = {}

    for idx, sample in enumerate(effective_samples):
        _walk(sample, "", path_stats, config, depth=0, sample_idx=idx)

    # Convert accumulators to NestedFields
    fields: list[NestedField] = []
    max_depth = 0

    for path, acc in sorted(path_stats.items()):
        field_type = acc.resolve_type()
        confidence = acc.count / sample_count if sample_count > 0 else 0.0
        nullable = acc.null_count > 0
        required = confidence == 1.0

        # Enum candidates
        enum_candidates = _detect_enum(acc, sample_count, config)

        # Format hint
        format_hint = _detect_format(acc)

        fields.append(
            NestedField(
                path=path,
                field_type=field_type,
                nullable=nullable,
                required=required,
                occurrence_count=acc.count,
                sample_count=sample_count,
                confidence=round(confidence, 4),
                enum_candidates=enum_candidates,
                format_hint=format_hint,
            )
        )

        depth = path.count(".") + 1
        if depth > max_depth:
            max_depth = depth

    return NestedResource(
        name=resource_name,
        source=source,
        fields=fields,
        sample_count=sample_count,
        max_depth=max_depth,
    )


def infer_shape_single(
    sample: dict[str, Any],
    resource_name: str = "payload",
    source: str = "",
    config: InferenceConfig | None = None,
) -> NestedResource:
    """Convenience: infer from a single sample."""
    return infer_shape([sample], resource_name=resource_name, source=source, config=config)


class _PathAccumulator:
    """Accumulates type and value statistics for a single path."""

    __slots__ = ("null_count", "sample_indices", "string_values", "types")

    def __init__(self) -> None:
        self.sample_indices: set[int] = set()
        self.null_count: int = 0
        self.types: dict[str, int] = {}
        self.string_values: list[str] = []  # capped for enum detection

    @property
    def count(self) -> int:
        return len(self.sample_indices)

    def add(self, value: Any, sample_idx: int) -> None:
        self.sample_indices.add(sample_idx)
        if value is None:
            self.null_count += 1
            self.types["null"] = self.types.get("null", 0) + 1
            return

        t = _infer_type(value)
        self.types[t] = self.types.get(t, 0) + 1

        # Track string values for enum detection (cap at 1000)
        if t == "string" and len(self.string_values) < 1000:
            self.string_values.append(str(value))

    def resolve_type(self) -> NestedFieldType:
        """Resolve the dominant type from observed types."""
        non_null = {k: v for k, v in self.types.items() if k != "null"}
        if not non_null:
            return NestedFieldType.NULL
        if len(non_null) == 1:
            return NestedFieldType(next(iter(non_null)))
        # integer + number → number
        if set(non_null.keys()) == {"integer", "number"}:
            return NestedFieldType.NUMBER
        return NestedFieldType.MIXED


def _infer_type(value: Any) -> str:
    """Infer atomic type from a Python value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "string"


def _walk(
    obj: Any,
    prefix: str,
    stats: dict[str, _PathAccumulator],
    config: InferenceConfig,
    depth: int,
    sample_idx: int,
) -> None:
    """Recursively walk a JSON object and accumulate path stats."""
    if depth >= config.max_depth:
        return

    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            acc = stats.setdefault(path, _PathAccumulator())
            acc.add(value, sample_idx)

            if isinstance(value, dict):
                _walk(value, path, stats, config, depth + 1, sample_idx)
            elif isinstance(value, list):
                _walk_array(value, path, stats, config, depth + 1, sample_idx)


def _walk_array(
    arr: list[Any],
    prefix: str,
    stats: dict[str, _PathAccumulator],
    config: InferenceConfig,
    depth: int,
    sample_idx: int,
) -> None:
    """Walk array items and accumulate stats under []-suffixed paths."""
    if depth >= config.max_depth:
        return

    for item in arr:
        if isinstance(item, dict):
            for key, value in item.items():
                path = f"{prefix}[].{key}"
                acc = stats.setdefault(path, _PathAccumulator())
                acc.add(value, sample_idx)

                if isinstance(value, dict):
                    _walk(value, path, stats, config, depth + 1, sample_idx)
                elif isinstance(value, list):
                    _walk_array(value, path, stats, config, depth + 1, sample_idx)
        # Primitive arrays: track item type
        elif item is not None:
            path = f"{prefix}[]"
            acc = stats.setdefault(path, _PathAccumulator())
            acc.add(item, sample_idx)


def _detect_enum(
    acc: _PathAccumulator,
    sample_count: int,
    config: InferenceConfig,
) -> list[str] | None:
    """Detect if a string field looks like an enum."""
    if not acc.string_values:
        return None

    distinct = set(acc.string_values)
    if len(distinct) > config.max_enum_values:
        return None

    # Check repetition ratio: each value should appear enough times
    if len(acc.string_values) < 2:
        return None

    avg_frequency = len(acc.string_values) / len(distinct)
    if avg_frequency < (1.0 / config.enum_min_repetition_ratio) and len(distinct) > 5:
        return None

    return sorted(distinct)


def _detect_format(acc: _PathAccumulator) -> str | None:
    """Detect string format hints from observed values."""
    if not acc.string_values or "string" not in acc.types:
        return None

    # Sample a few values for detection
    check = acc.string_values[:20]
    if not check:
        return None

    # Check UUID
    if all(_UUID_RE.match(v) for v in check):
        return "uuid"
    # Check email
    if all(_EMAIL_RE.match(v) for v in check):
        return "email"
    # Check datetime
    if all(_DATETIME_RE.match(v) for v in check):
        return "datetime"
    # Check date
    if all(_DATE_RE.match(v) for v in check):
        return "date"

    return None
