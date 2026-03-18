from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .config import AppConfig, load_app_config, parse_csv_set, render_template_config
from .models import OperationSpec
from .openapi import BuildOptions, OpenAPIError, build_operations, load_openapi_document, pick_base_url
from .runtime import OpenAPIMCPRuntime, RuntimeConfig, run_sync

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Turn any OpenAPI/Swagger document into a runnable MCP server.",
)

console = Console(stderr=True)


@app.command()
def run(
    source: str = typer.Argument(..., help="Path or URL of OpenAPI/Swagger file"),
    name: str = typer.Option("openapi-mcp", "--name", help="MCP server name"),
    config: str = typer.Option("", "--config", help="Path to openapi-to-mcp YAML/JSON config"),
    base_url: str = typer.Option("", "--base-url", help="Override API base URL from spec servers"),
    timeout: float = typer.Option(-1.0, "--timeout", help="HTTP timeout in seconds (default: 30 or config)"),
    include_tags: str = typer.Option("", "--include-tags", help="Comma-separated tags to keep"),
    exclude_tags: str = typer.Option("", "--exclude-tags", help="Comma-separated tags to drop"),
    only_operations: str = typer.Option(
        "", "--only-operations", help="Comma-separated operationIds to include"
    ),
    methods: str = typer.Option("", "--methods", help="Comma-separated HTTP methods to include"),
    prefix: str = typer.Option("", "--prefix", help="Prefix generated tool names"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Print generated tools and exit"),
) -> None:
    """Generate tools from OpenAPI and run MCP server over stdio."""
    cfg = _load_config_safe(config)

    try:
        spec = load_openapi_document(source)
    except (OpenAPIError, OSError, ValueError) as exc:
        raise typer.Exit(code=_print_error(str(exc))) from exc

    build_opts = _build_options_from_inputs(
        cfg=cfg,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        only_operations=only_operations,
        methods=methods,
        prefix=prefix,
    )

    try:
        operations = build_operations(spec, options=build_opts)
    except (OpenAPIError, ValueError) as exc:
        raise typer.Exit(code=_print_error(str(exc))) from exc

    if not operations:
        raise typer.Exit(code=_print_error("No operations matched after filtering."))

    base_url_effective = base_url or cfg.base_url or pick_base_url(spec)

    if dry_run:
        _print_operation_table(name=name, source=source, base_url=base_url_effective, operations=operations)
        return

    if not base_url_effective:
        raise typer.Exit(
            code=_print_error(
                "No base URL detected. Set `servers` in your spec, config runtime.base_url, or pass --base-url."
            )
        )

    timeout_effective = timeout if timeout >= 0 else (cfg.timeout_seconds if cfg.timeout_seconds else 30.0)

    console.print(
        f"[bold green]openapi-to-mcp[/] launching [cyan]{name}[/] with "
        f"[yellow]{len(operations)}[/] tools"
    )
    console.print(f"source: {source}")
    console.print(f"base URL: {base_url_effective}")
    console.print(f"timeout: {timeout_effective}s")
    console.print("transport: stdio")

    runtime = OpenAPIMCPRuntime(
        openapi_spec=spec,
        operations=operations,
        config=RuntimeConfig(
            server_name=name,
            server_version=__version__,
            base_url=base_url_effective,
            timeout_seconds=timeout_effective,
        ),
    )
    run_sync(runtime)


@app.command("list")
def list_tools(
    source: str = typer.Argument(..., help="Path or URL of OpenAPI/Swagger file"),
    config: str = typer.Option("", "--config", help="Path to openapi-to-mcp YAML/JSON config"),
    base_url: str = typer.Option("", "--base-url", help="Override base URL shown in output"),
    include_tags: str = typer.Option("", "--include-tags", help="Comma-separated tags to keep"),
    exclude_tags: str = typer.Option("", "--exclude-tags", help="Comma-separated tags to drop"),
    only_operations: str = typer.Option(
        "", "--only-operations", help="Comma-separated operationIds to include"
    ),
    methods: str = typer.Option("", "--methods", help="Comma-separated HTTP methods to include"),
    prefix: str = typer.Option("", "--prefix", help="Prefix generated tool names"),
    output_json: bool = typer.Option(False, "--json", help="Print machine-readable JSON"),
) -> None:
    """List generated tool names and descriptions without running MCP."""
    cfg = _load_config_safe(config)

    try:
        spec = load_openapi_document(source)
    except (OpenAPIError, OSError, ValueError) as exc:
        raise typer.Exit(code=_print_error(str(exc))) from exc

    build_opts = _build_options_from_inputs(
        cfg=cfg,
        include_tags=include_tags,
        exclude_tags=exclude_tags,
        only_operations=only_operations,
        methods=methods,
        prefix=prefix,
    )

    operations = build_operations(spec, options=build_opts)
    resolved_base_url = base_url or cfg.base_url or pick_base_url(spec)

    if output_json:
        payload = {
            "source": source,
            "base_url": resolved_base_url,
            "tool_count": len(operations),
            "tools": [
                {
                    "name": op.tool_name,
                    "method": op.method,
                    "path": op.path,
                    "summary": op.summary,
                }
                for op in operations.values()
            ],
        }
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    _print_operation_table(name="preview", source=source, base_url=resolved_base_url, operations=operations)


@app.command("mcp-config")
def mcp_config(
    source: str = typer.Argument(..., help="Path or URL of OpenAPI/Swagger file"),
    name: str = typer.Option("openapi-mcp", "--name", help="MCP server name key"),
    config: str = typer.Option("", "--config", help="Path to openapi-to-mcp YAML/JSON config"),
    base_url: str = typer.Option("", "--base-url", help="Force base URL for generated run args"),
    timeout: float = typer.Option(-1.0, "--timeout", help="HTTP timeout in seconds"),
    include_tags: str = typer.Option("", "--include-tags", help="Comma-separated tags to keep"),
    exclude_tags: str = typer.Option("", "--exclude-tags", help="Comma-separated tags to drop"),
    only_operations: str = typer.Option(
        "", "--only-operations", help="Comma-separated operationIds to include"
    ),
    methods: str = typer.Option("", "--methods", help="Comma-separated HTTP methods to include"),
    prefix: str = typer.Option("", "--prefix", help="Prefix generated tool names"),
) -> None:
    """Print a ready-to-paste mcpServers JSON snippet."""
    cfg = _load_config_safe(config)

    run_args: list[str] = ["run", source, "--name", name]
    if config:
        run_args.extend(["--config", config])
    if base_url:
        run_args.extend(["--base-url", base_url])
    if timeout >= 0:
        run_args.extend(["--timeout", str(timeout)])
    if include_tags:
        run_args.extend(["--include-tags", include_tags])
    if exclude_tags:
        run_args.extend(["--exclude-tags", exclude_tags])
    if only_operations:
        run_args.extend(["--only-operations", only_operations])
    if methods:
        run_args.extend(["--methods", methods])
    if prefix:
        run_args.extend(["--prefix", prefix])

    # If base URL is not explicitly set, try to infer it now for clarity.
    inferred_base_url = ""
    if not base_url and not cfg.base_url:
        try:
            spec = load_openapi_document(source)
            inferred_base_url = pick_base_url(spec)
        except Exception:  # noqa: BLE001
            inferred_base_url = ""
    if inferred_base_url:
        run_args.extend(["--base-url", inferred_base_url])

    payload = {
        "mcpServers": {
            name: {
                "command": "openapi-to-mcp",
                "args": run_args,
                "env": {
                    "OPENAPI_BEARER_TOKEN": "<your_token_if_needed>",
                    "OPENAPI_API_KEY": "<your_api_key_if_needed>",
                },
            }
        }
    }

    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command("init-config")
def init_config(
    path: str = typer.Argument("openapi-to-mcp.yaml", help="Output config file path"),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite if file exists"),
) -> None:
    """Generate a starter config file."""
    output_path = Path(path)
    if output_path.exists() and not force:
        raise typer.Exit(
            code=_print_error(f"File already exists: {output_path}. Use --force to overwrite.")
        )

    output_path.write_text(render_template_config(), encoding="utf-8")
    console.print(f"[green]Wrote[/] {output_path}")


def _load_config_safe(path: str) -> AppConfig:
    if not path:
        return AppConfig()

    try:
        return load_app_config(path)
    except Exception as exc:  # noqa: BLE001
        raise typer.Exit(code=_print_error(f"Failed to load config `{path}`: {exc}")) from exc


def _build_options_from_inputs(
    *,
    cfg: AppConfig,
    include_tags: str,
    exclude_tags: str,
    only_operations: str,
    methods: str,
    prefix: str,
) -> BuildOptions:
    include_tags_set = parse_csv_set(include_tags) if include_tags else cfg.include_tags
    exclude_tags_set = parse_csv_set(exclude_tags) if exclude_tags else cfg.exclude_tags
    only_ops_set = parse_csv_set(only_operations) if only_operations else cfg.only_operation_ids
    method_set = parse_csv_set(methods) if methods else cfg.allowed_methods
    prefix_value = prefix if prefix else cfg.name_prefix

    return BuildOptions(
        include_tags=include_tags_set,
        exclude_tags=exclude_tags_set,
        only_operation_ids=only_ops_set,
        allowed_methods=method_set,
        name_prefix=prefix_value,
    )


def _print_operation_table(
    *,
    name: str,
    source: str,
    base_url: str,
    operations: dict[str, OperationSpec],
) -> None:
    console.print(f"server: [cyan]{name}[/]")
    console.print(f"source: {source}")
    console.print(f"base URL: {base_url or '(not set)'}")
    console.print(f"tools: [bold]{len(operations)}[/]")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Tool")
    table.add_column("HTTP")
    table.add_column("Path")
    table.add_column("Summary")

    for op in operations.values():
        table.add_row(op.tool_name, op.method, op.path, op.summary)

    console.print(table)


def _print_error(message: str) -> int:
    console.print(f"[bold red]Error:[/] {message}")
    return 1


if __name__ == "__main__":
    app()
