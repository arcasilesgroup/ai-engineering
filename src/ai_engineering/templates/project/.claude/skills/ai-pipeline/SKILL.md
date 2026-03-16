---
name: ai-pipeline
description: "Generate stack-aware CI/CD workflow files from installed stacks and enforcement checks; use when setting up or modernizing CI/CD pipelines."
---


# CI/CD Workflow Generation

## Purpose

Generate stack-aware CI/CD workflow files (GitHub Actions, Azure Pipelines) based on installed stacks and framework enforcement checks. Produces project-managed workflow files that replicate local quality gates and add deployment-stage security checks. Supports deployment to Railway, Cloudflare Workers/Pages, Vercel, and Netlify.

## Trigger

- Command: agent invokes CI/CD generation skill or user requests CI/CD setup.
- Context: new project setup, stack addition, framework enforcement update, CI/CD modernization.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"cicd"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Procedure

1. **Read install manifest** — load `install-manifest.json` for active stacks and providers.
   - Determine stacks: `installedStacks` field.
   - Determine VCS provider: `providers.vcs.primary` field.
   - If no manifest exists, prompt user for stack selection.

2. **Read enforcement checks** — load `manifest.yml` for per-stack check definitions.
   - Map `enforcement.checks.pre_commit` and `enforcement.checks.pre_push` to CI jobs.
   - Include `common` checks for all stacks.
   - Include stack-specific checks for each active stack.

3. **Generate primary CI workflow** — create provider-appropriate CI configuration.
   - **GitHub Actions**: `.github/workflows/ci.yml` with matrix strategy across active stacks.
   - **Azure Pipelines**: `azure-pipelines.yml` with stages and templates in `pipelines/templates/`.
   - Jobs/stages: lint → build → test → security.
   - Common checks run once (gitleaks, semgrep).
   - Stack-specific checks run per matrix entry / stage.
    - Coverage upload as artifact.
    - If Sonar is configured (`ai-eng setup sonar` with project key), include Sonar analysis in primary `ci.yml`.
      - GitHub: SonarCloud/SonarQube scan action based on configured host URL.
      - Azure: SonarCloud/SonarQube Prepare/Analyze/Publish tasks with service-connection fallback.

3b. **Generate deployment configuration** (if applicable) — create platform-specific deploy config.
   - **Railway**: `railway.toml` with build/start commands, health checks.
   - **Cloudflare Workers/Pages**: `wrangler.toml` with compatibility date, bindings, routes.
   - **Vercel**: `vercel.json` with build output, rewrites, env references.
   - **Netlify**: `netlify.toml` with build command, publish directory, redirects.
   - All deployment configs reference environment variables, never inline secrets.

4. **Generate AI PR review workflow** — create provider-specific `ai-pr-review` pipeline.
   - Add `ai-eng review pr --strict` step.
   - High/critical findings are merge-blocking outcomes.
   - Ensure workflow is required by branch policy/build validation.

5. **Generate security workflow** (if DAST/container tools configured) — create `.github/workflows/security.yml`.
   - Trigger: on deployment to staging, or manual dispatch.
   - DAST job: ZAP/Nuclei against staging URL (URL as workflow input).
   - Container scan job: Trivy on built images (image reference as input).
   - Results uploaded as artifacts.

6. **Generate SBOM workflow** (if SBOM skill active) — create `.github/workflows/sbom.yml`.
   - Trigger: on release or manual dispatch.
   - Per-stack SBOM generation.
   - Upload SBOM as release asset.

7. **Validate generated workflows** — check syntax.
   - Run `actionlint` on generated files if available.
   - Verify YAML validity.
   - Report any issues.

8. **Report** — summarize generated files and next steps.
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
- Create-only caveat: existing workflow files are preserved; if already present, use injector snippets or manual edits.

### Post-Action Validation

- After generating CI/CD configuration, validate YAML syntax.
- Run actionlint if available for GitHub Actions workflows.
- If validation fails, fix issues and re-validate (max 3 attempts per iteration limits).

## References

- `standards/framework/cicd/core.md` — CI/CD standards and requirements.
- `manifest.yml` — per-stack enforcement check definitions.
- `standards/framework/stacks/python.md` — Python check details.
- `standards/framework/stacks/dotnet.md` — .NET check details.
- `standards/framework/stacks/nextjs.md` — Next.js check details.
- `standards/framework/stacks/typescript.md` — TypeScript check details.
- `standards/framework/stacks/rust.md` — Rust check details.
- `standards/framework/stacks/azure.md` — Azure Pipelines patterns.
- `standards/framework/stacks/infrastructure.md` — deployment platform patterns.
$ARGUMENTS
