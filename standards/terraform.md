# Terraform Standards

> Consolidated Terraform standards: file organization, naming, modules, state management, security, and Azure patterns.

---

## 1. File Organization

Every Terraform root module and child module must follow this structure:

```
modules/
  my-module/
    main.tf           # Resource definitions
    variables.tf      # Input variable declarations
    outputs.tf        # Output value declarations
    providers.tf      # Provider configuration (root only)
    versions.tf       # Required providers and Terraform version
    locals.tf         # Local values and computed expressions
    data.tf           # Data source lookups
    README.md         # Module documentation
```

### File Responsibilities

| File | Contains | Never Contains |
|------|----------|----------------|
| `main.tf` | Resource blocks, module calls | Variable declarations, outputs |
| `variables.tf` | All `variable` blocks with descriptions | Resource definitions |
| `outputs.tf` | All `output` blocks with descriptions | Variable declarations |
| `providers.tf` | `provider` blocks, backend config | Resource definitions |
| `versions.tf` | `terraform.required_providers` | Resource definitions |
| `locals.tf` | `locals` blocks for computed values | Resource definitions |
| `data.tf` | `data` source blocks | Resource definitions |

---

## 2. Naming Conventions

### Resources and Data Sources

Use **snake_case** for all identifiers:

```hcl
# GOOD: Descriptive snake_case names
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location
}

resource "azurerm_key_vault" "app_secrets" {
  name                = "${var.project_name}-${var.environment}-kv"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku_name            = "standard"
  tenant_id           = data.azurerm_client_config.current.tenant_id
}

# BAD: Inconsistent naming
resource "azurerm_resource_group" "MyResourceGroup" { ... }
resource "azurerm_key_vault" "keyVault1" { ... }
```

### Naming Convention Table

| Element | Convention | Example |
|---------|------------|---------|
| Resources | snake_case | `azurerm_storage_account.app_data` |
| Variables | snake_case | `var.resource_group_name` |
| Outputs | snake_case | `output.storage_account_id` |
| Locals | snake_case | `local.common_tags` |
| Modules | snake_case | `module.networking` |
| Files | kebab-case or snake_case | `main.tf`, `variables.tf` |
| Azure resource names | kebab-case with prefix | `myapp-prod-rg`, `myapp-prod-kv` |

---

## 3. Module Structure

### Root Module Calling Child Modules

```hcl
# main.tf (root)
module "networking" {
  source = "./modules/networking"

  project_name = var.project_name
  environment  = var.environment
  location     = var.location
  address_space = var.vnet_address_space
}

module "app_service" {
  source = "./modules/app-service"

  project_name        = var.project_name
  environment         = var.environment
  location            = var.location
  resource_group_name = module.networking.resource_group_name
  subnet_id           = module.networking.app_subnet_id
}
```

### Child Module Design Principles

- Accept only what the module needs (no passing entire objects)
- Output only what consumers need
- Never hardcode environment-specific values
- Include validation on all input variables
- Document with a README and examples

---

## 4. Variable Definitions and Validation

```hcl
# variables.tf
variable "environment" {
  description = "Deployment environment (dev, int, acc, pro)"
  type        = string

  validation {
    condition     = contains(["dev", "int", "acc", "pro"], var.environment)
    error_message = "Environment must be one of: dev, int, acc, pro."
  }
}

variable "location" {
  description = "Azure region for resource deployment"
  type        = string
  default     = "westeurope"

  validation {
    condition     = can(regex("^(westeurope|northeurope|eastus2)$", var.location))
    error_message = "Location must be an approved Azure region."
  }
}

variable "app_settings" {
  description = "Application settings key-value pairs"
  type        = map(string)
  default     = {}
  sensitive   = false
}

variable "database_password" {
  description = "Database administrator password"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.database_password) >= 16
    error_message = "Database password must be at least 16 characters."
  }
}
```

---

