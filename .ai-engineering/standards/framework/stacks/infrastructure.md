# Framework Infrastructure Cross-Cutting Standard

## Update Metadata

- Rationale: establish IaC, cloud provisioning, and deployment platform patterns for multi-cloud operations.
- Expected gain: consistent infrastructure management across Terraform, Bicep, Railway, Cloudflare, and other platforms.
- Potential impact: any project with infrastructure components gets enforceable IaC and deployment patterns.

## Standard Type

Cross-cutting standard. Applies alongside a primary stack standard. Does not define its own enforcement gates.

## Scope

- Infrastructure as Code: Terraform, Bicep, Pulumi, CloudFormation.
- Deployment platforms: Railway, Cloudflare Workers/Pages, Vercel, Netlify.
- Container orchestration: Docker, Kubernetes, Docker Compose.
- DNS and CDN management.
- Workflow automation: n8n, GitHub Actions, Azure Pipelines.
- Documentation platforms: Mintlify, Nextra, Docusaurus.

## IaC Core Patterns

- **Plan before apply**: always run `terraform plan` / `bicep what-if` before applying. Review changes.
- **State management**: remote state with locking (Terraform Cloud, Azure Storage, S3). Never commit state files.
- **Modules**: reusable modules for repeated infrastructure (networking, compute, storage). Version modules.
- **Environments**: separate state per environment. Use workspaces (Terraform) or parameter files (Bicep).
- **Variables**: no hardcoded values. Use variables with type constraints and descriptions.
- **Outputs**: export resource IDs, endpoints, and connection strings for downstream consumption.
- **Naming**: consistent resource naming convention across all IaC (see Azure standard for Azure resources).

## IaC Safety Rules

- **Destructive changes**: any resource replacement or deletion requires explicit approval.
- **Drift detection**: schedule periodic `terraform plan` runs to detect manual changes.
- **Rollback**: maintain ability to roll back to previous infrastructure state. Tag releases.
- **Secrets**: never in IaC files. Reference from Key Vault, Secrets Manager, or environment variables.
- **Blast radius**: limit the scope of each IaC module. One module per bounded context.

## Terraform Patterns

- Provider versions pinned in `required_providers`.
- Backend configured for remote state with encryption.
- `terraform fmt` enforced in CI.
- `tflint` and `tfsec` (or `checkov`) in pre-push gates.
- Module structure: `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf`, `versions.tf`.

## Bicep Patterns

- Bicep files organized by resource group deployment scope.
- Parameter files per environment: `main.dev.bicepparam`, `main.prod.bicepparam`.
- Use `@description()` decorator on all parameters and outputs.
- `az bicep lint` enforced in CI.

## Deployment Platforms

### Railway

- `railway.toml` for service configuration. Define build and start commands.
- Environment variables via Railway dashboard or CLI (`railway variables set`).
- Use Railway volumes for persistent storage.
- Health checks configured for automatic restart.

### Cloudflare Workers/Pages

- `wrangler.toml` for Worker configuration. Define compatibility dates.
- Use D1 for SQL, KV for key-value, R2 for object storage.
- Pages: connect to Git repo for automatic deployments.
- Workers: use module syntax (`export default { fetch() {} }`).

### Vercel/Netlify

- Configuration via `vercel.json` or `netlify.toml`.
- Environment variables in platform dashboard, not committed to repo.
- Preview deployments for PRs. Production deploys from main branch only.

## Container Patterns

- **Dockerfile**: multi-stage builds. Non-root user. Minimal base image (distroless, alpine).
- **Docker Compose**: for local development. Match production topology.
- **Health checks**: `HEALTHCHECK` instruction in Dockerfile.
- **Image scanning**: Trivy or Grype in CI pipeline.
- **Registry**: tag with semver and git SHA. Never use `latest` in production.

## n8n Workflow Patterns

- Export workflows as JSON. Version control in repo.
- Use credentials store, not hardcoded secrets.
- Error handling: configure error workflow for failure notifications.
- Naming: descriptive workflow and node names. Group related workflows.

## Mintlify Documentation Patterns

- `mint.json` for site configuration (navigation, theme, API references).
- MDX files for content pages. Organize by section.
- OpenAPI spec integration for API reference docs.
- Version control docs alongside code in monorepo or dedicated docs repo.

## DNS and CDN

- DNS records managed via IaC (Terraform/Cloudflare API), not manual dashboard.
- CDN: cache static assets. Configure cache headers. Purge on deploy.
- SSL/TLS: automated certificate provisioning (Let's Encrypt, Cloudflare).
- Monitoring: uptime checks on critical endpoints.

## Update Contract

This file is framework-managed and may be updated by framework releases.
