---
id: "048"
slug: "snyk-optional-cicd"
status: "in-progress"
created: "2026-03-10"
size: "S"
tags: ["security", "cicd", "snyk", "optional"]
branch: "feat/048-snyk-optional-cicd"
pipeline: "standard"
decisions:
  - id: "DEC-048-01"
    decision: "Snyk integration is CI/CD only — no local hooks"
    rationale: "Not all contributors will have snyk installed; local gates stay with gitleaks+semgrep+pip-audit"
  - id: "DEC-048-02"
    decision: "Snyk steps are optional (conditional on SNYK_TOKEN secret)"
    rationale: "Fail-open: repos without snyk token skip the steps silently"
  - id: "DEC-048-03"
    decision: "Snyk complements existing tools, does not replace them"
    rationale: "gitleaks, semgrep, pip-audit remain mandatory; snyk adds a second opinion layer"
---

# Spec 048 — Snyk Optional CI/CD Integration

## Problem

The framework uses gitleaks, semgrep, and pip-audit for security scanning. Snyk CLI provides deeper dependency vulnerability analysis and SAST capabilities but is not integrated. Snyk requires authentication (API key) and not all contributors/adopters will have it, so it cannot be a mandatory gate.

## Solution

Add Snyk as an **optional** CI/CD security step that runs when `SNYK_TOKEN` is configured as a repository secret. Keep all existing local gates unchanged. Document snyk as an optional tool in the framework manifest and CI/CD standards.

## Scope

### In Scope

- Add `snyk test` step to CI workflow (dependency vulnerabilities)
- Add `snyk code test` step to CI workflow (SAST)
- Both steps conditional on `SNYK_TOKEN` secret existence
- Add `snyk monitor` step for continuous monitoring (post-merge only)
- Register snyk as optional tool in `manifest.yml`
- Update `standards/framework/cicd/core.md` with snyk as optional check
- Update `skills/security/SKILL.md` to mention snyk as optional tool

### Out of Scope

- Local hook integration (snyk stays CI-only)
- Replacing pip-audit, semgrep, or gitleaks
- Snyk container scanning (no containers yet)
- Snyk IaC scanning (no IaC in repo)
- Snyk SBOM generation (existing cyclonedx-py is sufficient)
- `ai-eng doctor` snyk detection (not a required tool)

## Acceptance Criteria

1. CI workflow has a `snyk` job with `snyk test` and `snyk code test` steps
2. Snyk job is conditional: skipped gracefully when `SNYK_TOKEN` is not set
3. Snyk job does NOT block the `build` job (non-gating, informational)
4. `snyk monitor` runs only on pushes to main (not on PRs)
5. `manifest.yml` lists snyk under `tooling.optional.security`
6. `standards/framework/cicd/core.md` documents snyk as optional CI check
7. `skills/security/SKILL.md` references snyk as optional tool in `static` and `deps` modes
8. All existing security gates (gitleaks, semgrep, pip-audit) remain unchanged
9. CI workflow passes actionlint validation

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| DEC-048-01 | CI/CD only, no local hooks | Not all contributors have snyk |
| DEC-048-02 | Optional via SNYK_TOKEN conditional | Fail-open for repos without snyk |
| DEC-048-03 | Complements, does not replace | Existing tools remain mandatory |
