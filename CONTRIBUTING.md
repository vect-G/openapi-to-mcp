# Contributing

Thanks for helping improve `openapi-to-mcp`.

## Local setup

```bash
conda create -y -n openapi-mcp python=3.11
conda run -n openapi-mcp python -m pip install -e .[dev]
```

## Run checks

```bash
conda run -n openapi-mcp pytest -q
conda run -n openapi-mcp openapi-to-mcp list examples/store.yaml --json
```

## Pull request guidelines

- Keep changes focused and small when possible.
- Add tests for behavior changes.
- Update docs when introducing flags or new commands.
- Do not commit generated build artifacts from `dist/`.

## Release flow

- Tag format: `vX.Y.Z`.
- GitHub Action `Publish` builds and uploads package to PyPI.
- Ensure `PYPI_API_TOKEN` secret is configured before tagging.
