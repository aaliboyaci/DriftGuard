"""Tests for OpenAPI deep extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from driftguard.collectors.openapi_extractor import (
    extract_from_dict,
    extract_openapi_contract,
)
from driftguard.schema.openapi_models import OpenApiContract

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
PETSTORE = FIXTURE_DIR / "petstore_full.yaml"


@pytest.fixture
def contract() -> OpenApiContract:
    return extract_openapi_contract(PETSTORE)


class TestContractMetadata:
    def test_title(self, contract: OpenApiContract) -> None:
        assert contract.title == "Pet Store API"

    def test_version(self, contract: OpenApiContract) -> None:
        assert contract.version == "1.0.0"


class TestPathExtraction:
    def test_path_count(self, contract: OpenApiContract) -> None:
        assert len(contract.paths) == 3

    def test_path_names(self, contract: OpenApiContract) -> None:
        names = contract.path_names
        assert "/pets" in names
        assert "/pets/{petId}" in names
        assert "/owners" in names

    def test_get_path(self, contract: OpenApiContract) -> None:
        p = contract.get_path("/pets")
        assert p is not None
        assert p.path == "/pets"

    def test_get_path_missing(self, contract: OpenApiContract) -> None:
        assert contract.get_path("/nonexistent") is None


class TestMethodExtraction:
    def test_pets_has_get_and_post(self, contract: OpenApiContract) -> None:
        p = contract.get_path("/pets")
        assert p is not None
        methods = {op.method for op in p.operations}
        assert methods == {"get", "post"}

    def test_pets_petid_has_get_put_delete(self, contract: OpenApiContract) -> None:
        p = contract.get_path("/pets/{petId}")
        assert p is not None
        methods = {op.method for op in p.operations}
        assert methods == {"get", "put", "delete"}

    def test_owners_has_get(self, contract: OpenApiContract) -> None:
        p = contract.get_path("/owners")
        assert p is not None
        methods = {op.method for op in p.operations}
        assert methods == {"get"}

    def test_operation_count(self, contract: OpenApiContract) -> None:
        assert contract.operation_count == 6

    def test_get_operation(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        assert op.operation_id == "listPets"

    def test_get_operation_missing(self, contract: OpenApiContract) -> None:
        assert contract.get_operation("/pets", "delete") is None
        assert contract.get_operation("/nonexistent", "get") is None

    def test_operation_id(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "post")
        assert op is not None
        assert op.operation_id == "createPet"

    def test_operation_summary(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        assert op.summary == "List all pets"

    def test_deprecated_flag(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "put")
        assert op is not None
        assert op.deprecated is True

        op2 = contract.get_operation("/pets", "get")
        assert op2 is not None
        assert op2.deprecated is False

    def test_tags(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        assert op.tags == ["pets"]


class TestQueryParameterExtraction:
    def test_list_pets_query_params(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        query_params = [p for p in op.parameters if p.location == "query"]
        assert len(query_params) == 2
        names = {p.name for p in query_params}
        assert names == {"limit", "status"}

    def test_limit_param_type(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        limit = next(p for p in op.parameters if p.name == "limit")
        assert limit.param_type == "integer"
        assert limit.required is False
        assert limit.default == 20

    def test_status_param_enum(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        status = next(p for p in op.parameters if p.name == "status")
        assert status.param_type == "string"
        assert status.enum_values == ["available", "pending", "sold"]

    def test_owners_page_param(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/owners", "get")
        assert op is not None
        page = next(p for p in op.parameters if p.name == "page")
        assert page.param_type == "integer"
        assert page.default == 1


class TestPathParameterExtraction:
    def test_petid_path_param(self, contract: OpenApiContract) -> None:
        # Path-level parameter should be inherited by all operations
        op = contract.get_operation("/pets/{petId}", "get")
        assert op is not None
        path_params = [p for p in op.parameters if p.location == "path"]
        assert len(path_params) == 1
        assert path_params[0].name == "petId"
        assert path_params[0].required is True
        assert path_params[0].param_type == "integer"

    def test_path_param_inherited_by_delete(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "delete")
        assert op is not None
        path_params = [p for p in op.parameters if p.location == "path"]
        assert len(path_params) == 1
        assert path_params[0].name == "petId"


class TestHeaderParameterExtraction:
    def test_request_id_header(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        headers = [p for p in op.parameters if p.location == "header"]
        assert len(headers) == 1
        assert headers[0].name == "X-Request-Id"
        assert headers[0].required is False

    def test_confirm_header_required(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "delete")
        assert op is not None
        headers = [p for p in op.parameters if p.location == "header"]
        assert len(headers) == 1
        assert headers[0].name == "X-Confirm"
        assert headers[0].required is True


class TestRequestBodyExtraction:
    def test_create_pet_request_body(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "post")
        assert op is not None
        rb = op.request_body
        assert rb is not None
        assert rb.required is True
        assert rb.content_type == "application/json"

    def test_create_pet_request_fields(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "post")
        assert op is not None
        rb = op.request_body
        assert rb is not None
        field_names = {f.name for f in rb.fields}
        assert "name" in field_names
        assert "status" in field_names
        assert "tag" in field_names

    def test_create_pet_required_field(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "post")
        assert op is not None
        rb = op.request_body
        assert rb is not None
        name_field = next(f for f in rb.fields if f.name == "name")
        assert name_field.required is True
        status_field = next(f for f in rb.fields if f.name == "status")
        assert status_field.required is False

    def test_get_has_no_request_body(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        assert op.request_body is None

    def test_update_pet_request_body(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "put")
        assert op is not None
        rb = op.request_body
        assert rb is not None
        assert rb.required is True
        field_names = {f.name for f in rb.fields}
        assert "name" in field_names


class TestResponseExtraction:
    def test_list_pets_responses(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        status_codes = {r.status_code for r in op.responses}
        assert "200" in status_codes
        assert "400" in status_codes

    def test_list_pets_200_fields(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        resp_200 = next(r for r in op.responses if r.status_code == "200")
        # Array response -> extracts item fields
        field_names = {f.name for f in resp_200.fields}
        assert "id" in field_names
        assert "name" in field_names
        assert "status" in field_names
        assert "tag" in field_names

    def test_list_pets_200_description(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "get")
        assert op is not None
        resp_200 = next(r for r in op.responses if r.status_code == "200")
        assert resp_200.description == "A list of pets"

    def test_create_pet_201_fields(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "post")
        assert op is not None
        resp_201 = next(r for r in op.responses if r.status_code == "201")
        field_names = {f.name for f in resp_201.fields}
        assert "id" in field_names
        assert "name" in field_names

    def test_delete_204_no_fields(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "delete")
        assert op is not None
        resp_204 = next(r for r in op.responses if r.status_code == "204")
        assert resp_204.fields == []

    def test_404_no_fields(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "get")
        assert op is not None
        resp_404 = next(r for r in op.responses if r.status_code == "404")
        assert resp_404.fields == []


class TestStatusCodeExtraction:
    def test_get_pet_status_codes(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "get")
        assert op is not None
        codes = {r.status_code for r in op.responses}
        assert codes == {"200", "404"}

    def test_create_pet_status_codes(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets", "post")
        assert op is not None
        codes = {r.status_code for r in op.responses}
        assert codes == {"201", "422"}

    def test_delete_pet_status_codes(self, contract: OpenApiContract) -> None:
        op = contract.get_operation("/pets/{petId}", "delete")
        assert op is not None
        codes = {r.status_code for r in op.responses}
        assert codes == {"204", "404"}


class TestSwagger2xCompat:
    """Test Swagger 2.0 format extraction."""

    def test_swagger2_body_param(self) -> None:
        spec = {
            "swagger": "2.0",
            "info": {"title": "Legacy", "version": "1.0"},
            "paths": {
                "/users": {
                    "post": {
                        "parameters": [
                            {
                                "in": "body",
                                "name": "body",
                                "required": True,
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "age": {"type": "integer"},
                                    },
                                },
                            }
                        ],
                        "responses": {
                            "200": {"description": "OK"},
                        },
                    }
                }
            },
        }
        contract = extract_from_dict(spec)
        op = contract.get_operation("/users", "post")
        assert op is not None
        assert op.request_body is not None
        assert op.request_body.required is True
        field_names = {f.name for f in op.request_body.fields}
        assert field_names == {"name", "age"}

    def test_swagger2_response_schema(self) -> None:
        spec = {
            "swagger": "2.0",
            "info": {"title": "Legacy", "version": "1.0"},
            "definitions": {
                "User": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                }
            },
            "paths": {
                "/users": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "schema": {"$ref": "#/definitions/User"},
                            }
                        }
                    }
                }
            },
        }
        contract = extract_from_dict(spec)
        op = contract.get_operation("/users", "get")
        assert op is not None
        resp = op.responses[0]
        field_names = {f.name for f in resp.fields}
        assert field_names == {"id", "name"}

    def test_swagger2_array_response(self) -> None:
        spec = {
            "swagger": "2.0",
            "info": {"title": "Legacy", "version": "1.0"},
            "paths": {
                "/items": {
                    "get": {
                        "responses": {
                            "200": {
                                "description": "OK",
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "label": {"type": "string"},
                                        },
                                    },
                                },
                            }
                        }
                    }
                }
            },
        }
        contract = extract_from_dict(spec)
        op = contract.get_operation("/items", "get")
        assert op is not None
        resp = op.responses[0]
        field_names = {f.name for f in resp.fields}
        assert field_names == {"id", "label"}


class TestEdgeCases:
    def test_empty_spec(self) -> None:
        contract = extract_from_dict({"info": {"title": "Empty", "version": "0"}})
        assert contract.paths == []

    def test_path_with_no_operations(self) -> None:
        spec = {
            "info": {"title": "T", "version": "1"},
            "paths": {"/health": {"summary": "Health check"}},
        }
        contract = extract_from_dict(spec)
        p = contract.get_path("/health")
        assert p is not None
        assert p.operations == []

    def test_json_file(self, tmp_path: Path) -> None:
        import json

        spec = {
            "openapi": "3.0.0",
            "info": {"title": "JSON Test", "version": "1"},
            "paths": {
                "/ping": {
                    "get": {
                        "responses": {"200": {"description": "pong"}},
                    }
                }
            },
        }
        f = tmp_path / "spec.json"
        f.write_text(json.dumps(spec), encoding="utf-8")
        contract = extract_openapi_contract(f)
        assert contract.title == "JSON Test"
        assert len(contract.paths) == 1

    def test_parameter_merge_override(self) -> None:
        """Operation-level param overrides path-level with same name+location."""
        spec = {
            "info": {"title": "T", "version": "1"},
            "paths": {
                "/x": {
                    "parameters": [
                        {"name": "id", "in": "query", "required": False, "schema": {"type": "string"}},
                    ],
                    "get": {
                        "parameters": [
                            {"name": "id", "in": "query", "required": True, "schema": {"type": "integer"}},
                        ],
                        "responses": {"200": {"description": "OK"}},
                    },
                }
            },
        }
        contract = extract_from_dict(spec)
        op = contract.get_operation("/x", "get")
        assert op is not None
        id_param = next(p for p in op.parameters if p.name == "id")
        # Operation-level should win
        assert id_param.required is True
        assert id_param.param_type == "integer"

    def test_response_field_required(self, contract: OpenApiContract) -> None:
        """Verify required fields are correctly extracted from $ref responses."""
        op = contract.get_operation("/pets/{petId}", "get")
        assert op is not None
        resp = next(r for r in op.responses if r.status_code == "200")
        id_field = next(f for f in resp.fields if f.name == "id")
        assert id_field.required is True
        tag_field = next(f for f in resp.fields if f.name == "tag")
        assert tag_field.required is False
