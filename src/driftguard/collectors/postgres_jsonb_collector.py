"""PostgreSQL JSONB sample collector.

Extracts JSON samples from PostgreSQL JSONB columns and feeds them
to the shape inference engine to produce a NestedResource.

Supports:
- Configurable sample limit
- Optional WHERE clause filtering
- Graceful handling of NULL rows and invalid JSON
- Custom InferenceConfig for shape inference
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import create_engine, text

from driftguard.inference.json_shape import InferenceConfig, infer_shape
from driftguard.schema.nested_models import NestedResource

logger = logging.getLogger(__name__)


class PostgresJsonbCollectorError(Exception):
    """Raised when the JSONB collector encounters an error."""


class PostgresJsonbCollector:
    """Extracts JSON samples from PostgreSQL JSONB columns for shape inference.

    Args:
        connection_string: SQLAlchemy connection string for PostgreSQL.
        table: Table name containing the JSONB column.
        column: JSONB column name to sample from.
        sample_limit: Maximum number of rows to query (default 100).
        where: Optional WHERE clause (without the WHERE keyword).
        config: Optional InferenceConfig for the shape inference engine.
    """

    def __init__(
        self,
        connection_string: str,
        table: str,
        column: str,
        sample_limit: int = 100,
        where: str | None = None,
        config: InferenceConfig | None = None,
    ) -> None:
        self._connection_string = connection_string
        self._table = table
        self._column = column
        self._sample_limit = sample_limit
        self._where = where
        self._config = config

    def collect(self) -> NestedResource:
        """Query JSONB column, parse samples, run inference.

        Returns:
            NestedResource with inferred schema from all valid samples.

        Raises:
            PostgresJsonbCollectorError: On connection or query errors.
        """
        samples = self._fetch_samples()
        source = f"{self._table}.{self._column}"

        return infer_shape(
            samples=samples,
            resource_name=self._column,
            source=source,
            config=self._config,
        )

    def _build_query(self) -> str:
        """Build the SQL query string.

        Returns:
            SQL query string for extracting JSONB samples.
        """
        where_clause = ""
        if self._where:
            where_clause = f" AND ({self._where})"

        return (
            f"SELECT {self._column}::text FROM {self._table} "
            f"WHERE {self._column} IS NOT NULL{where_clause} "
            f"LIMIT {self._sample_limit}"
        )

    def _fetch_samples(self) -> list[dict[str, Any]]:
        """Execute query and parse JSON results.

        Returns:
            List of parsed JSON objects.

        Raises:
            PostgresJsonbCollectorError: On connection errors.
        """
        try:
            engine = create_engine(self._connection_string)
        except Exception as e:
            raise PostgresJsonbCollectorError(f"Failed to create database connection: {e}") from e

        samples: list[dict[str, Any]] = []
        query = self._build_query()

        try:
            with engine.connect() as connection:
                result = connection.execute(text(query))
                for row in result:
                    raw_value = row[0]
                    if raw_value is None:
                        continue

                    try:
                        parsed = json.loads(raw_value)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(
                            "Skipping invalid JSON in %s.%s: %s",
                            self._table,
                            self._column,
                            e,
                        )
                        continue

                    if isinstance(parsed, dict):
                        samples.append(parsed)
                    else:
                        logger.warning(
                            "Skipping non-object JSON value in %s.%s: got %s",
                            self._table,
                            self._column,
                            type(parsed).__name__,
                        )
        except PostgresJsonbCollectorError:
            raise
        except Exception as e:
            raise PostgresJsonbCollectorError(f"Failed to query {self._table}.{self._column}: {e}") from e
        finally:
            engine.dispose()

        return samples
