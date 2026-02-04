# Terraform Standards

> Infrastructure as Code conventions for Azure.

---

## Project Structure

```
terraform/
├── main.tf                 # Main configuration
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── providers.tf            # Provider configuration
├── versions.tf             # Version constraints
├── locals.tf               # Local values
├── data.tf                 # Data sources
│
├── modules/                # Reusable modules
│   ├── app-service/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── storage/
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── environments/           # Environment-specific
    ├── dev/
    │   ├── main.tf
    │   └── terraform.tfvars
    ├── staging/
    └── prod/
```

---

## Naming Conventions

### Resources

```hcl
# Pattern: {provider}_{resource_type}
resource "azurerm_resource_group" "main" { }
resource "azurerm_app_service" "api" { }
resource "azurerm_storage_account" "data" { }

# Use meaningful names, not generic "this"
resource "azurerm_app_service" "api_governor" { }  # ✅ Good
resource "azurerm_app_service" "this" { }          # ❌ Avoid
```

### Azure Resource Names

```hcl
# Pattern: {prefix}-{project}-{environment}-{resource_type}-{optional_suffix}
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

resource "azurerm_storage_account" "data" {
  # Storage accounts: lowercase, no hyphens, max 24 chars
  name = "st${replace(local.resource_prefix, "-", "")}data"
}
```

---

## Variables

### variables.tf

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

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

# Complex variable with validation
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

```hcl
variable "database_password" {
  description = "Database admin password"
  type        = string
  sensitive   = true  # Won't show in logs
}
```

---

## Outputs

```hcl
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "app_service_url" {
  description = "URL of the App Service"
  value       = "https://${azurerm_app_service.api.default_site_hostname}"
}

output "storage_connection_string" {
  description = "Storage account connection string"
  value       = azurerm_storage_account.data.primary_connection_string
  sensitive   = true  # Mark sensitive outputs
}
```

---

## Modules

### Module Definition

```hcl
# modules/app-service/main.tf
resource "azurerm_app_service_plan" "main" {
  name                = "asp-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "Linux"
  reserved            = true

  sku {
    tier = var.sku_tier
    size = var.sku_size
  }

  tags = var.tags
}

resource "azurerm_app_service" "main" {
  name                = "app-${var.name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  app_service_plan_id = azurerm_app_service_plan.main.id

  site_config {
    linux_fx_version = var.linux_fx_version
    always_on        = var.always_on
  }

  app_settings = var.app_settings

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

---

## State Management

### Backend Configuration

```hcl
# versions.tf
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

---

## Tagging

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

---

## Formatting

```bash
# Format all files
terraform fmt -recursive

# Check formatting (CI)
terraform fmt -check -recursive
```

---

## Best Practices

### Do

- ✅ Use version constraints for providers
- ✅ Use remote state with locking
- ✅ Tag all resources
- ✅ Use variables for environment-specific values
- ✅ Use modules for reusable infrastructure
- ✅ Validate variables with conditions

### Don't

- ❌ Hardcode secrets in .tf files
- ❌ Use local state in production
- ❌ Modify state manually
- ❌ Skip `terraform plan` before apply
- ❌ Use `count` when `for_each` is clearer

---

## Commands Reference

```bash
# Initialize
terraform init

# Validate
terraform validate

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan

# Destroy (careful!)
terraform destroy

# State operations
terraform state list
terraform state show azurerm_resource_group.main
```
