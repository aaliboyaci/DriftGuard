"""Schema collectors for various data sources."""

from driftguard.collectors.base import BaseCollector
from driftguard.collectors.csv_collector import CsvCollector
from driftguard.collectors.json_collector import JsonSchemaCollector, OpenApiCollector
from driftguard.collectors.postgres_collector import PostgresCollector

__all__ = [
    "BaseCollector",
    "CsvCollector",
    "JsonSchemaCollector",
    "OpenApiCollector",
    "PostgresCollector",
]