## 5. State Management

### Remote Backend (Azure)

```hcl
# providers.tf
terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstatestore"
    container_name       = "tfstate"
    key                  = "myapp/production.tfstate"
  }
}
```

### State Management Rules

| Rule | Reason |
|------|--------|
| Always use remote backend | Team collaboration, locking, durability |
| One state file per environment | Isolate blast radius |
| Enable state locking | Prevent concurrent modifications |
| Enable versioning on state storage | Recovery from corruption |
| Never store state in Git | Contains secrets in plaintext |
| Use `terraform_remote_state` sparingly | Prefer explicit variable passing |

---

## 6. Outputs

```hcl
# outputs.tf
output "resource_group_name" {
  description = "Name of the created resource group"
  value       = azurerm_resource_group.main.name
}

output "key_vault_uri" {
  description = "URI of the Key Vault for secret retrieval"
  value       = azurerm_key_vault.app_secrets.vault_uri
}

output "connection_string" {
  description = "Database connection string"
  value       = azurerm_mssql_database.main.connection_string
  sensitive   = true
}
```

---

## 7. Azure Resource Patterns

### Tagging Strategy

```hcl
# locals.tf
locals {
  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
    cost_center = var.cost_center
    owner       = var.team_email
  }
}

# Usage in resources
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location
  tags     = local.common_tags
}
```

### Required Tags

| Tag | Purpose | Example |
|-----|---------|---------|
| `project` | Project identification | `myapp` |
| `environment` | Environment tier | `dev`, `pro` |
| `managed_by` | Provisioning tool | `terraform` |
| `cost_center` | Billing attribution | `engineering-42` |
| `owner` | Team contact | `team-platform@company.com` |

### Resource Group Pattern

```hcl
# One resource group per application per environment
resource "azurerm_resource_group" "main" {
  name     = "${var.project_name}-${var.environment}-rg"
  location = var.location
  tags     = local.common_tags

  lifecycle {
    prevent_destroy = true
  }
}
```

---

## 8. Security

### Never Store Secrets in tfvars

```hcl
# BAD: secrets.tfvars (NEVER do this)
database_password = "SuperSecret123!"
api_key           = "sk-abc123..."

# GOOD: Use environment variables
# export TF_VAR_database_password=$(az keyvault secret show ...)

# GOOD: Use data sources for secrets
data "azurerm_key_vault_secret" "db_password" {
  name         = "database-password"
  key_vault_id = azurerm_key_vault.main.id
}
```

### Security Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| Secrets in `.tfvars` files | Committed to Git | Use Key Vault or env vars |
| Secrets in state file without encryption | Plaintext exposure | Encrypt state backend |
| Overly permissive security groups | Attack surface | Least privilege, specific CIDRs |
| Hardcoded IP addresses | Brittle, insecure | Use variables or data sources |
| Missing `sensitive = true` on outputs | Secrets shown in logs | Mark sensitive outputs |
| Public access on storage accounts | Data exposure | Default deny, private endpoints |

---

## 9. tflint Configuration

```hcl
# .tflint.hcl
config {
  call_module_type = "local"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

plugin "azurerm" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

rule "terraform_typed_variables" {
  enabled = true
}
```

---

## 10. Common Anti-Patterns

| Anti-Pattern | Problem | Correct Approach |
|-------------|---------|-----------------|
| No backend configuration | Local state, no collaboration | Always configure remote backend |
| Monolithic root module | Hard to manage, slow plans | Split into composed modules |
| Using `count` for conditional resources | Fragile index-based references | Use `for_each` with maps |
| No variable descriptions | Unusable modules | Document every variable |
| Missing `terraform.lock.hcl` in Git | Non-reproducible provider versions | Commit the lock file |
| `depends_on` overuse | Hides implicit dependencies | Rely on reference-based ordering |
| Ignoring plan output | Unexpected destroys | Always review `terraform plan` |
