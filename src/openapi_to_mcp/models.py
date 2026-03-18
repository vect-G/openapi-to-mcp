from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ParameterLocation = Literal["path", "query", "header", "cookie"]


@dataclass
class ParameterBinding:
    arg_name: str
    source_name: str
    location: ParameterLocation
    required: bool = False
    schema: dict[str, Any] = field(default_factory=lambda: {"type": "string"})
    description: str | None = None


@dataclass
class RequestBodyBinding:
    arg_name: str = "body"
    required: bool = False
    content_type: str = "application/json"
    schema: dict[str, Any] = field(default_factory=lambda: {"type": "object"})
    description: str | None = None


@dataclass
class OperationSpec:
    tool_name: str
    operation_id: str
    method: str
    path: str
    summary: str
    description: str
    parameters: list[ParameterBinding] = field(default_factory=list)
    request_body: RequestBodyBinding | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    security: list[dict[str, list[str]]] | None = None
