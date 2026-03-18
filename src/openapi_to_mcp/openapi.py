from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urljoin, urlparse

import httpx
import yaml

from .models import OperationSpec, ParameterBinding, RequestBodyBinding

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


class OpenAPIError(RuntimeError):
    """Raised when an OpenAPI document is invalid or unsupported."""


@dataclass
class BuildOptions:
    include_tags: set[str] = field(default_factory=set)
    exclude_tags: set[str] = field(default_factory=set)
    only_operation_ids: set[str] = field(default_factory=set)
    allowed_methods: set[str] = field(default_factory=set)
    name_prefix: str = ""


@dataclass
class _RefContext:
    documents: dict[str, dict[str, Any]] = field(default_factory=dict)
    timeout: float = 30.0


def load_openapi_document(source: str, timeout: float = 30.0) -> dict[str, Any]:
    """Load an OpenAPI document from a local file path or HTTP(S) URL."""
    from_url = _looks_like_url(source)
    source_canonical = source
    if from_url:
        response = httpx.get(source, timeout=timeout)
        response.raise_for_status()
        raw = response.text
    else:
        resolved_path = Path(source).expanduser().resolve()
        source_canonical = str(resolved_path)
        raw = resolved_path.read_text(encoding="utf-8")

    document = _parse_document(raw)
    if not isinstance(document, dict):
        raise OpenAPIError("OpenAPI document must be an object.")

    if "openapi" not in document and "swagger" not in document:
        raise OpenAPIError("Document does not look like OpenAPI/Swagger.")

    document["x-openapi-to-mcp-source"] = source_canonical

    return document


def build_operations(spec: dict[str, Any], options: BuildOptions | None = None) -> dict[str, OperationSpec]:
    """Extract MCP-friendly operation specs from OpenAPI paths."""
    opts = options or BuildOptions()

    include_tags = {tag.lower() for tag in opts.include_tags if tag}
    exclude_tags = {tag.lower() for tag in opts.exclude_tags if tag}
    only_operation_ids = {op_id.lower() for op_id in opts.only_operation_ids if op_id}
    allowed_methods = {method.lower() for method in opts.allowed_methods if method}

    paths = spec.get("paths") or {}
    if not isinstance(paths, dict):
        raise OpenAPIError("`paths` must be an object.")

    ref_context = _RefContext()
    spec_source = _document_source(spec)

    operations: dict[str, OperationSpec] = {}
    used_tool_names: set[str] = set()

    for raw_path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        path_parameters = _normalize_parameters(
            path_item.get("parameters"),
            spec,
            context=ref_context,
            current_source=spec_source,
        )

        for method, operation in path_item.items():
            method_lower = str(method).lower()
            if method_lower not in HTTP_METHODS:
                continue
            if allowed_methods and method_lower not in allowed_methods:
                continue
            if not isinstance(operation, dict):
                continue

            operation_resolved = _resolve_refs(
                operation,
                spec,
                context=ref_context,
                current_source=spec_source,
            )
            operation_id = str(
                operation_resolved.get("operationId")
                or _derive_operation_id(method_lower, raw_path)
            )

            if only_operation_ids and operation_id.lower() not in only_operation_ids:
                continue

            tags_raw = operation_resolved.get("tags")
            tags: set[str] = set()
            if isinstance(tags_raw, list):
                tags = {str(tag).lower() for tag in tags_raw if tag is not None}
            if include_tags and not (tags & include_tags):
                continue
            if exclude_tags and (tags & exclude_tags):
                continue

            if opts.name_prefix:
                base_tool_name = _sanitize_identifier(f"{opts.name_prefix}_{operation_id}")
            else:
                base_tool_name = _sanitize_identifier(operation_id)
            tool_name = _make_unique_name(base_tool_name, used_tool_names)

            merged_parameters = _merge_parameters(
                path_parameters,
                _normalize_parameters(
                    operation_resolved.get("parameters"),
                    spec,
                    context=ref_context,
                    current_source=spec_source,
                ),
            )

            request_body = _request_body_binding(
                operation_resolved.get("requestBody"),
                spec,
                context=ref_context,
                current_source=spec_source,
            )
            if request_body is None:
                request_body = _legacy_request_body_binding(
                    merged_parameters,
                    consumes=operation_resolved.get("consumes") or spec.get("consumes"),
                    spec=spec,
                    context=ref_context,
                    current_source=spec_source,
                )

            non_body_parameters = [
                param for param in merged_parameters if str(param.get("in") or "").lower() != "body"
            ]
            bindings = _parameter_bindings_from_openapi(non_body_parameters)
            input_schema = _build_tool_input_schema(bindings, request_body)

            summary = str(operation_resolved.get("summary") or operation_id)
            description = str(
                operation_resolved.get("description")
                or operation_resolved.get("summary")
                or f"Call {method_lower.upper()} {raw_path}"
            )

            operations[tool_name] = OperationSpec(
                tool_name=tool_name,
                operation_id=operation_id,
                method=method_lower.upper(),
                path=str(raw_path),
                summary=summary,
                description=description,
                parameters=bindings,
                request_body=request_body,
                input_schema=input_schema,
                security=operation_resolved.get("security"),
            )

    return operations


