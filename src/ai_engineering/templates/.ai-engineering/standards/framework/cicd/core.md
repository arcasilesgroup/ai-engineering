# CI/CD Standards

## Update Metadata

- Rationale: define CI/CD contract ensuring pipelines replicate local quality gates and add deployment-stage checks.
- Expected gain: consistent enforcement between local and CI environments; deployment-stage security checks automated.
- Potential impact: CI workflows must include all local gate checks plus additional deployment-stage scans.

## Purpose

Defines the contract between local quality gates and CI/CD pipelines. Ensures pipelines replicate local enforcement and add checks that cannot run locally (DAST, container scanning).

## Principles

1. **CI replicates local gates** — every pre-commit and pre-push check must have a CI equivalent.
2. **CI extends local gates** — DAST, container scanning, and SBOM generation run in CI only.
3. **Workflows are project-managed** — generated once by the CI/CD skill, then maintained by the project.
4. **Branch protection requires CI** — status checks from CI must be required for merge.

## Required CI Checks (Per Stack)

### Common (All Stacks)

- `gitleaks` — secret detection.
- `semgrep` — SAST with OWASP rules.

### Python

- `ruff format --check` + `ruff check` — format and lint.
- `pip-audit` — dependency vulnerability scan.
- `pytest` — test suite with coverage.
- `ty check` — type checking.

### .NET

- `dotnet format --verify-no-changes` — format check.
- `dotnet build` — compilation.
- `dotnet test` — test suite with coverage.
- `dotnet list package --vulnerable` — dependency scan.

### Next.js/TypeScript

- `prettier --check` + `eslint` — format and lint.
- `tsc --noEmit` — type checking.
- `vitest run` — test suite with coverage.
- `npm audit` — dependency scan.

## Required CI Checks (Snyk Security)

These checks require `SNYK_TOKEN` configured as a repository secret. When the token is absent, the job passes with a skip notice. When present, all checks must pass.

- **Snyk dependency test** — `snyk test --file=requirements.txt --package-manager=pip` for dependency vulnerabilities. Uses `uv pip freeze` to export pinned versions from the venv.
- **Snyk code test** — `snyk code test` for SAST analysis. Requires Snyk Code enabled in org settings.
- **Snyk monitor** — `snyk monitor --file=requirements.txt --package-manager=pip` for continuous monitoring. Runs on main branch pushes only.

## Optional CI Checks (Deployment-Stage)

These checks run only when tools are available and configured:

- **DAST** — OWASP ZAP or Nuclei against staging environment.
- **Container scan** — Trivy image scanning on built images.
- **SBOM generation** — CycloneDX SBOM as release artifact.

## Workflow Structure

CI workflows should follow this structure:

1. **Lint/Format** — fast feedback on code style.
2. **Build** — compilation/transpilation per stack.
3. **Test** — unit and integration tests with coverage.
4. **Security** — SAST, dependency scan, secret detection.
5. **Deploy-stage** (optional) — DAST, container scan, SBOM.

## Branch Protection

- Default branch (`main`/`master`) must require passing CI status checks.
- Pull requests must pass all required CI checks before merge.
- Direct push to protected branches is blocked (enforced by framework + CI).

## Multi-Stack Matrix

For multi-stack projects, CI should use matrix strategy:

- Run common checks once.
- Run stack-specific checks per stack.
- Aggregate results before merge gate.

## References

- `standards/framework/core.md` — mandatory local enforcement.
- `manifest.yml` — per-stack check definitions.
- `skills/cicd/SKILL.md` — CI/CD workflow generation skill.

## Update Contract

This file is framework-managed and may be updated by framework releases.
