# Terraform/Infrastructure Learnings

Stack-specific learnings for Terraform and Azure infrastructure management.

---

## Terraform Patterns

### [2024-01] State Management

**Context:** Managing Terraform state files
**Learning:** Always use remote state with locking (Azure Storage + blob lease)
**Consequence:** Local state or unlocked remote state leads to conflicts and corruption

---

### [2024-01] Module Versioning

**Context:** Using shared Terraform modules
**Learning:** Always pin module versions, never use `main` branch directly
```hcl
# ✅ Pinned version
module "storage" {
  source  = "git::https://repo.git//modules/storage?ref=v1.2.0"
}

# ❌ Unpinned - breaks unexpectedly
module "storage" {
  source  = "git::https://repo.git//modules/storage"
}
```

---

### [2024-02] Resource Naming with locals

**Context:** Consistent resource naming
**Learning:** Define naming convention in `locals` block, not inline
```hcl
locals {
  name_prefix = "${var.project}-${var.environment}"
  resource_name = "${local.name_prefix}-${var.component}"
}

resource "azurerm_resource_group" "main" {
  name = "${local.resource_name}-rg"
}
```

---

## Azure Resources

### [2024-01] Soft Delete Recovery

**Context:** Key Vault and Storage Account deletion
**Learning:** Resources with soft-delete require purge before recreation with same name
```bash
# Key Vault
az keyvault purge --name <name>

# Storage Account - check soft delete policy
az storage account show-deleted --name <name>
```

---

### [2024-02] RBAC Assignment Timing

**Context:** Creating resources with RBAC assignments
**Learning:** RBAC assignments may take 5-15 minutes to propagate
**Workaround:** Add `depends_on` and consider retry logic in subsequent resources

---

### [2024-02] Private Endpoints DNS

**Context:** Configuring private endpoints
**Learning:** Always create private DNS zones and link to VNet
**Consequence:** Without DNS, private endpoint resolution fails

---

## CI/CD Integration

### [2024-01] Plan Output Artifact

**Context:** Terraform in Azure DevOps pipelines
**Learning:** Save plan as artifact, apply from artifact (not re-plan)
```yaml
# Plan stage
- task: TerraformTaskV4@4
  inputs:
    command: 'plan'
    commandOptions: '-out=tfplan'

# Apply stage (separate job)
- task: TerraformTaskV4@4
  inputs:
    command: 'apply'
    commandOptions: 'tfplan'
```
**Rationale:** Ensures apply matches reviewed plan exactly

---

### [2024-02] Sensitive Variable Handling

**Context:** Passing secrets to Terraform
**Learning:** Use Azure Key Vault references, not pipeline variables for secrets
```hcl
data "azurerm_key_vault_secret" "db_password" {
  name         = "db-admin-password"
  key_vault_id = data.azurerm_key_vault.main.id
}
```

---

## Cost Management

### [2024-01] Tag All Resources

**Context:** Cost tracking and accountability
**Learning:** Apply mandatory tags via `default_tags` provider configuration
```hcl
provider "azurerm" {
  features {}
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project
      CostCenter  = var.cost_center
      ManagedBy   = "Terraform"
    }
  }
}
```

---

### [2024-02] Dev/Test Sizing

**Context:** Non-production environments
**Learning:** Use smaller SKUs for dev/test, parameterize via variables
```hcl
variable "app_service_sku" {
  type = map(string)
  default = {
    dev  = "B1"
    test = "B2"
    acc  = "S1"
    prod = "P1v2"
  }
}
```

---

## Troubleshooting

### [2024-01] State Drift Detection

**Context:** Resources modified outside Terraform
**Learning:** Run `terraform plan` regularly to detect drift
**Automation:** Schedule drift detection in CI pipeline

---

### [2024-02] Import Existing Resources

**Context:** Bringing existing resources under Terraform management
**Learning:** Use `terraform import` with corresponding resource block already written
```bash
# 1. Write resource block first
# 2. Import
terraform import azurerm_resource_group.existing /subscriptions/.../resourceGroups/my-rg
# 3. Run plan to verify state matches config
```

---

## Adding New Learnings

When a Terraform/infrastructure pattern emerges:

1. Add entry with date header
2. Include context, learning, and examples
3. Note Azure-specific vs general Terraform patterns
4. Consider if it affects existing modules
