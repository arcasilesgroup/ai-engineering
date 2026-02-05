# =============================================================================
# AI Engineering Framework - TFLint Configuration
# =============================================================================
# Place this file as .tflint.hcl in your Terraform project root.
# Then run: tflint --init && tflint
# =============================================================================

config {
  # Check module sources for issues
  call_module_type = "local"

  # Optionally enable all modules (slower but more thorough)
  # call_module_type = "all"
}

# Core Terraform rules
plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

# Azure-specific rules (comment out if not using Azure)
plugin "azurerm" {
  enabled = true
  version = "0.27.0"
  source  = "github.com/terraform-linters/tflint-ruleset-azurerm"
}

# AWS-specific rules (uncomment if using AWS)
# plugin "aws" {
#   enabled = true
#   version = "0.31.0"
#   source  = "github.com/terraform-linters/tflint-ruleset-aws"
# }

# Google Cloud rules (uncomment if using GCP)
# plugin "google" {
#   enabled = true
#   version = "0.28.0"
#   source  = "github.com/terraform-linters/tflint-ruleset-google"
# }
