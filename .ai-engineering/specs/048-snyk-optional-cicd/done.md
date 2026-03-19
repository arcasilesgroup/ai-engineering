---
spec: "048"
title: "Snyk Optional CI/CD Integration"
completed: "2026-03-10"
prs: ["#127", "#128"]
---

# Done — Snyk Optional CI/CD Integration

## Summary

Added Snyk CLI as an optional CI/CD security layer, conditional on `SNYK_TOKEN` secret presence.

## Delivered

- `snyk-security` job in CI workflow with token-conditional execution
- Snyk dependency test (`snyk test --file=requirements.txt --package-manager=pip`)
- Snyk SAST (`snyk code test`) with severity threshold
- Snyk monitor on main branch pushes
- Mandatory gate: `snyk-security` added to `build.needs`
- Framework registration: manifest.yml, cicd/core.md, security SKILL.md
- README badges for SonarCloud and Snyk

## Key Decisions

- Venv activation required before `snyk test` to avoid false positives from pyproject.toml auto-detection
- `uv pip freeze` used to export pinned requirements (not `uv export`)
- Severity threshold set to `high` to avoid noise from low/medium findings
