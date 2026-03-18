# Publish Runbook

## 0) Fill placeholders

- Replace GitHub URLs in `pyproject.toml`:
  - `https://github.com/vect-G/openapi-to-mcp`
- Replace `<YOUR_HANDLE>` in launch copies.
- (Optional) Replace security email in `SECURITY.md`.

## 0.5) Choose PyPI publish mode

Option A (simplest): API token

- In PyPI, create an API token (project-scoped recommended).
- In GitHub repo: `Settings -> Secrets and variables -> Actions`
- Add secret: `PYPI_API_TOKEN`

Option B: Trusted Publisher (OIDC)

- Configure Trusted Publisher on PyPI for this exact repo/workflow.
- If claims do not match, you'll see `invalid-publisher`.
- This repository currently defaults to API token mode.

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
git commit -m "release: vX.Y.Z"
git branch -M main
git remote add origin https://github.com/vect-G/openapi-to-mcp.git
git push -u origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 3) Create GitHub Release

- Tag: `vX.Y.Z`
- Title: `openapi-to-mcp vX.Y.Z`
- Body: copy matching release notes from `docs/release/`

## 4) Publish announcement

- X/Reddit/HN/中文社区 using `docs/release/launch-copies.md`
- Add demo GIF from `scripts/demo.sh`

## 5) First 48 hours playbook

- Reply to every issue within 12-24h.
- Collect 2-3 real specs from users and add them as examples.
- Ship one quick follow-up patch release (even small) to show project momentum.
