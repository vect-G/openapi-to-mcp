# openapi-to-mcp

[![CI](https://github.com/vect-G/openapi-to-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/vect-G/openapi-to-mcp/actions/workflows/ci.yml)
[![Publish](https://github.com/vect-G/openapi-to-mcp/actions/workflows/publish.yml/badge.svg)](https://github.com/vect-G/openapi-to-mcp/actions/workflows/publish.yml)
[![GitHub Release](https://img.shields.io/github/v/release/vect-G/openapi-to-mcp)](https://github.com/vect-G/openapi-to-mcp/releases)
[![GitHub stars](https://img.shields.io/github/stars/vect-G/openapi-to-mcp?style=social)](https://github.com/vect-G/openapi-to-mcp/stargazers)
[![License](https://img.shields.io/github/license/vect-G/openapi-to-mcp)](LICENSE)

Turn any OpenAPI/Swagger spec into a runnable MCP server in one command.

## 30s Try

```bash
openapi-to-mcp run https://petstore3.swagger.io/api/v3/openapi.json
```

If it fails on your spec, open an **OpenAPI Compatibility Request** issue.

## Why developers star this

- Instant leverage: existing REST APIs become AI-callable tools.
- Zero boilerplate: no hand-written MCP wrappers per endpoint.
- Production-minded: filtering, naming rules, auth mapping, CI-ready packaging.
- Handles real-world specs: supports external `$ref` files and Swagger 2 body params.

This exposes Petstore operations as MCP tools over `stdio`.

## Quickstart (Conda)

```bash
conda create -y -n openapi-mcp python=3.11
conda run -n openapi-mcp python -m pip install -e .[dev]

conda run -n openapi-mcp openapi-to-mcp run examples/store.yaml --dry-run
```

Expected output includes generated tools like:

- `listproducts`
- `getorder`
- `createorder`
- `internalhealth`

## Commands

```bash
openapi-to-mcp run <source> [options]
openapi-to-mcp list <source> [options]
openapi-to-mcp mcp-config <source> [options]
openapi-to-mcp init-config [path]
```

## Powerful options

- `--config`: Load YAML/JSON config
- `--include-tags`: Keep only matching tags
- `--exclude-tags`: Drop matching tags
- `--only-operations`: Include specific operationIds
- `--methods`: Keep specific HTTP methods
- `--prefix`: Prefix generated MCP tool names
- `--base-url`: Override `servers` URL

Example:

```bash
openapi-to-mcp list examples/store.yaml \
  --include-tags orders \
  --methods get \
  --prefix shop \
  --json
```

## Config file mode

Generate a starter file:

```bash
openapi-to-mcp init-config
```

`openapi-to-mcp.yaml` example:

```yaml
runtime:
  base_url: https://api.example.com/v1
  timeout_seconds: 30

naming:
  prefix: shop

filters:
  include_tags: [orders]
  exclude_tags: [internal]
  operation_ids: []
  methods: [get, post]
```

Use it:

```bash
openapi-to-mcp run ./openapi.yaml --config openapi-to-mcp.yaml
```

## MCP client config snippet

Generate a ready-to-paste JSON snippet:

```bash
openapi-to-mcp mcp-config examples/store.yaml --name demo
```

It outputs:

```json
{
  "mcpServers": {
    "demo": {
      "command": "openapi-to-mcp",
      "args": ["run", "examples/store.yaml", "--name", "demo"],
      "env": {
        "OPENAPI_BEARER_TOKEN": "<your_token_if_needed>",
        "OPENAPI_API_KEY": "<your_api_key_if_needed>"
      }
    }
  }
}
```

## Auth mapping

Common OpenAPI security types are mapped from environment variables:

- API key: `OPENAPI_API_KEY` or `OPENAPI_AUTH_<SCHEME_NAME>`
- Bearer/OAuth2/OpenID: `OPENAPI_BEARER_TOKEN` or `OPENAPI_AUTH_<SCHEME_NAME>`
- Basic auth: `OPENAPI_BASIC_USER` + `OPENAPI_BASIC_PASS` or `OPENAPI_AUTH_<SCHEME_NAME>=user:pass`

## Development

```bash
conda run -n openapi-mcp pytest -q
```

CI and release workflows are provided in `.github/workflows/`.

## Limitations (current)

- Response schema extraction is minimal
- Focused on HTTP tools (no resource/prompt generation yet)

## Docs

- [CONTRIBUTING.md](CONTRIBUTING.md)
- [CHANGELOG.md](CHANGELOG.md)
- [ROADMAP.md](ROADMAP.md)
- [SECURITY.md](SECURITY.md)
- [docs/launch-checklist.md](docs/launch-checklist.md)
- [docs/post-template.md](docs/post-template.md)
- [docs/release/v0.3.0-release-notes.md](docs/release/v0.3.0-release-notes.md)
- [docs/release/v0.3.1-release-notes.md](docs/release/v0.3.1-release-notes.md)
- [docs/release/v0.3.2-release-notes.md](docs/release/v0.3.2-release-notes.md)
- [docs/release/launch-copies.md](docs/release/launch-copies.md)
- [docs/release/launch-copies-v0.3.2.md](docs/release/launch-copies-v0.3.2.md)
- [docs/release/repo-branding.md](docs/release/repo-branding.md)
- [docs/release/publish-runbook.md](docs/release/publish-runbook.md)
- [docs/release/pinned-issue-openapi-drop.md](docs/release/pinned-issue-openapi-drop.md)
- [docs/release/day-2-growth-playbook.md](docs/release/day-2-growth-playbook.md)
- [scripts/demo.sh](scripts/demo.sh)

## More examples

- [examples/swagger2.yaml](examples/swagger2.yaml)
- [examples/external-ref/api.yaml](examples/external-ref/api.yaml)

## License

MIT
