# Example: Azure Service Principal setup for lm-cloud-sync
#
# This example shows how to use the Azure module to create
# the Service Principal and credentials needed for LogicMonitor
# Azure cloud integration.

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
  }
}

provider "azurerm" {
  features {}
}

provider "azuread" {}

# Option 1: Specify subscription IDs explicitly
module "logicmonitor_azure" {
  source = "../../modules/azure"

  subscription_ids = var.subscription_ids

  # Optional settings
  application_name         = var.application_name
  enable_monitoring_reader = var.enable_monitoring_reader
  enable_log_analytics     = var.enable_log_analytics
}

# Option 2: Auto-discover all subscriptions in tenant
# data "azurerm_subscriptions" "all" {}
#
# module "logicmonitor_azure_all" {
#   source = "../../modules/azure"
#   subscription_ids = [for s in data.azurerm_subscriptions.all.subscriptions : s.subscription_id]
# }

# Outputs for lm-cloud-sync CLI
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
