# Description: Azure integration example for lm-cloud-sync.
# Description: Shows SP-only setup and full integration with LM device groups.

terraform {
  required_version = ">= 1.0"

  required_providers {
    azuread = {
      source  = "hashicorp/azuread"
      version = ">= 2.47.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0"
    }
    logicmonitor = {
      source  = "ryanmat/logicmonitor"
      version = ">= 1.0"
    }
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {}

provider "logicmonitor" {
  api_id  = var.lm_api_id
  api_key = var.lm_api_key
  company = var.lm_company
}

# Option 1: SP setup only (use CLI for LM sync)
module "logicmonitor_azure" {
  source = "../../modules/azure"

  subscription_ids = var.subscription_ids

  application_name         = var.application_name
  enable_monitoring_reader = var.enable_monitoring_reader
  enable_log_analytics     = var.enable_log_analytics
}

# Option 2: SP setup + LM device groups in one module
# module "logicmonitor_azure_full" {
#   source = "../../modules/azure"
#
#   subscription_ids = var.subscription_ids
#
#   # Enable LM integration -- creates device groups for each subscription
#   enable_lm_integration = true
#   lm_api_id             = var.lm_api_id
#   lm_api_key            = var.lm_api_key
#   lm_company            = var.lm_company
# }

output "tenant_id" {
  description = "Azure AD tenant ID"
  value       = module.logicmonitor_azure.tenant_id
}

output "client_id" {
  description = "Application (client) ID"
  value       = module.logicmonitor_azure.client_id
}

output "client_secret" {
  description = "Client secret (sensitive)"
  value       = module.logicmonitor_azure.client_secret
  sensitive   = true
}

output "setup_instructions" {
  description = "Next steps for lm-cloud-sync"
  value       = module.logicmonitor_azure.setup_instructions
}
