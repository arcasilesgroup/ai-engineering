---
name: infra
description: "Design and generate Infrastructure as Code (Terraform, Bicep) with plan-before-apply safety, state management, and deployment configuration."
metadata:
  version: 1.0.0
  tags: [infrastructure, iac, terraform, bicep, cloud, deployment]
  ai-engineering:
    scope: read-write
    token_estimate: 850
---

# Infrastructure

## Purpose

Infrastructure as Code design and generation skill. Covers Terraform, Bicep, and platform deployment configuration with mandatory plan-before-apply safety, state management, and blast radius minimization. Ensures infrastructure is reproducible, secure, and auditable.

## Trigger

- Command: agent invokes infrastructure skill or user requests IaC design/generation.
- Context: new cloud resource provisioning, infrastructure migration, deployment platform setup, container configuration, network architecture.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"infra"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **CI/CD pipeline generation** — use `cicd` instead. This skill generates infrastructure, not pipelines.
- **Application deployment** — use `cicd` for deploy workflows. This skill generates deployment config, not execution.
- **Security review of infrastructure** — use `sec-review` for IaC scanning and cloud security audit.
- **Database provisioning only** — use `db` for schema design. Use this skill for database server provisioning.

## Procedure

1. **Understand requirements** — identify what infrastructure is needed.
   - Cloud provider (Azure, AWS, GCP) or platform (Railway, Cloudflare, Vercel).
   - Resource types: compute, storage, database, networking, CDN, DNS.
   - Environment structure: dev, staging, production.
   - Load `standards/framework/stacks/infrastructure.md` for patterns.

2. **Design architecture** — produce infrastructure design.
   - Resource naming following provider conventions (see `stacks/azure.md` for Azure).
   - Module decomposition: one module per bounded context.
   - Environment separation: per-environment state files or parameter files.
   - Network topology: VNets, subnets, NSGs, private endpoints.

3. **Generate IaC** — produce Infrastructure as Code files.
   - **Terraform**: `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`.
   - **Bicep**: `main.bicep` + `main.<env>.bicepparam`.
   - Pin provider versions. No hardcoded values. Secrets from Key Vault/Secrets Manager.
   - Apply tagging strategy: `environment`, `project`, `managed-by`.

4. **Generate deployment config** (if platform deployment).
   - Railway: `railway.toml` with build/deploy settings.
   - Cloudflare: `wrangler.toml` with bindings and compatibility date.
   - Vercel: `vercel.json` with rewrites and env references.
   - Docker: multi-stage Dockerfile, non-root user, minimal base image.

5. **Plan validation** — verify before applying.
   - Terraform: `terraform plan` output review.
   - Bicep: `az deployment group what-if` review.
   - Flag destructive changes (resource replacement, deletion).
   - Estimate cost impact if possible.

6. **State management** — configure remote state.
   - Terraform: remote backend with locking (Azure Storage, S3, Terraform Cloud).
   - Never commit state files to version control.
   - State encryption at rest and in transit.

## Output Contract

- IaC files (Terraform, Bicep, or platform config).
- Architecture diagram (textual or mermaid).
- Plan output with change summary.
- Cost estimate (when tooling supports it).
- Operational notes: provisioning steps, rollback procedures.

## Governance Notes

- Plan-before-apply is mandatory. Never auto-apply infrastructure changes.
- Destructive changes (resource deletion/replacement) require explicit user approval.
- Secrets must go to secrets manager, never in IaC files.
- Generated IaC is project-managed — the skill generates, the project maintains.

### Iteration Limits

- Max 3 attempts to resolve the same infrastructure issue. After 3 failures, escalate to user with evidence.

### Post-Action Validation

- After generating IaC, run `terraform fmt`/`terraform validate` or `az bicep lint`.
- Verify YAML/TOML syntax for platform configs.
- If validation fails, fix issues and re-validate (max 3 attempts).

## References

- `standards/framework/stacks/infrastructure.md` — IaC patterns and safety rules.
- `standards/framework/stacks/azure.md` — Azure-specific patterns.
- `agents/build.md` — implementation agent that designs infrastructure.
