from __future__ import annotations

import httpx
import pytest

from openapi_to_mcp.openapi import build_operations, load_openapi_document
from openapi_to_mcp.runtime import OpenAPIMCPRuntime, RuntimeConfig


@pytest.mark.asyncio
async def test_runtime_maps_arguments_into_http_request(monkeypatch: pytest.MonkeyPatch) -> None:
    spec = load_openapi_document("examples/store.yaml")
    operations = build_operations(spec)
    runtime = OpenAPIMCPRuntime(
        openapi_spec=spec,
        operations=operations,
        config=RuntimeConfig(server_name="test-mcp", server_version="0.1.0", base_url="https://api.test.local/v1"),
    )

    recorded: dict[str, object] = {}

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "FakeAsyncClient":
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

        async def request(self, method: str, url: str, **kwargs):
            recorded["method"] = method
            recorded["url"] = url
            recorded["kwargs"] = kwargs
            req = httpx.Request(method=method, url=url, params=kwargs.get("params"), headers=kwargs.get("headers"))
            return httpx.Response(
                status_code=200,
                json={"received": True},
                request=req,
                headers={"content-type": "application/json"},
            )

    monkeypatch.setattr("openapi_to_mcp.runtime.httpx.AsyncClient", FakeAsyncClient)

    result = await runtime.call_operation("getorder", {"id": "order-123"})

    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["status"] == 200
    assert recorded["method"] == "GET"
    assert recorded["url"] == "https://api.test.local/v1/orders/order-123"


@pytest.mark.asyncio
async def test_runtime_returns_error_for_missing_required_argument() -> None:
    spec = load_openapi_document("examples/store.yaml")
    operations = build_operations(spec)
    runtime = OpenAPIMCPRuntime(
        openapi_spec=spec,
        operations=operations,
        config=RuntimeConfig(server_name="test-mcp", server_version="0.1.0", base_url="https://api.test.local/v1"),
    )

    result = await runtime.call_operation("getorder", {})

    assert result.isError is True
    assert result.structuredContent is not None
    assert "Missing required argument" in result.structuredContent["error"]
