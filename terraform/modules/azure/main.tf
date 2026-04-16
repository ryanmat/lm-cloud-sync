# Description: Azure LM Cloud Sync Terraform module.
# Description: Creates Azure AD SP + role assignments, and optionally LM device groups.

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
    logicmonitor = {
      source  = "ryanmat/logicmonitor"
      version = ">= 1.0"
    }
  }
}

# --- Azure AD Infrastructure (Service Principal + Role Assignments) ---

data "azurerm_subscription" "current" {}

data "azuread_client_config" "current" {}

# Create Azure AD Application for LogicMonitor
resource "azuread_application" "logicmonitor" {
  display_name = var.application_name

  owners = [data.azuread_client_config.current.object_id]

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

# --- LogicMonitor Integration (optional, gated by enable_lm_integration) ---

# Create an LM device group for each Azure subscription
resource "logicmonitor_device_group" "azure_subscription" {
  for_each = var.enable_lm_integration ? local.subscription_map : {}

  name        = replace(replace(var.group_name_template, "{subscription_id}", each.key), "{display_name}", each.value.display_name)
  parent_id   = var.lm_parent_group_id
  description = each.value.display_name
  group_type  = "Azure/AzureRoot"

  custom_properties = local.custom_props

  extra = jsonencode({
    account = {
      tenantId        = data.azuread_client_config.current.tenant_id
      clientId        = azuread_application.logicmonitor.client_id
      secretKey       = azuread_application_password.logicmonitor.value
      subscriptionIds = each.key
      collectorId     = -4
      schedule        = var.schedule
    }
    default  = local.default_config
    services = local.service_config
  })

  # Ensure role assignments exist before creating LM integrations
  depends_on = [
    azurerm_role_assignment.reader,
    azurerm_role_assignment.monitoring_reader,
  ]
}
