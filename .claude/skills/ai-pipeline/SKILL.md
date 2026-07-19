---
name: ai-pipeline
description: "Generates, evolves, and validates CI/CD pipelines for GitHub Actions or Azure Pipelines, enforcing SHA pinning, timeouts, secret handling, and concurrency policy. Trigger for 'set up CI/CD', 'add a deployment pipeline', 'is this workflow secure', 'check workflow policy', 'add a security scan to CI'. Not for running pipelines; that is the CI system's job. Not for governance audits; use /ai-governance instead."
effort: mid
argument-hint: "generate|evolve|validate|--provider github|azure"
tags: [ci-cd, github-actions, azure-pipelines, enterprise]
requires:
  bins: [actionlint]
---

# CI/CD Pipeline

Router skill for CI/CD pipeline generation. Dispatches to a handler by sub-command.

```
/ai-pipeline generate --provider github   # scaffold a new GHA workflow
/ai-pipeline evolve --provider azure      # add patterns to an existing pipeline
/ai-pipeline validate                     # SHA pinning, timeouts, secret handling
```

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `generate` (default) | `handlers/generate.md` | Create new pipeline from project analysis |
| `evolve` | `handlers/evolve.md` | Add advanced patterns to an existing pipeline |
| `validate` | `handlers/validate.md` | Check pipeline compliance (SHA pins, timeouts, concurrency) |

Default (no sub-command): `generate`.

## Process

**Step 0 — load contexts**: read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` for each stack and `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md` for team conventions. Then dispatch to the handler for the resolved sub-command.

## Shared Rules

- **SHA pinning**: all third-party actions use SHA pins. First-party (`actions/*`) may use major tags.
- **No `*` versions**: explicit version constraints always.
- **OIDC auth**: prefer OIDC over long-lived secrets.
- **Timeouts**: every job must have `timeout-minutes`.
- **Concurrency**: group by branch to prevent parallel runs.

## Examples

User: "set up CI/CD for this Python project on GitHub Actions" → `/ai-pipeline generate --provider github`. Reads `providers.stacks` from `manifest.yml`, scaffolds `.github/workflows/ci.yml` with SHA-pinned actions, OIDC auth, timeouts, and concurrency groups; runs `actionlint` to verify.

## Integration

Reads: `providers.stacks` from `.ai-engineering/manifest.yml`. Calls: `actionlint` (GHA), `scripts/check_workflow_policy.py`. See also: `/ai-governance` (validates governance process around pipelines), `/ai-security` (CVE/SBOM scanning).

$ARGUMENTS
