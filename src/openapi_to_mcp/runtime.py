from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from .models import OperationSpec
from .openapi import extract_security_schemes


@dataclass
class RuntimeConfig:
    server_name: str
    server_version: str
    base_url: str
    timeout_seconds: float = 30.0
    user_agent: str = "openapi-to-mcp/0.3.1"


class OpenAPIMCPRuntime:
    def __init__(
        self,
        openapi_spec: dict[str, Any],
        operations: dict[str, OperationSpec],
        config: RuntimeConfig,
    ) -> None:
        self.openapi_spec = openapi_spec
        self.operations = operations
        self.config = config

        self.security_schemes = extract_security_schemes(openapi_spec)
        self.default_security = openapi_spec.get("security")

        self.server = Server(config.server_name)
        self._register_handlers()

    def _register_handlers(self) -> None:
        @self.server.list_tools()
        async def _list_tools(_: types.ListToolsRequest) -> list[types.Tool]:
            return [
                types.Tool(
                    name=op.tool_name,
                    title=op.summary,
                    description=op.description,
                    inputSchema=op.input_schema,
                )
                for op in self.operations.values()
            ]

        @self.server.call_tool()
        async def _call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
            return await self.call_operation(name, arguments or {})

    async def call_operation(self, tool_name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        operation = self.operations.get(tool_name)
        if not operation:
            return _error_result(f"Unknown tool `{tool_name}`")

        try:
            payload = await self._execute_http_request(operation, arguments)
        except Exception as exc:  # noqa: BLE001
            return _error_result(str(exc))

        text = json.dumps(payload, ensure_ascii=False, indent=2)
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=text)],
            structuredContent=payload,
            isError=bool(not payload.get("ok", False)),
        )

    async def _execute_http_request(self, operation: OperationSpec, arguments: dict[str, Any]) -> dict[str, Any]:
        if not self.config.base_url:
            raise RuntimeError(
                "No base URL found. Provide --base-url or define `servers` in the OpenAPI file."
            )

        path = operation.path
        query: dict[str, Any] = {}
        headers: dict[str, str] = {
            "User-Agent": self.config.user_agent,
        }
        cookies: dict[str, str] = {}
        body: Any = None

        for binding in operation.parameters:
            if binding.arg_name not in arguments:
                if binding.required:
                    raise RuntimeError(f"Missing required argument: `{binding.arg_name}`")
                continue

            value = arguments[binding.arg_name]
            if binding.location == "path":
                path = path.replace("{" + binding.source_name + "}", quote(str(value), safe=""))
            elif binding.location == "query":
                query[binding.source_name] = value
            elif binding.location == "header":
                headers[binding.source_name] = str(value)
            elif binding.location == "cookie":
                cookies[binding.source_name] = str(value)

        if operation.request_body and operation.request_body.arg_name in arguments:
            body = arguments[operation.request_body.arg_name]

        self._apply_auth(operation, headers=headers, query=query, cookies=cookies)

        url = f"{self.config.base_url.rstrip('/')}/{path.lstrip('/')}"
        request_kwargs: dict[str, Any] = {
            "params": query,
            "headers": headers,
            "cookies": cookies,
        }

        if body is not None:
            if operation.request_body and "json" in operation.request_body.content_type:
                request_kwargs["json"] = body
            elif operation.request_body and operation.request_body.content_type == "application/x-www-form-urlencoded":
                request_kwargs["data"] = body
            else:
                request_kwargs["content"] = body if isinstance(body, (bytes, str)) else json.dumps(body)
                if operation.request_body:
                    request_kwargs["headers"]["Content-Type"] = operation.request_body.content_type

        started = time.monotonic()
        timeout = httpx.Timeout(self.config.timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(operation.method, url, **request_kwargs)
        elapsed_ms = int((time.monotonic() - started) * 1000)

        parsed_body: Any
        content_type = response.headers.get("content-type", "")
        if "json" in content_type.lower():
            try:
                parsed_body = response.json()
            except json.JSONDecodeError:
                parsed_body = response.text
        else:
            parsed_body = response.text

        return {
            "ok": response.is_success,
            "status": response.status_code,
            "method": operation.method,
            "url": str(response.request.url),
            "duration_ms": elapsed_ms,
            "data": parsed_body,
        }

    def _apply_auth(
        self,
        operation: OperationSpec,
        *,
        headers: dict[str, str],
        query: dict[str, Any],
        cookies: dict[str, str],
    ) -> None:
        security_requirements = operation.security
        if security_requirements is None:
            security_requirements = self.default_security

        if not security_requirements:
            return

        missing_messages: list[str] = []

        for requirement in security_requirements:
            if not isinstance(requirement, dict):
                continue

            staged_headers = dict(headers)
            staged_query = dict(query)
            staged_cookies = dict(cookies)
            requirement_ok = True

            for scheme_name in requirement.keys():
                scheme_def = self.security_schemes.get(scheme_name)
                if not isinstance(scheme_def, dict):
                    requirement_ok = False
                    missing_messages.append(f"Unknown security scheme: {scheme_name}")
                    break

                applied = self._apply_single_scheme(
                    scheme_name,
                    scheme_def,
                    headers=staged_headers,
                    query=staged_query,
                    cookies=staged_cookies,
                )
                if not applied:
                    requirement_ok = False
                    missing_messages.append(
                        f"Missing credentials for {scheme_name}. Set OPENAPI_AUTH_{_env_suffix(scheme_name)}"
                    )
                    break

            if requirement_ok:
                headers.clear()
                headers.update(staged_headers)
                query.clear()
                query.update(staged_query)
                cookies.clear()
                cookies.update(staged_cookies)
                return

        message = "Authentication required but credentials were not found."
        if missing_messages:
            unique_messages = "; ".join(dict.fromkeys(missing_messages))
            message = f"{message} {unique_messages}"
        raise RuntimeError(message)

    def _apply_single_scheme(
        self,
        scheme_name: str,
        scheme_def: dict[str, Any],
        *,
        headers: dict[str, str],
        query: dict[str, Any],
        cookies: dict[str, str],
    ) -> bool:
        env_primary = f"OPENAPI_AUTH_{_env_suffix(scheme_name)}"
        scheme_type = str(scheme_def.get("type") or "").lower()

        if scheme_type == "apikey":
            value = os.getenv(env_primary) or os.getenv("OPENAPI_API_KEY")
            if not value:
                return False
            location = str(scheme_def.get("in") or "header").lower()
            key_name = str(scheme_def.get("name") or "X-API-Key")
            if location == "query":
                query[key_name] = value
            elif location == "cookie":
                cookies[key_name] = value
            else:
                headers[key_name] = value
            return True

        if scheme_type == "http":
            http_scheme = str(scheme_def.get("scheme") or "").lower()
            if http_scheme == "bearer":
                value = os.getenv(env_primary) or os.getenv("OPENAPI_BEARER_TOKEN")
                if not value:
                    return False
                headers["Authorization"] = f"Bearer {value}"
                return True
            if http_scheme == "basic":
                raw = os.getenv(env_primary)
                if raw and ":" in raw:
                    user, password = raw.split(":", 1)
                else:
                    user = os.getenv("OPENAPI_BASIC_USER")
                    password = os.getenv("OPENAPI_BASIC_PASS")
                if not user or not password:
                    return False
                import base64

                token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
                headers["Authorization"] = f"Basic {token}"
                return True

        if scheme_type in {"oauth2", "openidconnect"}:
            value = os.getenv(env_primary) or os.getenv("OPENAPI_BEARER_TOKEN")
            if not value:
                return False
            headers["Authorization"] = f"Bearer {value}"
            return True

        # Unsupported security scheme type.
        return False

    async def run_stdio(self) -> None:
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.config.server_name,
                    server_version=self.config.server_version,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                    instructions="OpenAPI-powered MCP server. Tools map to API operations.",
                ),
            )


def _env_suffix(name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in name.upper())


def _error_result(message: str) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=message)],
        structuredContent={"ok": False, "error": message},
        isError=True,
    )


def run_sync(runtime: OpenAPIMCPRuntime) -> None:
    asyncio.run(runtime.run_stdio())
