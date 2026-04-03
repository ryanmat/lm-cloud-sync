# Outputs for Azure LogicMonitor Service Principal module

output "tenant_id" {
  description = "Azure AD tenant ID"
  value       = data.azuread_client_config.current.tenant_id
}

output "client_id" {
  description = "Application (client) ID for LogicMonitor"
  value       = azuread_application.logicmonitor.client_id
}

output "client_secret" {
  description = "Client secret for LogicMonitor (sensitive)"
  value       = azuread_application_password.logicmonitor.value
  sensitive   = true
}

output "service_principal_id" {
  description = "Service Principal object ID"
  value       = azuread_service_principal.logicmonitor.object_id
}

output "application_id" {
  description = "Azure AD Application object ID"
  value       = azuread_application.logicmonitor.object_id
}

output "subscription_ids" {
  description = "List of subscription IDs with assigned roles"
  value       = var.subscription_ids
}

output "lm_cloud_sync_env" {
  description = "Environment variables for lm-cloud-sync CLI"
  value = {
    AZURE_TENANT_ID     = data.azuread_client_config.current.tenant_id
    AZURE_CLIENT_ID     = azuread_application.logicmonitor.client_id
    AZURE_CLIENT_SECRET = azuread_application_password.logicmonitor.value
  }
  sensitive = true
}

output "setup_instructions" {
  description = "Instructions for using these credentials with lm-cloud-sync"
  value       = <<-EOT
    Azure Service Principal created successfully!

    To use with lm-cloud-sync CLI:

    1. Export the environment variables:
       export AZURE_TENANT_ID="${data.azuread_client_config.current.tenant_id}"
       export AZURE_CLIENT_ID="${azuread_application.logicmonitor.client_id}"
       export AZURE_CLIENT_SECRET="$(terraform output -raw client_secret)"

    2. Run discovery:
       lm-cloud-sync azure discover --auto-discover

    3. Sync to LogicMonitor:
       lm-cloud-sync azure sync --auto-discover --dry-run
       lm-cloud-sync azure sync --auto-discover --yes
  EOT
}
