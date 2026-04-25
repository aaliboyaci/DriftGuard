"""Tests for the SQLite collector."""

import sqlite3

import pytest

from driftguard.collectors.sqlite_collector import SqliteCollector
from driftguard.schema.models import SourceType


@pytest.fixture()
def sample_db(tmp_path: pytest.TempPathFactory) -> str:  # type: ignore[type-arg]
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            age INTEGER,
            active BOOLEAN DEFAULT 1
        )
    """)
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            total REAL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()
    return db_path


class TestSqliteCollector:
    def test_collects_tables(self, sample_db: str) -> None:
        collector = SqliteCollector(sample_db)
        resources = collector.collect()
        names = {r.name for r in resources}
        assert "users" in names
        assert "orders" in names

    def test_field_types(self, sample_db: str) -> None:
        collector = SqliteCollector(sample_db)
        resources = collector.collect()
        users = next(r for r in resources if r.name == "users")
        id_field = users.get_field("id")
        assert id_field is not None
        assert id_field.field_type == "integer"
        name_field = users.get_field("name")
        assert name_field is not None
        assert name_field.field_type == "string"

    def test_source_type(self, sample_db: str) -> None:
        collector = SqliteCollector(sample_db)
        resources = collector.collect()
        assert all(r.source_type == SourceType.SQLITE for r in resources)

    def test_primary_key_detected(self, sample_db: str) -> None:
        collector = SqliteCollector(sample_db)
        resources = collector.collect()
        users = next(r for r in resources if r.name == "users")
        id_field = users.get_field("id")
        assert id_field is not None
        assert id_field.constraints is not None
        assert id_field.constraints.primary_key is True

    def test_collector_name(self, sample_db: str) -> None:
        collector = SqliteCollector(sample_db)
        assert "sqlite" in collector.name
