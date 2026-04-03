# Azure Service Principal Module for LogicMonitor

This Terraform module creates the Azure AD application and service principal required for LogicMonitor to monitor Azure subscriptions.

## Prerequisites

- Azure CLI installed and authenticated (`az login`)
- Terraform >= 1.0.0
- Permissions to create Azure AD applications and assign roles

## Required Azure Permissions

The user or service principal running Terraform needs:
- **Azure AD**: Application Administrator or Global Administrator
- **Subscriptions**: Owner or User Access Administrator on target subscriptions

## Usage

```hcl
module "logicmonitor_azure" {
  source = "./modules/azure"

  subscription_ids = [
    "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
  ]

  # Optional: customize settings
  application_name         = "LogicMonitor Cloud Integration"
  enable_monitoring_reader = true
  enable_log_analytics     = false
  tags                     = ["Production", "Monitoring"]
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| `subscription_ids` | List of Azure subscription IDs to grant access to | `list(string)` | n/a | yes |
| `application_name` | Name for the Azure AD application | `string` | `"LogicMonitor Cloud Integration"` | no |
| `secret_expiration_date` | Expiration date for the client secret (ISO 8601) | `string` | `null` (2 years) | no |
| `enable_monitoring_reader` | Assign Monitoring Reader role | `bool` | `true` | no |
| `enable_log_analytics` | Assign Log Analytics Reader role | `bool` | `false` | no |
| `tags` | Additional tags for the application | `list(string)` | `[]` | no |

## Outputs

| Name | Description |
|------|-------------|
| `tenant_id` | Azure AD tenant ID |
| `client_id` | Application (client) ID for LogicMonitor |
| `client_secret` | Client secret for LogicMonitor (sensitive) |
| `service_principal_id` | Service Principal object ID |
| `lm_cloud_sync_env` | Environment variables for lm-cloud-sync CLI |
| `setup_instructions` | Instructions for using the credentials |

## Role Assignments

This module assigns the following roles:

| Role | Scope | Description |
|------|-------|-------------|
| Reader | Each subscription | Required for basic resource enumeration |
| Monitoring Reader | Each subscription | Enhanced Azure Monitor access (optional) |
| Log Analytics Reader | Each subscription | Log workspace access (optional) |

## Example: Multi-Subscription Deployment

```hcl
# Get all subscriptions in the tenant
data "azurerm_subscriptions" "all" {}

module "logicmonitor_azure" {
  source = "./modules/azure"

  subscription_ids = [for s in data.azurerm_subscriptions.all.subscriptions : s.subscription_id]
}

# Output for lm-cloud-sync
output "azure_credentials" {
  value     = module.logicmonitor_azure.lm_cloud_sync_env
  sensitive = true
}
```

## Using with lm-cloud-sync

After running Terraform:

```bash
# Export credentials
export AZURE_TENANT_ID="$(terraform output -raw tenant_id)"
export AZURE_CLIENT_ID="$(terraform output -raw client_id)"
export AZURE_CLIENT_SECRET="$(terraform output -raw client_secret)"

# Discover subscriptions
lm-cloud-sync azure discover --auto-discover

# Preview sync
lm-cloud-sync azure sync --auto-discover --dry-run

# Execute sync
lm-cloud-sync azure sync --auto-discover --yes
```

## Security Considerations

1. **Secret Rotation**: The client secret should be rotated periodically. Set `secret_expiration_date` and plan for renewal.

2. **Least Privilege**: Only the Reader role is required for basic monitoring. Enable additional roles only if needed.

3. **Secret Storage**: Store the client secret securely (Azure Key Vault, HashiCorp Vault, etc.).

4. **Audit Logging**: Azure AD sign-in logs will record all authentication attempts by the service principal.
