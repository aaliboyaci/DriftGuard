"""Tests for ORM collectors (Sequelize and Prisma)."""

from __future__ import annotations

from pathlib import Path

import pytest

from driftguard.collectors.orm.prisma_collector import PrismaCollector
from driftguard.collectors.orm.sequelize_collector import SequelizeCollector
from driftguard.schema.models import SourceType

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "orm"


class TestSequelizeCollector:
    """Tests for the Sequelize model collector."""

    @pytest.fixture
    def resources(self):
        collector = SequelizeCollector(FIXTURES_DIR / "sequelize_user.js")
        return collector.collect()

    def test_model_name_in_metadata(self, resources):
        assert len(resources) == 1
        assert resources[0].metadata["model_name"] == "User"

    def test_table_name(self, resources):
        assert resources[0].name == "users"

    def test_source_type(self, resources):
        assert resources[0].source_type == SourceType.SEQUELIZE

    def test_field_count(self, resources):
        assert len(resources[0].fields) == 7

    def test_field_names(self, resources):
        names = {f.name for f in resources[0].fields}
        expected = {"id", "email", "name", "role", "isActive", "metadata", "createdAt"}
        assert names == expected

    def test_integer_type(self, resources):
        field = resources[0].get_field("id")
        assert field is not None
        assert field.field_type == "integer"

    def test_string_type(self, resources):
        field = resources[0].get_field("email")
        assert field is not None
        assert field.field_type == "string"

    def test_boolean_type(self, resources):
        field = resources[0].get_field("isActive")
        assert field is not None
        assert field.field_type == "boolean"

    def test_jsonb_type(self, resources):
        field = resources[0].get_field("metadata")
        assert field is not None
        assert field.field_type == "object"

    def test_date_type(self, resources):
        field = resources[0].get_field("createdAt")
        assert field is not None
        assert field.field_type == "string(date)"

    def test_enum_type(self, resources):
        field = resources[0].get_field("role")
        assert field is not None
        assert field.field_type == "string"

    def test_nullable_false(self, resources):
        field = resources[0].get_field("email")
        assert field is not None
        assert field.nullable is False

    def test_nullable_true(self, resources):
        field = resources[0].get_field("metadata")
        assert field is not None
        assert field.nullable is True

    def test_primary_key(self, resources):
        field = resources[0].get_field("id")
        assert field is not None
        assert field.constraints is not None
        assert field.constraints.primary_key is True

    def test_unique(self, resources):
        field = resources[0].get_field("email")
        assert field is not None
        assert field.constraints is not None
        assert field.constraints.unique is True

    def test_default_value_string(self, resources):
        field = resources[0].get_field("role")
        assert field is not None
        assert field.default == "user"

    def test_default_value_boolean(self, resources):
        field = resources[0].get_field("isActive")
        assert field is not None
        assert field.default == "true"

    def test_enum_values(self, resources):
        field = resources[0].get_field("role")
        assert field is not None
        assert field.enum_values == ["admin", "user", "guest"]

    def test_collector_name(self):
        collector = SequelizeCollector(FIXTURES_DIR / "sequelize_user.js")
        assert collector.name == "sequelize"


class TestPrismaCollector:
    """Tests for the Prisma schema collector."""

    @pytest.fixture
    def resources(self):
        collector = PrismaCollector(FIXTURES_DIR / "schema.prisma")
        return collector.collect()

    def test_model_count(self, resources):
        assert len(resources) == 2

    def test_model_names(self, resources):
        names = {r.name for r in resources}
        assert names == {"User", "Post"}

    def test_source_type(self, resources):
        for r in resources:
            assert r.source_type == SourceType.PRISMA

    def test_user_field_names(self, resources):
        user = next(r for r in resources if r.name == "User")
        names = {f.name for f in user.fields}
        expected = {"id", "email", "name", "role", "isActive", "metadata", "createdAt"}
        assert names == expected

    def test_post_field_names(self, resources):
        post = next(r for r in resources if r.name == "Post")
        names = {f.name for f in post.fields}
        expected = {"id", "title", "content", "published", "authorId"}
        assert names == expected

    def test_integer_type(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("id")
        assert field is not None
        assert field.field_type == "integer"

    def test_string_type(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("email")
        assert field is not None
        assert field.field_type == "string"

    def test_boolean_type(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("isActive")
        assert field is not None
        assert field.field_type == "boolean"

    def test_json_type(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("metadata")
        assert field is not None
        assert field.field_type == "object"

    def test_datetime_type(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("createdAt")
        assert field is not None
        assert field.field_type == "string(datetime)"

    def test_nullable_optional(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("metadata")
        assert field is not None
        assert field.nullable is True

    def test_nullable_required(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("email")
        assert field is not None
        assert field.nullable is False

    def test_primary_key(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("id")
        assert field is not None
        assert field.constraints is not None
        assert field.constraints.primary_key is True

    def test_unique(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("email")
        assert field is not None
        assert field.constraints is not None
        assert field.constraints.unique is True

    def test_default_autoincrement(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("id")
        assert field is not None
        assert field.default == "autoincrement()"

    def test_default_string(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("role")
        assert field is not None
        assert field.default == "user"

    def test_default_boolean(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("isActive")
        assert field is not None
        assert field.default == "true"

    def test_default_now(self, resources):
        user = next(r for r in resources if r.name == "User")
        field = user.get_field("createdAt")
        assert field is not None
        assert field.default == "now()"

    def test_relation_field_excluded(self, resources):
        """Relation fields (like posts Post[]) should not appear as fields."""
        user = next(r for r in resources if r.name == "User")
        assert user.get_field("posts") is None

    def test_relation_object_excluded(self, resources):
        """Relation object fields (like author User) should not appear."""
        post = next(r for r in resources if r.name == "Post")
        assert post.get_field("author") is None

    def test_collector_name(self):
        collector = PrismaCollector(FIXTURES_DIR / "schema.prisma")
        assert collector.name == "prisma"
