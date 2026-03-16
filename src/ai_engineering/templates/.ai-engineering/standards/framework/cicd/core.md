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
- `skills/pipeline/SKILL.md` — CI/CD workflow generation skill.

## Action Version Pinning Policy

All GitHub Actions must use pinned, auditable version references.

### Rules

- **Third-party actions**: SHA pinning required. Format: `uses: owner/action@SHA # vN.M.P`.
- **First-party GitHub actions** (`actions/*`): major version tag acceptable (`@v4`).
- **Tag comment**: always include the human-readable version as a trailing comment.
- **Never use branch references**: `@main` or `@master` are prohibited.
- **Dependabot updates SHAs**: the `github-actions` ecosystem in `dependabot.yml` auto-updates pinned SHAs.

### Example

```yaml
# Correct — SHA-pinned with tag comment
- uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11 # v4.1.1
- uses: astral-sh/setup-uv@6b9c6063abd6010835c3544edc914d3bbd55ad7e # v5.3.0

# Acceptable — first-party with major version
- uses: actions/checkout@v4

# Prohibited — mutable tag, no audit trail
- uses: some-org/some-action@v2
- uses: some-org/some-action@main
```

## Dependabot Management Contract

Dependency updates must be managed through Dependabot with proper grouping and automation.

### Requirements

- **Ecosystem grouping**: all dependencies within an ecosystem grouped into a single PR (reduces review overhead).
- **Conventional commit prefixes**: `chore(deps)` for runtime, `chore(deps-dev)` for dev, `ci(deps)` for actions.
- **Auto-lock workflow**: Python projects using `uv` must have `dependabot-auto-lock.yml` to regenerate `uv.lock` after `pyproject.toml` changes. Node projects regenerate `package-lock.json`.
- **Weekly schedule**: Monday for all ecosystems (configurable per project).
- **PR limit**: 5 open PRs per ecosystem maximum.

### Supported Ecosystems

| Ecosystem | Lock file | Auto-lock command |
|-----------|-----------|-------------------|
| pip (uv) | `uv.lock` | `uv lock` |
| npm | `package-lock.json` | `npm install --package-lock-only` |
| github-actions | N/A | N/A |

## Azure Pipelines Standards

Azure Pipelines projects must use template composition and enterprise patterns for maintainability and consistency.

### Template Composition

- **Central template repository**: shared templates in a dedicated repo, referenced via `resources.repositories`.
- **Manager pattern**: high-level orchestrator templates (`build-manager.yml`, `deploy-manager.yml`) that compose lower-level templates.
- **Three template levels**: stage templates, job templates, step templates — use the appropriate level for the reuse scope.
- **Versioned references**: pin template repo references to specific branches or tags, never `main` for production.

### Variable Management

- **Variable groups per environment**: `app-settings-INT`, `app-settings-ACC`, `app-settings-PRO`.
- **KeyVault-linked groups**: sensitive values (connection strings, API keys, certificates) must come from Azure Key Vault.
- **Never inline secrets**: no secret values in YAML files, pipeline variables UI, or script arguments.

### Environment Gates

- **Production requires approval**: at least 1 approver for production deployments.
- **Exclusive lock**: prevent parallel deployments to the same environment.
- **Business hours gate**: optional, for production deployments during working hours only.
- **Staging requires passing CI**: no manual deployment to staging without green CI.

### Artifact Promotion

- **Build once, deploy many**: the same artifact flows through INT → ACC → PRO.
- **Never rebuild between environments**: configuration differs, binaries don't.
- **Versioned artifacts**: use `Build.BuildNumber` or semantic version in artifact names.

### Branch-Conditional Deployment

| Branch pattern | Target environment |
|---------------|-------------------|
| `develop` | Integration (INT) |
| `release/*` | Acceptance (ACC) |
| `main` | Production (PRO) |

## Reusable Components Contract

CI/CD platforms must use reusable components to reduce duplication and enforce consistency.

### GitHub Actions

- **Composite actions**: for repeated step sequences (setup, scan, deploy). Store in `.github/actions/<name>/action.yml`.
- **Reusable workflows**: for shared CI patterns across repos. Store in `.github/workflows/reusable-<name>.yml`.
- **Input/output contracts**: all reusable components must define explicit `inputs`, `outputs`, and `secrets`.
- **Versioning**: cross-repo reusable workflows referenced by SHA or tag, never branch.

