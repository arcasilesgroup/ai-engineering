---
spec: "048"
approach: "serial-phases"
---

# Plan — Snyk Optional CI/CD Integration

## Architecture

### Modified Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Add snyk job with test, code test, and monitor steps |
| `.ai-engineering/manifest.yml` | Register snyk as optional security tool |
| `.ai-engineering/standards/framework/cicd/core.md` | Document snyk as optional CI check |
| `.ai-engineering/skills/security/SKILL.md` | Reference snyk as optional tool in modes |

### New Files

None.

### Mirror Copies

None.

## Session Map

### Phase 0: Scaffold [S]
Spec files, branch, activate.

### Phase 1: CI Workflow [M]
Add `snyk-security` job to `.github/workflows/ci.yml`:
- Conditional on `secrets.SNYK_TOKEN`
- `snyk test` for dependency vulnerabilities
- `snyk code test` for SAST
- `snyk monitor` on main branch pushes only
- Non-gating: `build` job does NOT depend on snyk job
- Uses `continue-on-error: true` for resilience

### Phase 2: Framework Registration [S]
- `manifest.yml`: add `snyk` to `tooling.optional.security`
- `cicd/core.md`: add snyk to optional CI checks section
- `security/SKILL.md`: mention snyk as optional in `static` and `deps` modes

### Phase 3: Validation [S]
- Run actionlint on modified workflow
- Verify existing CI jobs are unchanged
- Run `ai-eng validate` for content integrity

## Patterns

- **Fail-open**: snyk steps use `if: secrets.SNYK_TOKEN != ''` guard
- **Non-gating**: snyk job is independent, not in the `build` dependency chain
- **Monitor on main only**: `snyk monitor` uses additional `if: github.ref == 'refs/heads/main'`

## Agent Assignments

| Phase | Agent | Skills |
|-------|-------|--------|
| 1 | build | cicd |
| 2 | build | security, standards |
| 3 | scan | governance, security |
