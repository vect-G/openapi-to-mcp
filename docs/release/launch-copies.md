# Launch Copies (v0.3.0)

Replace these placeholders before posting:

- `<YOUR_HANDLE>`

## X / Twitter

### EN short

Built `openapi-to-mcp` v0.3.0: turn OpenAPI/Swagger into a runnable MCP server in one command.

New in this release:
- external `$ref` support (local + URL)
- nested `$ref` expansion
- Swagger 2 `in: body` support

Try:
`openapi-to-mcp run https://petstore3.swagger.io/api/v3/openapi.json`

Repo: https://github.com/vect-G/openapi-to-mcp

### EN medium

Shipped `openapi-to-mcp` v0.3.0.

If you already have OpenAPI specs and want AI agents to call them via MCP, this tool removes the wrapper work.

New:
- external `$ref` across files/URLs
- nested `$ref` resolution
- Swagger 2 `in: body` compatibility

Demo:
`openapi-to-mcp list examples/external-ref/api.yaml --json`

Repo: https://github.com/vect-G/openapi-to-mcp
Feedback welcome, especially weird specs.

### 中文短版

我开源了 `openapi-to-mcp` v0.3.0：
一行命令把 OpenAPI/Swagger 变成可运行的 MCP Server。

这版新增：
- 外部 `$ref`（本地文件/远程 URL）
- 嵌套 `$ref` 展开
- Swagger2 `in: body` 兼容

仓库：https://github.com/vect-G/openapi-to-mcp
欢迎拿你们的真实 API 规范来测。

## Reddit (r/LocalLLaMA / r/Python)

Title:
`openapi-to-mcp v0.3.0: One-command OpenAPI/Swagger -> MCP server (now supports external $ref + Swagger2 body)`

Body:
I built `openapi-to-mcp` to bridge existing REST APIs into MCP tools with minimal glue code.

What it does:
- reads local or remote OpenAPI/Swagger specs
- maps operations to MCP tools
- calls upstream APIs and returns structured results

What’s new in v0.3.0:
- external `$ref` support (file + URL)
- nested `$ref` expansion
- Swagger 2 `in: body` mapping

Quick try:
```bash
openapi-to-mcp run https://petstore3.swagger.io/api/v3/openapi.json
```

Repo: https://github.com/vect-G/openapi-to-mcp
I’d love feedback on unusual enterprise specs.

## Hacker News

Title options:
- Show HN: openapi-to-mcp – One-command OpenAPI/Swagger to MCP server
- openapi-to-mcp v0.3.0: External `$ref` + Swagger2 support

Post:
I built `openapi-to-mcp`, a CLI that turns OpenAPI/Swagger docs into a runnable MCP server.

Goal: teams already have API specs; they should not need to hand-write MCP wrappers.

v0.3.0 added:
- external `$ref` (files + URLs)
- nested `$ref` resolution
- Swagger2 `in: body` compatibility

Repo: https://github.com/vect-G/openapi-to-mcp
Happy to debug any spec edge cases.

## 中文社区（知乎/掘金/即刻）

标题建议：
- 开源一个工具：把 OpenAPI 一键变成 MCP Server（支持外部 $ref）
- 我做了个 CLI：OpenAPI/Swagger 到 MCP Server，全自动

正文：
最近做 Agent 工具接入时，我发现很多团队已经有 OpenAPI 文档，但缺一个 MCP Server。
所以做了 `openapi-to-mcp`：

- 输入 OpenAPI/Swagger（本地文件或 URL）
- 自动把每个接口转成 MCP tool
- 直接以 stdio 方式运行

v0.3.0 新增：
- 外部 `$ref`（文件和远程 URL）
- 引用里的嵌套 `$ref` 展开
- Swagger2 的 `in: body` 参数兼容

仓库：https://github.com/vect-G/openapi-to-mcp
如果你有复杂规范（比如多层 ref、历史 Swagger2），欢迎丢给我测。