### Azure Pipelines

- **Step templates**: for repeated step sequences.
- **Job templates**: for repeated job configurations.
- **Stage templates**: for repeated stage patterns (CI, deployment).
- **Template repo versioning**: pin to specific branch or tag in `resources.repositories`.

## Environment Protection Requirements

### Production

- **Required approvers**: at least 1 reviewer must approve deployment.
- **Wait timer**: optional delay (e.g., 15 minutes) for rollback window.
- **Branch restriction**: only `main` branch can deploy to production.
- **OIDC authentication**: preferred over long-lived deployment credentials.

### Staging

- **CI gate**: deployment requires passing CI pipeline.
- **Auto-deploy**: staging may auto-deploy after CI passes (no manual approval).
- **Branch restriction**: `develop` or `release/*` branches only.

### Secrets Management

- **GitHub**: use repository or environment secrets. Use OIDC for cloud providers.
- **Azure DevOps**: use variable groups linked to Azure Key Vault.
- **Never inline**: no secrets in YAML, scripts, or commit messages.

## Concurrency & Performance

### Concurrency Control

- **GitHub Actions**: `concurrency` group required for PR workflows. Cancel stale runs: `cancel-in-progress: true`.
- **Azure Pipelines**: use exclusive lock on environments to prevent parallel deployments.
- **Concurrency group pattern**: `ci-${{ github.ref }}` for CI, `deploy-<env>` for deployments.

### Timeout Policy

- **Every job must have a timeout**: default `timeout-minutes: 30`.
- **Test suites**: max 60 minutes.
- **Deployment jobs**: max 30 minutes.
- **No unlimited jobs**: bare `runs-on` without timeout is prohibited.

### Artifact Retention Policy

| Artifact type | Retention | Rationale |
|---------------|-----------|-----------|
| CI diagnostics | 5 days | Ephemeral debugging |
| Coverage reports | 30 days | Trend analysis |
| Release builds | 90 days | Compliance |
| SBOM | 1 year | Supply chain audit |

### Cache Strategy

| Stack | Tool | Cache key |
|-------|------|-----------|
| Python/uv | `setup-uv enable-cache` | Automatic |
| Node | `setup-node cache: npm` | `package-lock.json` hash |
| .NET | `actions/cache` | `packages.lock.json` hash |
| Rust | `actions/cache` | `Cargo.lock` hash |

## Required Check Strategy

### Single CI Result Gate

Branch Protection must require **only the `CI Result` job** as a status check (DEC-054-06). This replaces requiring individual job names.

### Rationale

Conditional jobs (`if: code == 'true'`) that are skipped show as "Expected" or "Pending" in Branch Protection, blocking merge for docs-only PRs, Dependabot PRs, and external contributions. A single aggregator job solves this.

### Job Categories

| Category | Jobs | Rule |
|----------|------|------|
| always-required | `security`, `content-integrity`, `workflow-sanity` | Must succeed always |
| code-conditional | `lint`, `typecheck`, `test-*`, `duplication`, `sonarcloud`, `framework-smoke`, `build` | Must succeed when code changes detected; skip accepted when no code changes |
| PR-only | `verify-gate-trailers` | Must succeed on non-Dependabot PRs; skip accepted for Dependabot and push events |
| optional | `snyk-security` | May skip (token absent) but must not fail |

### Anti-Bypass Rules

- `paths-filter` patterns must cover all source file extensions (`.py`, `.toml`, `.yml`, `.md`, etc.).
- The `ci-result` job must use `if: always()` to run even when upstream jobs are skipped.
- Any `failure` result in any category → `ci-result` fails.
- Individual job statuses remain visible in the PR checks UI for debugging.

### Branch Protection Configuration

```
Settings → Branches → Branch protection rules → main
  ✓ Require status checks to pass before merging
  ✓ Require branches to be up to date before merging
  Status checks that are required:
    → CI Result (only this one)
```

## Update Contract

This file is framework-managed and may be updated by framework releases.
