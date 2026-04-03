# Azure Service Principal for LogicMonitor Cloud Integration
# This module creates the Azure AD application, service principal, and role assignments
# required for LogicMonitor to monitor Azure subscriptions.

terraform {
  required_version = ">= 1.0.0"

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

# Data source to get current Azure context
data "azurerm_subscription" "current" {}

data "azuread_client_config" "current" {}

# Create Azure AD Application for LogicMonitor
resource "azuread_application" "logicmonitor" {
  display_name = var.application_name

  # Application owners
  owners = [data.azuread_client_config.current.object_id]

  # API permissions for Azure management
  required_resource_access {
    resource_app_id = "797f4846-ba00-4fd7-ba43-dac1f8f63013" # Azure Service Management

    resource_access {
      id   = "41094075-9dad-400e-a0bd-54e686782033" # user_impersonation
      type = "Scope"
    }
  }

  tags = concat(
    ["LogicMonitor", "CloudMonitoring"],
    var.tags
  )
}

# Create Service Principal for the application
resource "azuread_service_principal" "logicmonitor" {
  client_id = azuread_application.logicmonitor.client_id
  owners    = [data.azuread_client_config.current.object_id]

  tags = concat(
    ["LogicMonitor", "CloudMonitoring"],
    var.tags
  )
}

# Create client secret for the service principal
resource "azuread_application_password" "logicmonitor" {
  application_id = azuread_application.logicmonitor.id
  display_name   = "LogicMonitor Cloud Integration"
  end_date       = var.secret_expiration_date
}

# Assign Reader role to service principal on each subscription
resource "azurerm_role_assignment" "reader" {
  for_each = toset(var.subscription_ids)

  scope                = "/subscriptions/${each.value}"
  role_definition_name = "Reader"
  principal_id         = azuread_service_principal.logicmonitor.object_id

  # Skip if principal doesn't exist yet (eventual consistency)
  skip_service_principal_aad_check = true
}

# Optional: Assign Monitoring Reader role for enhanced metrics access
resource "azurerm_role_assignment" "monitoring_reader" {
  for_each = var.enable_monitoring_reader ? toset(var.subscription_ids) : toset([])

  scope                = "/subscriptions/${each.value}"
  role_definition_name = "Monitoring Reader"
  principal_id         = azuread_service_principal.logicmonitor.object_id

  skip_service_principal_aad_check = true
}

# Optional: Assign Log Analytics Reader for log access
resource "azurerm_role_assignment" "log_analytics_reader" {
  for_each = var.enable_log_analytics ? toset(var.subscription_ids) : toset([])

  scope                = "/subscriptions/${each.value}"
  role_definition_name = "Log Analytics Reader"
  principal_id         = azuread_service_principal.logicmonitor.object_id

  skip_service_principal_aad_check = true
}
