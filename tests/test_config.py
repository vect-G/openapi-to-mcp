from __future__ import annotations

from pathlib import Path

from openapi_to_mcp.config import load_app_config, parse_csv_set, render_template_config


def test_parse_csv_set() -> None:
    assert parse_csv_set("a,b,c") == {"a", "b", "c"}
    assert parse_csv_set("  get, post ,, ") == {"get", "post"}


def test_load_app_config_from_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "openapi-to-mcp.yaml"
    config_file.write_text(
        """
runtime:
  base_url: https://api.acme.dev
  timeout_seconds: 42
naming:
  prefix: acme
filters:
  include_tags: [orders, products]
  exclude_tags: [internal]
  operation_ids: [getOrder]
  methods: [get]
""".strip(),
        encoding="utf-8",
    )

    cfg = load_app_config(str(config_file))

    assert cfg.base_url == "https://api.acme.dev"
    assert cfg.timeout_seconds == 42
    assert cfg.name_prefix == "acme"
    assert cfg.include_tags == {"orders", "products"}
    assert cfg.exclude_tags == {"internal"}
    assert cfg.only_operation_ids == {"getOrder"}
    assert cfg.allowed_methods == {"get"}


def test_template_config_contains_expected_sections() -> None:
    text = render_template_config()
    assert "runtime:" in text
    assert "naming:" in text
    assert "filters:" in text
