# CI/CD Workflow Generation

## Purpose

Generate stack-aware CI/CD workflow files (GitHub Actions) based on installed stacks and framework enforcement checks. Produces project-managed workflow files that replicate local quality gates and add deployment-stage security checks.

## Trigger

- Command: agent invokes CI/CD generation skill or user requests CI/CD setup.
- Context: new project setup, stack addition, framework enforcement update, CI/CD modernization.

## Procedure

1. **Read install manifest** — load `install-manifest.json` for active stacks and providers.
   - Determine stacks: `installedStacks` field.
   - Determine VCS provider: `providers.vcs.primary` field.
   - If no manifest exists, prompt user for stack selection.

2. **Read enforcement checks** — load `manifest.yml` for per-stack check definitions.
   - Map `enforcement.checks.pre_commit` and `enforcement.checks.pre_push` to CI jobs.
   - Include `common` checks for all stacks.
   - Include stack-specific checks for each active stack.

3. **Generate primary CI workflow** — create `.github/workflows/ci.yml`.
   - Matrix strategy across active stacks.
   - Jobs: lint → build → test → security.
   - Common checks run once (gitleaks, semgrep).
   - Stack-specific checks run per matrix entry.
   - Coverage upload as artifact.

4. **Generate security workflow** (if DAST/container tools configured) — create `.github/workflows/security.yml`.
   - Trigger: on deployment to staging, or manual dispatch.
   - DAST job: ZAP/Nuclei against staging URL (URL as workflow input).
   - Container scan job: Trivy on built images (image reference as input).
   - Results uploaded as artifacts.

5. **Generate SBOM workflow** (if SBOM skill active) — create `.github/workflows/sbom.yml`.
   - Trigger: on release or manual dispatch.
   - Per-stack SBOM generation.
   - Upload SBOM as release asset.

6. **Validate generated workflows** — check syntax.
   - Run `actionlint` on generated files if available.
   - Verify YAML validity.
   - Report any issues.

7. **Report** — summarize generated files and next steps.
   - List generated workflow files.
   - Note required GitHub Actions secrets/variables.
   - Recommend branch protection settings.

## Output Contract

- Generated workflow file(s) in `.github/workflows/`.
- Validation report (actionlint results if available).
- Recommendations for GitHub repository settings (branch protection, required checks).

## Governance Notes

- Generated workflows are **project-managed** — the skill generates once, the project maintains.
- The skill does not push or commit workflow files — it generates them for review.
- Workflows must replicate all local gate checks per `standards/framework/cicd/core.md`.
- Secret values (API keys, tokens) must use GitHub Actions secrets, never hardcoded.

## References

- `standards/framework/cicd/core.md` — CI/CD standards and requirements.
- `manifest.yml` — per-stack enforcement check definitions.
- `standards/framework/stacks/python.md` — Python check details.
- `standards/framework/stacks/dotnet.md` — .NET check details.
- `standards/framework/stacks/nextjs.md` — Next.js check details.
