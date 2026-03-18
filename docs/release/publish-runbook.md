# Publish Runbook (v0.3.0)

## 0) Fill placeholders

- Replace GitHub URLs in `pyproject.toml`:
  - `https://github.com/vect-G/openapi-to-mcp`
- Replace `<YOUR_HANDLE>` in launch copies.
- (Optional) Replace security email in `SECURITY.md`.

## 1) Final local checks

```bash
conda run -n openapi-mcp pytest -q
conda run -n openapi-mcp openapi-to-mcp list examples/external-ref/api.yaml --json
conda run -n openapi-mcp openapi-to-mcp list examples/swagger2.yaml --json
```

## 2) Commit and tag

```bash
git init
git add .
git commit -m "release: v0.3.0"
git branch -M main
git remote add origin https://github.com/vect-G/openapi-to-mcp.git
git push -u origin main
git tag v0.3.0
git push origin v0.3.0
```

## 3) Create GitHub Release

- Tag: `v0.3.0`
- Title: `openapi-to-mcp v0.3.0`
- Body: copy `docs/release/v0.3.0-release-notes.md`

## 4) Publish announcement

- X/Reddit/HN/中文社区 using `docs/release/launch-copies.md`
- Add demo GIF from `scripts/demo.sh`

## 5) First 48 hours playbook

- Reply to every issue within 12-24h.
- Collect 2-3 real specs from users and add them as examples.
- Ship one quick follow-up patch release (even small) to show project momentum.
