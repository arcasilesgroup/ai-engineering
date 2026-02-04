# TFLint Configuration Standard

> Terraform linter with Azure provider plugin and security rules.

---

## Installation

```bash
# macOS
brew install tflint

# Windows (Chocolatey)
choco install tflint

# Linux
curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
```

### Install Plugins

```bash
# Initialize plugins from config
tflint --init
```

---

## Configuration Template

```hcl
# .tflint.hcl

tflint {
  required_version = ">= 0.50"
}

# =============================================================================
# GLOBAL CONFIG
# =============================================================================
config {
  # Output format: default, json, checkstyle, junit, compact, sarif
  format = "compact"

  # Module inspection
  call_module_type = "local"  # local, all, none

  # Force run even with errors
  force = false

  # Disable all rules by default (enable explicitly)
  disabled_by_default = false
}

# =============================================================================
# AZURE PROVIDER PLUGIN
# =============================================================================
plugin "azurerm" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

# =============================================================================
# TERRAFORM LANGUAGE RULES
# =============================================================================
plugin "terraform" {
  enabled = true
  preset  = "recommended"  # none, recommended, all
}

# =============================================================================
# TERRAFORM NAMING CONVENTION
# =============================================================================
rule "terraform_naming_convention" {
  enabled = true
  format  = "snake_case"

  # Custom formats per block type
  custom_formats = {
    # Allow hyphens in resource names
    azurerm_resource_group = {
      format = "^[a-z][a-z0-9-]*$"
    }
  }
}

# =============================================================================
# DOCUMENTATION RULES
# =============================================================================
rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}

# =============================================================================
# CODE QUALITY RULES
# =============================================================================
rule "terraform_unused_declarations" {
  enabled = true
}

rule "terraform_unused_required_providers" {
  enabled = true
}

rule "terraform_required_version" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true

  # Require source for all providers
  source = true
}

rule "terraform_standard_module_structure" {
  enabled = true
}

rule "terraform_workspace_remote" {
  enabled = true
}

# =============================================================================
# STYLE RULES
# =============================================================================
rule "terraform_comment_syntax" {
  enabled = true
}

rule "terraform_deprecated_index" {
  enabled = true
}

rule "terraform_deprecated_interpolation" {
  enabled = true
}

rule "terraform_empty_list_equality" {
  enabled = true
}

rule "terraform_module_pinned_source" {
  enabled = true

  # Enforce version constraints
  style                        = "flexible"  # flexible, semver
  default_branches             = ["main", "master"]
}

rule "terraform_typed_variables" {
  enabled = true
}

# =============================================================================
# AZURE-SPECIFIC RULES
# =============================================================================

# Validate Azure resource naming
rule "azurerm_resource_missing_tags" {
  enabled = true
  tags    = ["Environment", "Project", "Owner"]
}

# =============================================================================
# DISABLED RULES (with reason)
# =============================================================================

# Disabled: We use dynamic blocks intentionally
# rule "terraform_dynamic_blocks" {
#   enabled = false
# }
```

---

## Module-Level Config

For modules, create a `.tflint.hcl` in each module:

```hcl
# modules/storage/.tflint.hcl

# Inherit from root config
config {
  call_module_type = "none"  # Don't inspect nested modules
}

# Module-specific rules
rule "terraform_standard_module_structure" {
  enabled = true
}
```

---

## Checkov Integration (Security)

```yaml
# .checkov.yml
compact: true
directory:
  - infrastructure/
framework:
  - terraform
check:
  # Azure best practices
  - CKV_AZURE_1   # Storage secure transfer required
  - CKV_AZURE_2   # Storage logging enabled
  - CKV_AZURE_3   # Storage encryption enabled
  - CKV_AZURE_4   # AKS logging enabled
  - CKV_AZURE_5   # AKS dashboard disabled
  - CKV_AZURE_6   # AKS network policy
  - CKV_AZURE_7   # AKS private cluster
  - CKV_AZURE_8   # AKS RBAC enabled
  - CKV_AZURE_9   # AKS secrets encryption
  - CKV_AZURE_10  # Key Vault purge protection
skip-check:
  - CKV_AZURE_35  # Skip: Storage public access (intentional for CDN)
soft-fail: false
output:
  - cli
  - sarif
```

---

## Verification Commands

```bash
# Initialize plugins
tflint --init

# Lint current directory
tflint

# Lint with specific config
tflint --config=.tflint.hcl

# Lint recursively (all modules)
tflint --recursive

# Output as JSON (for CI)
tflint --format=json

# Specific directory
tflint infrastructure/

# Combined with terraform fmt check
terraform fmt -check -recursive
tflint --recursive
```

---

## Azure Pipeline Integration

```yaml
# templates/steps/terraform-lint.yml
steps:
  - script: |
      terraform fmt -check -recursive -diff
    displayName: 'Terraform Format Check'

  - script: |
      curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
      tflint --init
      tflint --recursive --format=compact
    displayName: 'TFLint'

  - script: |
      pip install checkov
      checkov -d infrastructure/ --output cli --output sarif --output-file-path . --soft-fail
    displayName: 'Checkov Security Scan'

  - task: PublishBuildArtifacts@1
    inputs:
      pathToPublish: 'results_sarif.sarif'
      artifactName: 'checkov-results'
    condition: always()
```

---

## Pre-commit Integration

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/antonbabenko/pre-commit-terraform
    rev: v1.92.0
    hooks:
      - id: terraform_fmt
      - id: terraform_validate
      - id: terraform_tflint
        args:
          - --args=--config=__GIT_WORKING_DIR__/.tflint.hcl
      - id: terraform_checkov
        args:
          - --args=--quiet
          - --args=--compact
```

---

## VS Code Integration

```json
// .vscode/settings.json
{
  "terraform.languageServer.enable": true,
  "terraform.codelens.referenceCount": true,
  "[terraform]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "hashicorp.terraform"
  },
  "[terraform-vars]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "hashicorp.terraform"
  }
}
```
