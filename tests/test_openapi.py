from pathlib import Path

from openapi_to_mcp.openapi import BuildOptions, build_operations, load_openapi_document, pick_base_url


def test_load_and_build_operations_from_example() -> None:
    source = Path("examples/store.yaml")
    spec = load_openapi_document(str(source))
    operations = build_operations(spec)

    assert len(operations) == 4
    assert "listproducts" in operations
    assert "getorder" in operations
    assert "createorder" in operations
    assert "internalhealth" in operations

    create_order = operations["createorder"]
    assert create_order.request_body is not None
    assert "body" in create_order.input_schema["properties"]


def test_pick_base_url_from_servers() -> None:
    source = Path("examples/store.yaml")
    spec = load_openapi_document(str(source))

    assert pick_base_url(spec) == "https://api.example.com/v1"


def test_pick_base_url_resolves_remote_relative_servers() -> None:
    spec = {
        "openapi": "3.0.3",
        "servers": [{"url": "/api/v3"}],
        "x-openapi-to-mcp-source": "https://petstore3.swagger.io/api/v3/openapi.json",
    }
    assert pick_base_url(spec) == "https://petstore3.swagger.io/api/v3"


def test_build_operations_filters_by_tag_method_and_prefix() -> None:
    source = Path("examples/store.yaml")
    spec = load_openapi_document(str(source))

    options = BuildOptions(
        include_tags={"orders"},
        exclude_tags={"internal"},
        allowed_methods={"get"},
        name_prefix="shop",
    )
    operations = build_operations(spec, options=options)

    assert list(operations.keys()) == ["shop_getorder"]
    assert operations["shop_getorder"].path == "/orders/{id}"


def test_build_operations_resolves_external_file_refs(tmp_path: Path) -> None:
    schemas_file = tmp_path / "schemas.yaml"
    schemas_file.write_text(
        """
OrderCreate:
  type: object
  required: [item]
  properties:
    item:
      $ref: '#/Item'
Item:
  type: object
  required: [id]
  properties:
    id:
      type: string
""".strip(),
        encoding="utf-8",
    )

    spec_file = tmp_path / "api.yaml"
    spec_file.write_text(
        """
openapi: 3.0.3
info:
  title: External Ref API
  version: 1.0.0
servers:
  - url: https://api.example.com
paths:
  /orders:
    post:
      operationId: createOrder
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: ./schemas.yaml#/OrderCreate
      responses:
        '201':
          description: Created
""".strip(),
        encoding="utf-8",
    )

    spec = load_openapi_document(str(spec_file))
    operations = build_operations(spec)

    create_order = operations["createorder"]
    body_schema = create_order.input_schema["properties"]["body"]
    assert "item" in body_schema["properties"]
    assert body_schema["properties"]["item"]["properties"]["id"]["type"] == "string"


def test_build_operations_supports_swagger2_body_parameters() -> None:
    spec = {
        "swagger": "2.0",
        "info": {"title": "Legacy API", "version": "1.0.0"},
        "host": "api.example.com",
        "schemes": ["https"],
        "basePath": "/v1",
        "paths": {
            "/orders": {
                "post": {
                    "operationId": "createOrder",
                    "consumes": ["application/json"],
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "required": True,
                            "schema": {
                                "type": "object",
                                "required": ["product_id"],
                                "properties": {"product_id": {"type": "string"}},
                            },
                        }
                    ],
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
    }
    operations = build_operations(spec)
    create_order = operations["createorder"]

    assert create_order.request_body is not None
    assert create_order.request_body.content_type == "application/json"
    assert "body" in create_order.input_schema["required"]
    assert create_order.input_schema["properties"]["body"]["properties"]["product_id"]["type"] == "string"


def test_examples_external_ref_and_swagger2_files() -> None:
    external_spec = load_openapi_document("examples/external-ref/api.yaml")
    external_ops = build_operations(external_spec)
    assert "createorder" in external_ops

    swagger2_spec = load_openapi_document("examples/swagger2.yaml")
    swagger2_ops = build_operations(swagger2_spec)
    assert "createorder" in swagger2_ops
