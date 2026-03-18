# Changelog

## 0.3.1 - 2026-03-18

- CI: publish workflow now skips PyPI upload when `PYPI_API_TOKEN` is not configured.
- Docs: added explicit PyPI token vs trusted publisher guidance to publish runbook.

## 0.3.0 - 2026-03-18

- Added external `$ref` resolution across local files and URLs.
- Added nested `$ref` expansion support inside referenced external files.
- Added Swagger 2 `in: body` parameter support as MCP tool request body.
- Expanded tests to cover external references and legacy Swagger body mapping.

## 0.2.0 - 2026-03-18

- Added config file support (`--config`) with runtime, naming, and filter sections.
- Added operation filtering by tags, methods, and operation IDs.
- Added tool naming prefix support.
- Added `mcp-config` command to generate ready-to-paste MCP client JSON.
- Added `init-config` command to scaffold starter YAML config.
- Improved base URL resolution for remote specs with relative `servers.url`.
- Added CI workflow and package publish workflow.
- Expanded test suite to cover config loading, filtering, and runtime behavior.

## 0.1.0 - 2026-03-18

- Initial release.
- One-command OpenAPI/Swagger to MCP server runtime.
- Supports local files and remote OpenAPI URLs.
- Basic auth scheme mapping and structured tool results.
