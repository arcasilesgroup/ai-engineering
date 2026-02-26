# Framework Azure Cross-Cutting Standard

## Update Metadata

- Rationale: establish Azure-specific patterns for services, DevOps, Pipelines, and cloud operations.
- Expected gain: consistent Azure resource management, pipeline design, and security patterns.
- Potential impact: any project using Azure services or Azure DevOps gets enforceable patterns.

## Standard Type

Cross-cutting standard. Applies alongside a primary stack standard. Does not define its own enforcement gates.

## Scope

- Azure services: App Service, Functions, Container Apps, Storage, Key Vault, SQL Database, Cosmos DB, Service Bus, Event Grid.
- Azure DevOps: Repos, Pipelines, Boards, Artifacts.
- Azure Pipelines: YAML pipeline authoring, templates, environments.
- Azure CLI and Bicep for resource provisioning.
- Azure identity: Entra ID (Azure AD), service principals, managed identities.

## Azure Resource Patterns

- **Naming convention**: `<project>-<environment>-<resource-type>-<region>` (e.g., `myapp-prod-func-westeu`).
- **Resource groups**: one per environment per project. Tag with `project`, `environment`, `owner`, `cost-center`.
- **Tags**: mandatory tags on all resources: `environment`, `project`, `managed-by` (terraform/bicep/manual).
- **Regions**: prefer West Europe and North Europe for EU compliance. Document region choices.
- **RBAC**: least privilege. Use built-in roles before custom. Assign to groups, not individuals.

## Azure DevOps Patterns

- **Repos**: branch policies on main (require PR, require build, require reviewers).
- **Boards**: link work items to PRs and commits for traceability.
- **Artifacts**: use Azure Artifacts for private package feeds (npm, NuGet, Python).
- **Service connections**: use workload identity federation (not client secrets) for pipeline authentication.

## Azure Pipelines Patterns

- **YAML first**: all pipelines defined in `azure-pipelines.yml` or `pipelines/` directory.
- **Templates**: reusable stages/jobs/steps in `pipelines/templates/`. DRY across environments.
- **Environments**: define environments (dev, staging, prod) with approval gates for production.
- **Variables**: use variable groups for environment-specific config. Secrets in Key Vault-linked variable groups.
- **Stages**: `build` → `test` → `security-scan` → `deploy-staging` → `approval` → `deploy-prod`.
- **Caching**: cache node_modules, NuGet packages, pip cache between runs.

## Key Vault Integration

- Store all secrets in Key Vault, not in pipeline variables or appsettings.
- Use managed identity for Key Vault access from compute (App Service, Functions, Container Apps).
- Reference secrets via `@Microsoft.KeyVault(SecretUri=...)` in App Service configuration.
- Rotate secrets on schedule. Alert on expiring certificates/secrets.

## Azure CLI Patterns

- **Login**: `az login --service-principal` for automation, `az login` with device code for humans.
- **Subscription**: always set subscription context explicitly: `az account set --subscription <id>`.
- **Output**: use `--output json` for parsing, `--output table` for human readability.
- **Idempotency**: use `az resource create --is-full-object` or Bicep for declarative provisioning.

## Security Patterns

- **Managed identities**: prefer system-assigned for single-resource scenarios, user-assigned for shared access.
- **Network**: use Private Endpoints for database and storage access. VNet integration for compute.
- **TLS**: enforce TLS 1.2+ on all services. Disable HTTP access to storage accounts.
- **Diagnostic logging**: enable diagnostic settings on all resources. Send to Log Analytics workspace.
- **Microsoft Defender for Cloud**: enable on subscription. Review security score monthly.

## Update Contract

This file is framework-managed and may be updated by framework releases.
