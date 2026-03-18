from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AppConfig:
    base_url: str | None = None
    timeout_seconds: float | None = None
    name_prefix: str = ""
    include_tags: set[str] = field(default_factory=set)
    exclude_tags: set[str] = field(default_factory=set)
    only_operation_ids: set[str] = field(default_factory=set)
    allowed_methods: set[str] = field(default_factory=set)


def load_app_config(path: str) -> AppConfig:
    data = _load_document(path)
    if not isinstance(data, dict):
        raise ValueError("Config file must be a YAML/JSON object.")

    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        runtime = {}

    filters = data.get("filters")
    if not isinstance(filters, dict):
        filters = {}

    naming = data.get("naming")
    if not isinstance(naming, dict):
        naming = {}

    base_url = _as_optional_str(runtime.get("base_url") if "base_url" in runtime else data.get("base_url"))

    timeout_raw = runtime.get("timeout_seconds")
    if timeout_raw is None:
        timeout_raw = data.get("timeout_seconds")
    timeout_seconds = _as_optional_float(timeout_raw)

    prefix = _as_optional_str(naming.get("prefix") if "prefix" in naming else data.get("name_prefix")) or ""

    include_tags = _as_str_set(filters.get("include_tags") if "include_tags" in filters else data.get("include_tags"))
    exclude_tags = _as_str_set(filters.get("exclude_tags") if "exclude_tags" in filters else data.get("exclude_tags"))
    only_ops = _as_str_set(filters.get("operation_ids") if "operation_ids" in filters else data.get("operation_ids"))
    methods = _as_str_set(filters.get("methods") if "methods" in filters else data.get("methods"))

    return AppConfig(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        name_prefix=prefix,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        only_operation_ids=only_ops,
        allowed_methods=methods,
    )


def parse_csv_set(value: str) -> set[str]:
    return {chunk.strip() for chunk in value.split(",") if chunk.strip()}


def render_template_config() -> str:
    return """# openapi-to-mcp config
# Save as openapi-to-mcp.yaml and run:
# openapi-to-mcp run ./openapi.yaml --config openapi-to-mcp.yaml

runtime:
  # Optional override when spec has missing/relative servers URL.
  base_url: https://api.example.com
  timeout_seconds: 30

naming:
  # Prefix all generated tool names.
  prefix: shop

filters:
  # Keep operations that have at least one of these tags.
  include_tags: [products, orders]

  # Drop operations that match these tags.
  exclude_tags: [internal]

  # Keep only specific operationIds (case-insensitive).
  operation_ids: []

  # Keep only these HTTP methods.
  methods: [get, post]
"""


def _load_document(path: str) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    return yaml.safe_load(text)


def _as_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    value_str = str(value).strip()
    return value_str or None


def _as_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    value_str = str(value).strip()
    if not value_str:
        return None
    return float(value_str)


def _as_str_set(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(v).strip() for v in value if str(v).strip()}
    if isinstance(value, str):
        return parse_csv_set(value)
    raise ValueError(f"Expected string or list for set-like config value, got {type(value).__name__}")