def pick_base_url(spec: dict[str, Any], override: str | None = None) -> str:
    if override:
        return override

    base = ""
    servers = spec.get("servers")
    if isinstance(servers, list) and servers:
        first = servers[0]
        if isinstance(first, dict):
            base = _expand_server_url(first)

    if not base:
        host = spec.get("host")
        if not host:
            return ""
        scheme = "https"
        schemes = spec.get("schemes")
        if isinstance(schemes, list) and schemes:
            scheme = str(schemes[0])
        base_path = str(spec.get("basePath") or "")
        base = f"{scheme}://{host}{base_path}"

    source = spec.get("x-openapi-to-mcp-source")
    if not isinstance(source, str) or not source.startswith(("http://", "https://")):
        return base

    parsed_source = urlparse(source)
    if not parsed_source.scheme or not parsed_source.netloc:
        return base

    if base.startswith("/"):
        return f"{parsed_source.scheme}://{parsed_source.netloc}{base}"
    if base.startswith("./") or base.startswith("../"):
        return urljoin(source, base)
    return base


def extract_security_schemes(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    ref_context = _RefContext()
    spec_source = _document_source(spec)

    components = spec.get("components") or {}
    if not isinstance(components, dict):
        components = {}

    schemes = components.get("securitySchemes") or {}
    if isinstance(schemes, dict):
        return {
            name: _resolve_refs(schema, spec, context=ref_context, current_source=spec_source)
            for name, schema in schemes.items()
            if isinstance(schema, dict)
        }

    # Swagger 2 fallback
    legacy = spec.get("securityDefinitions") or {}
    if isinstance(legacy, dict):
        return {
            name: _resolve_refs(schema, spec, context=ref_context, current_source=spec_source)
            for name, schema in legacy.items()
            if isinstance(schema, dict)
        }

    return {}


def _parse_document(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    try:
        return yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise OpenAPIError(f"Failed to parse OpenAPI document: {exc}") from exc


def _looks_like_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _document_source(document: dict[str, Any]) -> str | None:
    source = document.get("x-openapi-to-mcp-source")
    if isinstance(source, str) and source:
        return source
    return None


def _expand_server_url(server: dict[str, Any]) -> str:
    url = str(server.get("url") or "")
    variables = server.get("variables") or {}
    if not isinstance(variables, dict):
        return url

    for name, var_def in variables.items():
        if not isinstance(var_def, dict):
            continue
        value = var_def.get("default")
        if value is None:
            enum_values = var_def.get("enum")
            if isinstance(enum_values, list) and enum_values:
                value = enum_values[0]
        if value is None:
            continue
        url = url.replace("{" + str(name) + "}", str(value))
    return url


def _resolve_refs(
    node: Any,
    root: dict[str, Any],
    max_depth: int = 24,
    *,
    context: _RefContext | None = None,
    current_source: str | None = None,
) -> Any:
    ctx = context or _RefContext()
    root_source = current_source or _document_source(root)

    def _walk(
        value: Any,
        depth: int,
        chain: tuple[str, ...],
        active_root: dict[str, Any],
        active_source: str | None,
    ) -> Any:
        if depth > max_depth:
            return value
        if isinstance(value, dict):
            if "$ref" in value:
                ref = value.get("$ref")
                if isinstance(ref, str):
                    target_root, target_source, pointer, ref_key = _resolve_ref_target(
                        ref,
                        active_root=active_root,
                        active_source=active_source,
                        context=ctx,
                    )
                    if ref_key in chain:
                        return value

                    resolved = (
                        _resolve_pointer(target_root, pointer)
                        if pointer
                        else copy.deepcopy(target_root)
                    )
                    if isinstance(resolved, dict):
                        merged = copy.deepcopy(resolved)
                        for key, subval in value.items():
                            if key == "$ref":
                                continue
                            merged[key] = subval
                    else:
                        # If ref target isn't an object, sibling fields cannot be merged meaningfully.
                        if len(value) > 1:
                            raise OpenAPIError(
                                f"Cannot merge sibling fields into non-object $ref target: {ref}"
                            )
                        merged = resolved
                    return _walk(
                        merged,
                        depth + 1,
                        chain + (ref_key,),
                        target_root,
                        target_source,
                    )
                return value
            return {
                key: _walk(subval, depth + 1, chain, active_root, active_source)
                for key, subval in value.items()
            }
        if isinstance(value, list):
            return [
                _walk(item, depth + 1, chain, active_root, active_source)
                for item in value
            ]
        return value

    return _walk(node, depth=0, chain=(), active_root=root, active_source=root_source)


def _resolve_ref_target(
    ref: str,
    *,
    active_root: dict[str, Any],
    active_source: str | None,
    context: _RefContext,
) -> tuple[dict[str, Any], str | None, str, str]:
    if ref.startswith("#"):
        source_key = active_source or "<memory>"
        return active_root, active_source, ref, f"{source_key}::{ref}"

    if "#" in ref:
        source_part, fragment = ref.split("#", 1)
        pointer = f"#{fragment}" if fragment else ""
    else:
        source_part = ref
        pointer = ""

    target_source = _resolve_source(active_source, source_part)
    target_root = _load_external_document(target_source, context=context)
    return target_root, target_source, pointer, f"{target_source}::{pointer or '#'}"


def _resolve_source(current_source: str | None, source_part: str) -> str:
    if _looks_like_url(source_part):
        return source_part

    if current_source and _looks_like_url(current_source):
        return urljoin(current_source, source_part)

    if current_source:
        base_path = Path(current_source).expanduser().resolve().parent
        return str((base_path / source_part).resolve())

    source_path = Path(source_part).expanduser()
    if source_path.is_absolute():
        return str(source_path)

    raise OpenAPIError(
        f"Relative external $ref `{source_part}` cannot be resolved without source context."
    )


def _load_external_document(source: str, *, context: _RefContext) -> dict[str, Any]:
    cached = context.documents.get(source)
    if cached is not None:
        return cached

    if _looks_like_url(source):
        response = httpx.get(source, timeout=context.timeout)
        response.raise_for_status()
        raw = response.text
    else:
        raw = Path(source).read_text(encoding="utf-8")

    parsed = _parse_document(raw)
    if not isinstance(parsed, dict):
        raise OpenAPIError(f"External $ref target must be an object: {source}")

    parsed["x-openapi-to-mcp-source"] = source
    context.documents[source] = parsed
    return parsed


def _resolve_pointer(document: dict[str, Any], pointer: str) -> Any:
    if pointer in {"", "#"}:
        return copy.deepcopy(document)
    if not pointer.startswith("#/"):
        raise OpenAPIError(f"Unsupported $ref pointer format: {pointer}")

    current: Any = document
    for token in pointer[2:].split("/"):
        token = unquote(token).replace("~1", "/").replace("~0", "~")
        if not isinstance(current, dict) or token not in current:
            raise OpenAPIError(f"Invalid $ref pointer: {pointer}")
        current = current[token]
    return copy.deepcopy(current)


def _derive_operation_id(method: str, path: str) -> str:
    method_part = method.lower()
    path_part = _sanitize_identifier(path.replace("{", "").replace("}", ""))
    return f"{method_part}_{path_part}"


def _sanitize_identifier(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_").lower()
    if not cleaned:
        cleaned = "tool"
    if cleaned[0].isdigit():
        cleaned = f"op_{cleaned}"
    return cleaned


def _make_unique_name(base: str, used: set[str]) -> str:
    candidate = base
    idx = 2
    while candidate in used:
        candidate = f"{base}_{idx}"
        idx += 1
    used.add(candidate)
    return candidate


def _normalize_parameters(
    raw_parameters: Any,
    spec: dict[str, Any],
    *,
    context: _RefContext | None = None,
    current_source: str | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(raw_parameters, list):
        return []

    out: list[dict[str, Any]] = []
    for param in raw_parameters:
        if not isinstance(param, dict):
            continue
        resolved = _resolve_refs(
            param,
            spec,
            context=context,
            current_source=current_source,
        )
        if isinstance(resolved, dict):
            out.append(resolved)
    return out


def _merge_parameters(path_level: list[dict[str, Any]], operation_level: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for param in path_level:
        key = (str(param.get("name") or ""), str(param.get("in") or ""))
        by_key[key] = param

    for param in operation_level:
        key = (str(param.get("name") or ""), str(param.get("in") or ""))
        by_key[key] = param

    return list(by_key.values())


def _parameter_bindings_from_openapi(parameters: list[dict[str, Any]]) -> list[ParameterBinding]:
    bindings: list[ParameterBinding] = []
    used_names: set[str] = set()

    for param in parameters:
        location = str(param.get("in") or "").lower()
        if location not in {"path", "query", "header", "cookie"}:
            continue

        source_name = str(param.get("name") or "")
        if not source_name:
            continue

        base_name = _sanitize_identifier(source_name)
        arg_name = base_name
        if arg_name in used_names:
            arg_name = _sanitize_identifier(f"{base_name}_{location}")
        arg_name = _make_unique_name(arg_name, used_names)

        schema = param.get("schema")
        if not isinstance(schema, dict):
            schema = _schema_from_legacy_openapi_v2(param)
        if not isinstance(schema, dict):
            schema = {"type": "string"}

        schema = copy.deepcopy(schema)
        description = param.get("description")
        if isinstance(description, str) and description and "description" not in schema:
            schema["description"] = description

        bindings.append(
            ParameterBinding(
                arg_name=arg_name,
                source_name=source_name,
                location=location,
                required=bool(param.get("required") or location == "path"),
                schema=schema,
                description=description if isinstance(description, str) else None,
            )
        )

    return bindings


def _schema_from_legacy_openapi_v2(param: dict[str, Any]) -> dict[str, Any] | None:
    if "type" not in param and "items" not in param:
        return None

    schema: dict[str, Any] = {}
    for key in ("type", "format", "items", "enum", "minimum", "maximum", "default"):
        if key in param:
            schema[key] = param[key]
    if not schema:
        return None
    return schema


def _request_body_binding(
    raw_body: Any,
    spec: dict[str, Any],
    *,
    context: _RefContext | None = None,
    current_source: str | None = None,
) -> RequestBodyBinding | None:
    if not isinstance(raw_body, dict):
        return None

    body = _resolve_refs(
        raw_body,
        spec,
        context=context,
        current_source=current_source,
    )
    if not isinstance(body, dict):
        return None

    content = body.get("content")
    if not isinstance(content, dict) or not content:
        # Swagger 2 body parameter style not handled here because it is represented as normal param.
        return None

    content_type, media = _pick_content_type(content)
    schema: dict[str, Any] = {"type": "object"}
    if isinstance(media, dict) and isinstance(media.get("schema"), dict):
        schema = _resolve_refs(
            media["schema"],
            spec,
            context=context,
            current_source=current_source,
        )

    description = body.get("description")
    if isinstance(description, str) and description and isinstance(schema, dict) and "description" not in schema:
        schema = copy.deepcopy(schema)
        schema["description"] = description

    return RequestBodyBinding(
        arg_name="body",
        required=bool(body.get("required")),
        content_type=content_type,
        schema=schema if isinstance(schema, dict) else {"type": "object"},
        description=description if isinstance(description, str) else None,
    )


def _legacy_request_body_binding(
    parameters: list[dict[str, Any]],
    *,
    consumes: Any,
    spec: dict[str, Any],
    context: _RefContext | None = None,
    current_source: str | None = None,
) -> RequestBodyBinding | None:
    body_param: dict[str, Any] | None = None
    for param in parameters:
        if str(param.get("in") or "").lower() == "body":
            body_param = param
            break

    if not body_param:
        return None

    resolved = _resolve_refs(
        body_param,
        spec,
        context=context,
        current_source=current_source,
    )
    if not isinstance(resolved, dict):
        return None

    schema = resolved.get("schema")
    if not isinstance(schema, dict):
        schema = {"type": "object"}
    else:
        schema = _resolve_refs(
            schema,
            spec,
            context=context,
            current_source=current_source,
        )

    content_type = _pick_legacy_content_type(consumes)
    description = resolved.get("description")
    if isinstance(description, str) and description and "description" not in schema:
        schema = copy.deepcopy(schema)
        schema["description"] = description

    return RequestBodyBinding(
        arg_name="body",
        required=bool(resolved.get("required")),
        content_type=content_type,
        schema=schema if isinstance(schema, dict) else {"type": "object"},
        description=description if isinstance(description, str) else None,
    )


def _pick_content_type(content: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    preferred = [
        "application/json",
        "application/*+json",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
    ]

    for candidate in preferred:
        if candidate in content and isinstance(content[candidate], dict):
            return candidate, content[candidate]

    for key, val in content.items():
        if isinstance(val, dict):
            return str(key), val

    return "application/json", {}


def _pick_legacy_content_type(consumes: Any) -> str:
    if isinstance(consumes, list):
        for value in consumes:
            value_str = str(value).strip()
            if value_str:
                return value_str
    return "application/json"


def _build_tool_input_schema(
    parameters: list[ParameterBinding],
    request_body: RequestBodyBinding | None,
) -> dict[str, Any]:
    properties: dict[str, Any] = {}
    required: list[str] = []

    for binding in parameters:
        schema = copy.deepcopy(binding.schema)
        if not isinstance(schema, dict):
            schema = {"type": "string"}
        properties[binding.arg_name] = schema
        if binding.required:
            required.append(binding.arg_name)

    if request_body:
        body_schema = copy.deepcopy(request_body.schema)
        if not isinstance(body_schema, dict):
            body_schema = {"type": "object"}
        properties[request_body.arg_name] = body_schema
        if request_body.required:
            required.append(request_body.arg_name)

    tool_schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }

    if required:
        tool_schema["required"] = sorted(set(required))

    return tool_schema
