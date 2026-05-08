---
name: ai-pipeline
description: Generates, evolves, and validates CI/CD pipelines for GitHub Actions or Azure Pipelines, enforcing SHA pinning, timeouts, secret handling, and concurrency policy. Trigger for 'set up CI/CD', 'add a deployment pipeline', 'is this workflow secure', 'check workflow policy', 'add a security scan to CI'. Not for running pipelines; that is the CI system's job. Not for governance audits; use /ai-governance instead.
effort: high
argument-hint: "generate|evolve|validate|--provider github|azure"
tags: [ci-cd, github-actions, azure-pipelines, enterprise]
requires:
  bins:
  - actionlint
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-pipeline/SKILL.md
edit_policy: generated-do-not-edit
---



# CI/CD Pipeline

## Quick start

```
/ai-pipeline generate --provider github   # scaffold a new GHA workflow
/ai-pipeline evolve --provider azure      # add patterns to an existing pipeline
/ai-pipeline validate                     # SHA pinning, timeouts, secret handling
```

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

## Examples

### Example 1 — scaffold a GHA pipeline for a Python repo

User: "set up CI/CD for this Python project on GitHub Actions"

```
/ai-pipeline generate --provider github
```

Reads `providers.stacks` from `manifest.yml`, scaffolds `.github/workflows/ci.yml` with SHA-pinned actions, OIDC auth, timeouts, and concurrency groups; runs `actionlint` to verify.

### Example 2 — validate compliance pre-merge

User: "is the existing workflow secure and policy-compliant?"

```
/ai-pipeline validate
```

Checks SHA pinning of third-party actions, presence of `timeout-minutes`, OIDC auth (vs long-lived secrets), and concurrency groups; reports gaps with remediation hints.

## Integration

Reads: `providers.stacks` from `.ai-engineering/manifest.yml`. Calls: `actionlint` (GHA), `scripts/check_workflow_policy.py`. See also: `/ai-governance` (validates governance process around pipelines), `/ai-security` (CVE/SBOM scanning).

$ARGUMENTS
