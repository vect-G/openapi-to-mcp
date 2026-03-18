# Launch Copies (v0.3.2)

Repo: https://github.com/vect-G/openapi-to-mcp

## X / Twitter

### English

Shipped `openapi-to-mcp` v0.3.2.

One command to turn OpenAPI/Swagger into a runnable MCP server.

- external `$ref` support (file + URL)
- nested `$ref` expansion
- Swagger2 `in: body` support
- publish workflow fixes

Try:
`openapi-to-mcp run https://petstore3.swagger.io/api/v3/openapi.json`

Repo: https://github.com/vect-G/openapi-to-mcp

### 中文

`openapi-to-mcp` 发布到 v0.3.2 了。

一句话：一行命令把 OpenAPI/Swagger 变成可运行的 MCP Server。

这几个点已经支持：
- 外部 `$ref`（本地文件 + URL）
- 嵌套 `$ref` 展开
- Swagger2 `in: body`
- 发布流程修复

仓库：https://github.com/vect-G/openapi-to-mcp

## Reddit

Title:
`openapi-to-mcp v0.3.2: One-command OpenAPI/Swagger -> MCP server (external $ref + Swagger2 support)`

Body:
I’m building `openapi-to-mcp` to help teams reuse existing API specs as MCP tools without writing wrappers.

Highlights:
- OpenAPI/Swagger -> MCP tools over stdio
- external `$ref` (local and URL)
- nested `$ref` handling
- Swagger2 `in: body` compatibility

Quick test:
```bash
openapi-to-mcp list https://petstore3.swagger.io/api/v3/openapi.json --json
```

Repo: https://github.com/vect-G/openapi-to-mcp
If you have a spec that fails, share it and I’ll add support + tests.

## Hacker News

Title:
`Show HN: openapi-to-mcp — one-command OpenAPI/Swagger to MCP server`

Post:
Built a CLI to convert OpenAPI/Swagger specs into a runnable MCP server.

v0.3.x now handles:
- external `$ref`
- nested `$ref`
- Swagger2 body params

Repo: https://github.com/vect-G/openapi-to-mcp
I’m collecting weird enterprise specs to improve compatibility.

## 中文平台（知乎/掘金/即刻）

标题：
`我做了个开源工具：OpenAPI/Swagger 一键转 MCP Server（v0.3.2）`

正文：
这几天把 `openapi-to-mcp` 打磨到 v0.3.2。

它做的事很直接：
- 输入 OpenAPI/Swagger 文档
- 自动映射成 MCP tools
- 直接运行给 Agent/LLM 用

目前重点支持：
- 外部 `$ref` + 嵌套 `$ref`
- Swagger2 的 `in: body`

仓库：https://github.com/vect-G/openapi-to-mcp
如果你有复杂规范，欢迎直接丢 issue，我会按复现优先修。
