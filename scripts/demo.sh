#!/usr/bin/env bash
set -euo pipefail

# Quick terminal demo for recording GIFs/videos.
# Usage: bash scripts/demo.sh

echo "== openapi-to-mcp demo =="

echo
printf '1) Inspect tools from public OpenAPI...\n\n'
openapi-to-mcp list https://petstore3.swagger.io/api/v3/openapi.json --json | head -n 30

echo
printf '2) Generate MCP config snippet...\n\n'
openapi-to-mcp mcp-config https://petstore3.swagger.io/api/v3/openapi.json --name petstore | head -n 40

echo
printf '3) Dry-run with local spec + filters...\n\n'
openapi-to-mcp run examples/store.yaml --include-tags orders --prefix shop --dry-run
