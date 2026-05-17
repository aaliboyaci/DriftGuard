"""Tests for PostgreSQL JSONB sample collector."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from driftguard.collectors.postgres_jsonb_collector import (
    PostgresJsonbCollector,
    PostgresJsonbCollectorError,
)
from driftguard.inference.json_shape import InferenceConfig
from driftguard.schema.nested_models import NestedFieldType


def _make_mock_result(rows: list[tuple[str | None]]) -> MagicMock:
    """Create a mock SQLAlchemy result set."""
    mock_result = MagicMock()
    mock_result.__iter__ = lambda self: iter(rows)
    return mock_result


class TestSampleExtraction:
    """Test sample extraction with mocked DB returning JSON strings."""

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_basic_extraction(self, mock_create_engine: MagicMock) -> None:
        """Test basic JSON sample extraction from mocked rows."""
        rows = [
            ('{"id": 1, "name": "Alice"}',),
            ('{"id": 2, "name": "Bob"}',),
            ('{"id": 3, "name": "Charlie"}',),
        ]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
        )
        result = collector.collect()

        assert result.sample_count == 3
        assert result.name == "payload"
        assert result.source == "events.payload"
        assert result.get_field("id") is not None
        assert result.get_field("name") is not None
        assert result.get_field("id").field_type == NestedFieldType.INTEGER

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_nested_json_extraction(self, mock_create_engine: MagicMock) -> None:
        """Test nested JSON objects are properly inferred."""
        rows = [
            ('{"user": {"email": "a@b.com", "age": 30}}',),
            ('{"user": {"email": "c@d.com", "age": 25}}',),
        ]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="users",
            column="profile",
        )
        result = collector.collect()

        assert result.sample_count == 2
        assert result.get_field("user.email") is not None
        assert result.get_field("user.age") is not None


class TestWhereClause:
    """Test WHERE clause construction."""

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_no_where_clause(self, mock_create_engine: MagicMock) -> None:
        """Test query without WHERE clause."""
        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
            sample_limit=50,
        )
        query = collector._build_query()
        assert "WHERE payload IS NOT NULL" in query
        assert "AND" not in query
        assert "LIMIT 50" in query

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_with_where_clause(self, mock_create_engine: MagicMock) -> None:
        """Test query with custom WHERE clause."""
        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
            where="event_type = 'order'",
        )
        query = collector._build_query()
        assert "WHERE payload IS NOT NULL" in query
        assert "AND (event_type = 'order')" in query

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_where_clause_with_complex_condition(self, mock_create_engine: MagicMock) -> None:
        """Test query with complex WHERE clause."""
        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
            where="created_at > '2024-01-01' AND status IN ('active', 'pending')",
        )
        query = collector._build_query()
        assert "AND (created_at > '2024-01-01' AND status IN ('active', 'pending'))" in query


class TestSampleLimit:
    """Test sample_limit behavior."""

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_default_limit(self, mock_create_engine: MagicMock) -> None:
        """Test default sample limit of 100."""
        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
        )
        query = collector._build_query()
        assert "LIMIT 100" in query

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_custom_limit(self, mock_create_engine: MagicMock) -> None:
        """Test custom sample limit."""
        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
            sample_limit=500,
        )
        query = collector._build_query()
        assert "LIMIT 500" in query

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_limit_1(self, mock_create_engine: MagicMock) -> None:
        """Test sample limit of 1."""
        rows = [('{"id": 1}',)]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
            sample_limit=1,
        )
        result = collector.collect()
        assert result.sample_count == 1


class TestNullRowsSkipped:
    """Test that null rows are properly skipped."""

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_null_rows_skipped(self, mock_create_engine: MagicMock) -> None:
        """Test that None values in rows are skipped."""
        rows = [
            ('{"id": 1}',),
            (None,),
            ('{"id": 3}',),
            (None,),
        ]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
        )
        result = collector.collect()

        assert result.sample_count == 2
        assert result.get_field("id") is not None


class TestInvalidJsonHandling:
    """Test graceful handling of invalid JSON in column."""

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_invalid_json_skipped(self, mock_create_engine: MagicMock) -> None:
        """Test that invalid JSON rows are skipped gracefully."""
        rows = [
            ('{"id": 1}',),
            ("not valid json {{{",),
            ('{"id": 3}',),
        ]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
        )
        result = collector.collect()

        assert result.sample_count == 2

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_non_object_json_skipped(self, mock_create_engine: MagicMock) -> None:
        """Test that non-object JSON (arrays, primitives) are skipped."""
        rows = [
            ('{"id": 1}',),
            ("[1, 2, 3]",),
            ('"just a string"',),
            ("42",),
            ('{"id": 5}',),
        ]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
        )
        result = collector.collect()

        assert result.sample_count == 2

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_all_invalid_returns_empty(self, mock_create_engine: MagicMock) -> None:
        """Test that all-invalid rows result in empty resource."""
        rows = [
            ("not json",),
            ("also not json",),
        ]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
        )
        result = collector.collect()

        assert result.sample_count == 0
        assert result.fields == []


class TestConnectionErrorHandling:
    """Test connection error handling."""

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_connection_creation_error(self, mock_create_engine: MagicMock) -> None:
        """Test error raised when engine creation fails."""
        mock_create_engine.side_effect = Exception("Cannot resolve host")

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@badhost/db",
            table="events",
            column="payload",
        )

        with pytest.raises(PostgresJsonbCollectorError, match="Failed to create database connection"):
            collector.collect()

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_query_execution_error(self, mock_create_engine: MagicMock) -> None:
        """Test error raised when query execution fails."""
        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.side_effect = Exception("relation does not exist")
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="nonexistent",
            column="payload",
        )

        with pytest.raises(PostgresJsonbCollectorError, match="Failed to query"):
            collector.collect()

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_connection_refused_error(self, mock_create_engine: MagicMock) -> None:
        """Test error raised when connection is refused."""
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection refused")
        mock_create_engine.return_value = mock_engine

        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost:5433/db",
            table="events",
            column="payload",
        )

        with pytest.raises(PostgresJsonbCollectorError, match="Failed to query"):
            collector.collect()


class TestInferenceConfigIntegration:
    """Test that InferenceConfig is passed through to the inference engine."""

    @patch("driftguard.collectors.postgres_jsonb_collector.create_engine")
    def test_custom_config_used(self, mock_create_engine: MagicMock) -> None:
        """Test that custom InferenceConfig is applied."""
        rows = [
            (json.dumps({"a": {"b": {"c": {"d": {"e": "deep"}}}}}),),
        ]

        mock_engine = MagicMock()
        mock_connection = MagicMock()
        mock_connection.execute.return_value = _make_mock_result(rows)
        mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_connection)
        mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
        mock_create_engine.return_value = mock_engine

        config = InferenceConfig(max_depth=2)
        collector = PostgresJsonbCollector(
            connection_string="postgresql://user:pass@localhost/db",
            table="events",
            column="payload",
            config=config,
        )
        result = collector.collect()

        # max_depth=2 should stop at a.b, not go deeper
        assert result.get_field("a.b") is not None
        assert result.get_field("a.b.c") is None
