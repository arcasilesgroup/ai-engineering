# Azure Standards

> Azure resource patterns and naming conventions.

---

## Naming Conventions

### Resource Naming Pattern

```
{resource-type}-{project}-{environment}-{region}-{instance}
```

### Resource Type Abbreviations

| Resource Type | Abbreviation | Example |
|---------------|--------------|---------|
| Resource Group | rg | `rg-{project}-prod-weu` |
| App Service | app | `app-{project}-prod-weu` |
| App Service Plan | asp | `asp-{project}-prod-weu` |
| Function App | func | `func-{project}-prod-weu` |
| Storage Account | st | `st{project}prodweu` |
| Key Vault | kv | `kv-{project}-prod-weu` |
| Application Insights | appi | `appi-{project}-prod-weu` |
| API Management | apim | `apim-{project}-prod-weu` |
| Virtual Network | vnet | `vnet-{project}-prod-weu` |
| Subnet | snet | `snet-{project}-prod-weu` |
| Network Security Group | nsg | `nsg-{project}-prod-weu` |
| SQL Server | sql | `sql-{project}-prod-weu` |
| SQL Database | sqldb | `sqldb-{project}-prod-weu` |
| Cosmos DB | cosmos | `cosmos-{project}-prod-weu` |
| Service Bus | sb | `sb-{project}-prod-weu` |
| Event Hub | evh | `evh-{project}-prod-weu` |

### Environment Abbreviations

| Environment | Abbreviation |
|-------------|--------------|
| Development | dev |
| Integration | int |
| Staging/Acceptance | stg / acc |
| Production | prod |

### Region Abbreviations

| Region | Abbreviation |
|--------|--------------|
| West Europe | weu |
| North Europe | neu |
| East US | eus |
| West US | wus |

---

## Resource Group Organization

### By Environment

```
rg-{project}-{environment}
├── All resources for that environment
```

### By Component (large projects)

```
rg-{project}-{component}-{environment}
├── rg-{project}-api-prod
├── rg-{project}-data-prod
└── rg-{project}-infra-prod
```

---

## Tagging Strategy

### Required Tags

| Tag | Description | Example |
|-----|-------------|---------|
| `Project` | Project name | `{ProjectName}` |
| `Environment` | Environment | `Production` |
| `Owner` | Team or person | `platform-team` |
| `CostCenter` | Cost allocation | `IT-12345` |
| `ManagedBy` | Deployment method | `Terraform` |

### Optional Tags

| Tag | Description | Example |
|-----|-------------|----------|
| `Application` | Application name | `WebPortal` |
| `DataClassification` | Data sensitivity | `Confidential` |
| `ExpirationDate` | For temporary resources | `2024-12-31` |
| `SLA` | Service level | `99.9` |

---

## App Service Configuration

### Standard Settings

```json
{
  "ASPNETCORE_ENVIRONMENT": "Production",
  "WEBSITE_TIME_ZONE": "W. Europe Standard Time",
  "APPINSIGHTS_INSTRUMENTATIONKEY": "@Microsoft.KeyVault(SecretUri=...)"
}
```

### Health Check

```
/health          # Liveness probe
/health/ready    # Readiness probe
```

---

## Key Vault

### Secret Naming

```
{application}-{purpose}--{optional-qualifier}
```

Examples:
- `{project}-database--connection-string`
- `{project}-externalapi--api-key`
- `common-sendgrid--api-key`

### Access Patterns

```
✅ Use Managed Identity
✅ Use Key Vault References in App Settings
❌ Never store secrets in code or config files
```

---

## Application Insights

### Naming

```
appi-{project}-{environment}-{region}
```

### Log Analytics Workspace

```
log-{project}-{environment}-{region}
```

Tip: Share Log Analytics workspace across related resources for unified monitoring.

---

## Network Security

### Standard NSG Rules

| Priority | Name | Direction | Action | Source | Destination | Port |
|----------|------|-----------|--------|--------|-------------|------|
| 100 | AllowHTTPS | Inbound | Allow | Internet | VNet | 443 |
| 200 | AllowHealthProbes | Inbound | Allow | AzureLoadBalancer | * | * |
| 4096 | DenyAllInbound | Inbound | Deny | * | * | * |

---

## Cost Optimization

### Development Environments

- Use Basic/Standard tiers
- Enable auto-shutdown
- Use reserved capacity for predictable workloads
- Consider spot instances for non-critical workloads

### Production Environments

- Use Premium tiers for SLA requirements
- Enable auto-scaling
- Use reserved instances (1-3 year) for cost savings
- Enable diagnostic settings for monitoring

---

## Compliance

### Data Residency

- Keep data in approved regions (e.g., West Europe for EU)
- Document data flows across regions
- Use Azure Policy to enforce location constraints

### Security Baseline

- Enable Azure Defender for Cloud
- Enable diagnostic logging
- Use private endpoints where possible
- Enable TLS 1.2 minimum
- Use managed identities over service principals
