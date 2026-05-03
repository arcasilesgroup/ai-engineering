---
name: ai-pipeline
description: "Use for CI/CD pipeline work: generating GitHub Actions or Azure Pipelines workflows, evolving existing pipelines, or validating pipeline compliance (SHA pinning, timeouts, secret handling). Trigger for 'set up CI/CD', 'add a deployment pipeline', 'is this workflow secure?', 'check our workflow policy', 'add a security scan to CI'. Providers: GitHub Actions (default), Azure Pipelines."
effort: high
argument-hint: "generate|evolve|validate|--provider github|azure"
tags: [ci-cd, github-actions, azure-pipelines, enterprise]
requires:
  bins:
  - actionlint
---



# CI/CD Pipeline

Router skill for CI/CD pipeline generation. Dispatches to handler files based on sub-command.

## When to Use

- Creating new CI/CD pipelines for a project.
- Evolving existing pipelines with advanced patterns.
- Validating pipeline compliance (SHA pinning, timeouts, concurrency).
- NOT for running pipelines -- that is the CI system's job.

## Process

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Routing

| Sub-command | Handler | Purpose |
|-------------|---------|---------|
| `generate` (default) | `handlers/generate.md` | Create new pipeline from project analysis |
| `evolve` | `handlers/evolve.md` | Add advanced patterns to existing pipeline |
| `validate` | `handlers/validate.md` | Check pipeline compliance |

Default (no sub-command): `generate`.

## Quick Reference

```
/ai-pipeline generate                    # new pipeline from project analysis
/ai-pipeline generate --provider azure   # Azure Pipelines specifically
/ai-pipeline evolve                      # add advanced patterns
/ai-pipeline validate                    # check compliance
```

## Shared Rules

- **SHA pinning**: all third-party actions use SHA pins. First-party (`actions/*`) may use major tags.
- **No `*` versions**: explicit version constraints always.
- **OIDC auth**: prefer OIDC over long-lived secrets.
- **Timeouts**: every job must have `timeout-minutes`.
- **Concurrency**: group by branch to prevent parallel runs.

## Integration

- Stack detection: reads `providers.stacks` from `.ai-engineering/manifest.yml`.
- Validation: `actionlint` for GitHub Actions.
- Policy: `scripts/check_workflow_policy.py` for SHA pinning and timeout compliance.
- **Boundary**: `/ai-governance` validates governance process; `/ai-pipeline` generates and validates the workflow files themselves

References: `.ai-engineering/manifest.yml` (CI/CD standards) and `.ai-engineering/contexts/` (per-stack check definitions).
$ARGUMENTS
