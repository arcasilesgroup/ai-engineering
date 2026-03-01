# Framework Azure Cross-Cutting Standard

## Update Metadata

- Rationale: production-grade Azure patterns across Functions, App Service, Logic Apps, Well-Architected Framework, and cloud design patterns for AI-assisted architecture and implementation.
- Expected gain: consistent Azure service configuration, deployment safety, and architectural decisions aligned with Microsoft best practices.
- Potential impact: any project using Azure services or Azure DevOps gets enforceable patterns for services, pipelines, and security.

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
- **Stages**: `build` > `test` > `security-scan` > `deploy-staging` > `approval` > `deploy-prod`.
- **Caching**: cache node_modules, NuGet packages, pip cache between runs.

## Azure Functions Patterns

- **Isolated worker model**: default for .NET 8+. Not in-process hosting model (deprecated).
- **Triggers**: HTTP, Timer (NCRONTAB: `0 */5 * * * *`), Queue (`QueueTrigger`), Blob (`BlobTrigger`), Event Grid, Cosmos DB change feed, Service Bus.
- **Bindings**: input/output bindings reduce boilerplate for storage, queues, and tables. Prefer bindings over manual SDK calls for simple operations.
- **Durable Functions**: orchestration patterns — function chaining, fan-out/fan-in, human interaction (approval workflows), monitoring (polling loops), eternal orchestrations.
- **Cold start mitigation**: Premium plan or Dedicated plan for production workloads. Keep-alive pings via Timer trigger for Consumption plan. Minimize startup dependencies.
- **Configuration**: `local.settings.json` for local development (gitignored). App Settings for deployed environments. Key Vault references for secrets.
- **Scaling**: Consumption plan auto-scales per trigger type. Configure `maxConcurrentRequests` (HTTP), `batchSize` (Queue), `maxPollingInterval` (Queue/Cosmos).
- **Idempotency**: design all function handlers to be idempotent. Use deduplication IDs for message-triggered functions.

## App Service Patterns

- **Deployment slots**: blue/green deployment via staging slot > production swap. Warm up staging before swap (`applicationInitialization`).
- **Health check endpoint**: `/healthz` configured in App Service Health Check blade. Unhealthy instances removed from load balancer after threshold.
- **Auto-scaling**: rules based on CPU, memory, HTTP queue length, or custom metrics. Minimum 2 instances for production (availability).
- **Always On**: enable for production plans (prevents idle shutdown on Basic+ tiers).
- **Managed identity**: system-assigned for Key Vault, Storage, SQL Database access. No connection strings with passwords in App Settings.
- **Logging**: enable App Service logs and send to Log Analytics workspace. Application Insights for APM.
- **TLS**: enforce HTTPS only. Minimum TLS 1.2. Custom domains with managed certificates.

## Logic Apps Patterns

- **Standard (single-tenant)**: prefer over Consumption (multi-tenant) for enterprise workloads. Better networking, performance, and cost predictability.
- **Connectors**: managed connectors preferred for Azure and Microsoft 365 services. Custom connectors for internal APIs with OpenAPI spec.
- **Error handling**: configure retry policies per action (fixed, exponential, none). Use `runAfter` with `Failed`/`TimedOut` for failure handling paths.
- **Stateful vs stateless**: stateful workflows for long-running orchestrations with durable state. Stateless for high-throughput request-response (no run history).
- **Concurrency control**: set concurrency limits on triggers to prevent overloading downstream systems.
- **Monitoring**: enable diagnostic logs. Use tracked properties for custom telemetry in Application Insights.

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

- **Managed identities**: prefer system-assigned for single-resource scenarios, user-assigned for shared access across multiple resources.
- **Network**: use Private Endpoints for database and storage access. VNet integration for compute services.
- **TLS**: enforce TLS 1.2+ on all services. Disable HTTP access to storage accounts.
- **Diagnostic logging**: enable diagnostic settings on all resources. Send to Log Analytics workspace.
- **Microsoft Defender for Cloud**: enable on subscription. Review security score monthly.
- **WAF**: Azure Front Door or Application Gateway WAF for internet-facing APIs.

## Well-Architected Framework References

Azure architecture decisions should align with the five pillars:

- **Reliability**: redundancy, fault tolerance, disaster recovery, health modeling. Design for failure.
- **Security**: zero trust, defense in depth, identity-centric access, encryption at rest and in transit.
- **Cost Optimization**: right-sizing, reserved instances, auto-scaling, cost alerts, resource tagging for cost allocation.
- **Operational Excellence**: IaC, monitoring, alerting, incident response, deployment automation, safe deployment practices.
- **Performance Efficiency**: scaling strategy, caching, CDN, async processing, database tuning, load testing.

Use the Azure Well-Architected Review tool for service-level assessments.

## Cloud Design Pattern References

Key patterns agents should recognize and apply:

- **Circuit Breaker**: prevent cascading failures by failing fast when downstream is unhealthy.
- **Retry**: handle transient faults with exponential backoff and jitter.
- **Cache-Aside**: load data into cache on demand, invalidate on write.
- **CQRS**: separate read and write models for complex domains.
- **Event Sourcing**: persist state as a sequence of events, replay for current state.
- **Saga**: manage distributed transactions with compensating actions.
- **Bulkhead**: isolate resources per workload to prevent noisy neighbor failures.
- **Throttling**: limit request rate to protect backend services.
- **Queue-Based Load Leveling**: buffer requests via queue to smooth traffic spikes.
- **Health Endpoint Monitoring**: expose health status for load balancer and orchestrator consumption.
- **Strangler Fig**: incrementally migrate legacy systems by routing traffic to new implementation.
- **Gateway Aggregation**: combine multiple backend calls into a single frontend response.
- **Gateway Routing**: route requests to different backends based on URL path or header.
- **Valet Key**: issue limited-access tokens (SAS) for direct client-to-storage access.
- **Claim Check**: store large payloads in blob storage, pass reference through messaging.
- **Competing Consumers**: scale message processing with multiple consumer instances.
- **Sidecar**: deploy helper processes alongside the main application container.

## Update Contract

This file is framework-managed and may be updated by framework releases.
