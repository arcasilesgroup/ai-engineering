---
applyTo: "**/*.tf"
---

# Terraform Coding Standards for Copilot

These instructions apply to all Terraform files in this project. Follow these standards when generating or modifying infrastructure code.

## File Organization

Every Terraform root module and child module must follow this file structure:

| File             | Purpose                          |
|-----------------|----------------------------------|
| `main.tf`       | Primary resource definitions     |
| `variables.tf`  | Input variable declarations      |
| `outputs.tf`    | Output value declarations        |
| `providers.tf`  | Provider configuration           |
| `versions.tf`   | Terraform and provider versions  |
| `locals.tf`     | Local value computations         |
| `data.tf`       | Data source lookups              |

Environment-specific configurations go in `environments/{env}/`:

```
terraform/
    main.tf
    variables.tf
    outputs.tf
    providers.tf
    versions.tf
    locals.tf
    data.tf
    modules/
        app-service/
            main.tf
            variables.tf
            outputs.tf
        storage/
            main.tf
            variables.tf
            outputs.tf
    environments/
        dev/
            main.tf
            terraform.tfvars
        staging/
            main.tf
            terraform.tfvars
        prod/
            main.tf
            terraform.tfvars
```

## Naming Conventions

### Terraform Resource Names

Use meaningful, descriptive names. Never use generic names like `this`.

```hcl
# CORRECT
resource "azurerm_app_service" "api_governor" { }
resource "azurerm_resource_group" "main" { }

# WRONG
resource "azurerm_app_service" "this" { }
resource "azurerm_resource_group" "rg" { }
```

### Azure Resource Names

Follow the pattern: `{abbreviation}-{project}-{environment}-{type}-{suffix}`

```hcl
locals {
  resource_prefix = "${var.project}-${var.environment}"
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
}

resource "azurerm_app_service" "api" {
  name = "app-${local.resource_prefix}-api"
}

# Storage accounts: lowercase, no hyphens, max 24 characters
resource "azurerm_storage_account" "data" {
  name = "st${replace(local.resource_prefix, "-", "")}data"
}
```

## Variable Validation

All variables must have a `description`. Use `validation` blocks for constrained values.

```hcl
variable "project" {
  description = "Project name used in resource naming"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "westeurope"
}

variable "app_service_config" {
  description = "App Service configuration"
  type = object({
    sku_name     = string
    worker_count = number
  })
  default = {
    sku_name     = "B1"
    worker_count = 1
  }
  validation {
    condition     = var.app_service_config.worker_count >= 1
    error_message = "Worker count must be at least 1."
  }
}
```

### Sensitive Variables

Mark sensitive variables and outputs explicitly:

```hcl
variable "database_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true
}

output "storage_connection_string" {
  description = "Storage account connection string"
  value       = azurerm_storage_account.data.primary_connection_string
  sensitive   = true
}
```

## Module Patterns

### Module Definition

Every module must have `variables.tf`, `main.tf`, and `outputs.tf`.

```hcl
# modules/app-service/main.tf
resource "azurerm_app_service_plan" "main" {
  name                = "asp-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name

  sku {
    tier = var.sku_tier
    size = var.sku_size
  }

  tags = var.tags
}
```

### Module Usage

```hcl
module "api_app_service" {
  source = "./modules/app-service"

  name                = "${local.resource_prefix}-api"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  sku_tier         = "Basic"
  sku_size         = "B1"
  linux_fx_version = "DOTNETCORE|8.0"
  always_on        = true

  app_settings = {
    "ASPNETCORE_ENVIRONMENT" = var.environment
  }

  tags = local.common_tags
}
```

## State Management

- Always use remote state with locking in non-local environments
- Use Azure Storage backend for state files
- Never modify state manually; use `terraform state` commands when necessary

```hcl
terraform {
  required_version = ">= 1.5.0"

  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "stterraformstate"
    container_name       = "tfstate"
    key                  = "project.terraform.tfstate"
  }

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}
```

## Tagging

Tag all resources with standard tags. Define common tags in `locals.tf`:

```hcl
locals {
  common_tags = {
    Project     = var.project
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner
    CostCenter  = var.cost_center
  }
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.common_tags
}
```

## Iteration

- Prefer `for_each` over `count` when iterating over collections
- Use `count` only for simple conditional resource creation

```hcl
# PREFERRED: for_each with a map
resource "azurerm_app_service" "services" {
  for_each = var.services

  name                = "app-${local.resource_prefix}-${each.key}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  app_service_plan_id = azurerm_app_service_plan.main.id

  tags = local.common_tags
}
```

## Formatting

- Run `terraform fmt -recursive` before committing
- Use 2-space indentation (Terraform default)
- Align `=` signs within blocks for readability

## Best Practices

- Pin provider versions with `~>` constraints
- Use `terraform plan` before every `terraform apply`
- Use `terraform validate` in CI pipelines
- Keep modules small and focused on a single concern
- Use data sources to reference existing infrastructure
- Never hardcode secrets in `.tf` or `.tfvars` files
- Use variables and secret managers for sensitive values

## Security

- Never commit secrets in `.tfvars` files
- Mark sensitive variables and outputs with `sensitive = true`
- Use Azure Key Vault references for secrets in App Service settings
- Restrict state file access with RBAC
- Enable state file encryption at rest
